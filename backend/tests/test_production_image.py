import os
import subprocess
import time
from collections.abc import Iterator
from http.client import HTTPException
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen
from uuid import uuid4

import pytest


@pytest.fixture
def backend_image(repo_root: Path) -> Iterator[str]:
    prebuilt = os.environ.get("PJM_BACKEND_IMAGE")
    if prebuilt:
        yield prebuilt
        return

    context = repo_root / "backend"
    assert (context / "Dockerfile").is_file(), "backend production image build is missing"

    tag = f"print-job-manager-backend-test:{uuid4().hex}"
    try:
        result = subprocess.run(
            ["docker", "build", "--platform", "linux/amd64", "--tag", tag, str(context)],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        yield tag
    finally:
        subprocess.run(
            ["docker", "image", "rm", tag],
            capture_output=True,
            timeout=30,
            check=False,
        )


def test_backend_production_image_builds_for_amd64(backend_image: str) -> None:
    assert backend_image


def test_backend_production_image_runs_as_non_root(backend_image: str) -> None:
    name = f"print-job-manager-user-test-{uuid4().hex}"
    try:
        result = subprocess.run(
            [
                "docker", "run", "--rm", "--platform", "linux/amd64", "--name", name,
                "--entrypoint", "id", backend_image, "-u",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert int(result.stdout.strip()) != 0, "backend image runs as root"
    finally:
        subprocess.run(
            ["docker", "rm", "-f", name],
            capture_output=True,
            timeout=30,
            check=False,
        )


def test_backend_image_migrates_disposable_database_and_starts(backend_image: str) -> None:
    suffix = uuid4().hex
    network = f"pjm-test-network-{suffix}"
    database = f"pjm-test-db-{suffix}"
    backend = f"pjm-test-api-{suffix}"

    def docker(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["docker", *args], capture_output=True, text=True, timeout=30, check=check
        )

    try:
        docker("network", "create", network)
        docker(
            "run", "-d", "--name", database, "--network", network,
            "-e", "POSTGRES_PASSWORD=test-password", "postgres:16",
        )
        deadline = time.monotonic() + 45
        while docker(
            "exec", database, "pg_isready", "-h", "127.0.0.1", "-U", "postgres", check=False
        ).returncode:
            assert time.monotonic() < deadline, "disposable PostgreSQL did not become ready"
            time.sleep(0.5)

        docker(
            "run", "-d", "--platform", "linux/amd64", "--name", backend,
            "--network", network, "-p", "127.0.0.1::8000",
            "-e", f"PRINT_JOB_MANAGER_DATABASE_URL=postgresql+psycopg://postgres:"
            f"test-password@{database}:5432/postgres", backend_image,
        )
        port = docker("port", backend, "8000/tcp").stdout.strip().rsplit(":", 1)[1]
        deadline = time.monotonic() + 20
        while True:
            try:
                with urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
                    assert response.status == 200
                break
            except (URLError, OSError, HTTPException):
                if time.monotonic() >= deadline:
                    logs = docker("logs", backend, check=False)
                    pytest.fail(f"backend did not become ready: {logs.stderr}")
                time.sleep(0.2)

        result = docker(
            "exec", database, "psql", "-U", "postgres", "-d", "postgres", "-Atc",
            "SELECT version_num FROM alembic_version", check=False,
        )
        assert result.returncode == 0, f"packaged migrations were not applied: {result.stderr}"
        revision = result.stdout.strip()
        head = docker("exec", backend, "alembic", "heads").stdout.split()[0]
        assert revision == head
    finally:
        docker("rm", "-f", backend, database, check=False)
        docker("network", "rm", network, check=False)


def test_backend_image_stops_when_migrations_fail(backend_image: str) -> None:
    name = f"pjm-test-migration-failure-{uuid4().hex}"
    try:
        result = subprocess.run(
            [
                "docker", "run", "--name", name, "--network", "none", "--platform",
                "linux/amd64", "-e", "PRINT_JOB_MANAGER_DATABASE_URL="
                "postgresql+psycopg://postgres:test@127.0.0.1:1/postgres?connect_timeout=2",
                backend_image,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode != 0, "backend should fail when migration cannot connect"
        assert "connection refused" in result.stderr.lower()
        assert "Uvicorn running" not in result.stderr
    finally:
        subprocess.run(
            ["docker", "rm", "-f", name], capture_output=True, timeout=30, check=False
        )


def test_backend_image_does_not_start_when_postgresql_rejects_migration(
    backend_image: str,
) -> None:
    suffix = uuid4().hex
    network = f"pjm-test-failure-network-{suffix}"
    database = f"pjm-test-failure-db-{suffix}"
    backend = f"pjm-test-failure-api-{suffix}"

    def docker(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["docker", *args], capture_output=True, text=True, timeout=30, check=check
        )

    try:
        docker("network", "create", network)
        docker(
            "run", "-d", "--name", database, "--network", network,
            "-e", "POSTGRES_PASSWORD=test-password", "postgres:16",
        )
        deadline = time.monotonic() + 45
        while docker(
            "exec", database, "pg_isready", "-h", "127.0.0.1", "-U", "postgres", check=False
        ).returncode:
            assert time.monotonic() < deadline, "disposable PostgreSQL did not become ready"
            time.sleep(0.5)
        docker(
            "exec", database, "psql", "-U", "postgres", "-d", "postgres", "-v",
            "ON_ERROR_STOP=1", "-c", "CREATE ROLE no_migrate LOGIN PASSWORD 'test-password'",
        )
        result = docker(
            "run", "--name", backend, "--network", network, "--platform", "linux/amd64",
            "-e", f"PRINT_JOB_MANAGER_DATABASE_URL=postgresql+psycopg://no_migrate:"
            f"test-password@{database}:5432/postgres", backend_image, check=False,
        )
        assert result.returncode != 0, "backend should exit when migration is rejected"
        assert "permission denied" in result.stderr.lower(), result.stderr
        assert "Uvicorn running" not in result.stderr
    finally:
        docker("rm", "-f", backend, database, check=False)
        docker("network", "rm", network, check=False)
