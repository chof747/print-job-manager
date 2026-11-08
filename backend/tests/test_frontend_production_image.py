import json
import os
import subprocess
import time
from collections.abc import Iterator
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from uuid import uuid4

import pytest


@pytest.fixture
def frontend_image(repo_root: Path) -> Iterator[str]:
    prebuilt = os.environ.get("PJM_FRONTEND_IMAGE")
    if prebuilt:
        yield prebuilt
        return

    context = repo_root / "frontend"
    assert (context / "Dockerfile").is_file(), "frontend production image build is missing"

    tag = f"print-job-manager-frontend-test:{uuid4().hex}"
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


def test_frontend_production_image_builds_for_amd64(frontend_image: str) -> None:
    assert frontend_image


def test_frontend_image_serves_client_side_routes(frontend_image: str) -> None:
    name = f"print-job-manager-frontend-route-{uuid4().hex}"
    try:
        start = subprocess.run(
            [
                "docker", "run", "-d", "--platform", "linux/amd64", "--name", name,
                "-p", "127.0.0.1::8080", frontend_image,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert start.returncode == 0, start.stderr
        port = subprocess.run(
            ["docker", "port", name, "8080/tcp"],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        ).stdout.strip().rsplit(":", 1)[1]
        base_url = f"http://127.0.0.1:{port}"
        deadline = time.monotonic() + 20
        while True:
            try:
                with urlopen(base_url + "/", timeout=2) as response:
                    index = response.read()
                break
            except (URLError, OSError, HTTPException):
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.2)
        try:
            with urlopen(base_url + "/jobs/client-side-route", timeout=5) as response:
                status, body = response.status, response.read()
        except HTTPError as error:
            status, body = error.code, error.read()
        assert status == 200, f"client-side route returned HTTP {status}"
        assert body == index
    finally:
        subprocess.run(
            ["docker", "rm", "-f", name],
            capture_output=True,
            timeout=30,
            check=False,
        )


def test_frontend_image_serves_mounted_runtime_config(
    frontend_image: str, tmp_path: Path
) -> None:
    config_path = tmp_path / "runtime-config.json"
    config = {"apiBaseUrl": "https://printer.example.test/api/v1"}
    config_path.write_text(json.dumps(config), encoding="utf-8")
    config_path.chmod(0o644)
    name = f"pjm-test-frontend-config-{uuid4().hex}"
    try:
        subprocess.run(
            [
                "docker", "run", "-d", "--platform", "linux/amd64", "--name", name,
                "-p", "127.0.0.1::8080", "--mount",
                f"type=bind,src={config_path},dst=/usr/share/nginx/html/runtime-config.json,readonly",
                frontend_image,
            ],
            capture_output=True, text=True, timeout=30, check=True,
        )
        port = subprocess.run(
            ["docker", "port", name, "8080/tcp"],
            capture_output=True, text=True, timeout=30, check=True,
        ).stdout.strip().rsplit(":", 1)[1]
        deadline = time.monotonic() + 20
        while True:
            try:
                with urlopen(f"http://127.0.0.1:{port}/runtime-config.json", timeout=2) as response:
                    assert response.status == 200
                    assert json.load(response) == config
                break
            except (URLError, OSError, HTTPException):
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.2)
    finally:
        subprocess.run(
            ["docker", "rm", "-f", name], capture_output=True, timeout=30, check=False,
        )


def test_frontend_image_runs_as_non_root(frontend_image: str) -> None:
    name = f"pjm-test-frontend-user-{uuid4().hex}"
    try:
        result = subprocess.run(
            [
                "docker", "run", "--rm", "--platform", "linux/amd64", "--name", name,
                "--entrypoint", "id", frontend_image, "-u",
            ],
            capture_output=True, text=True, timeout=30, check=False,
        )
        assert result.returncode == 0, result.stderr
        assert int(result.stdout.strip()) != 0, "frontend image runs as root"
    finally:
        subprocess.run(
            ["docker", "rm", "-f", name], capture_output=True, timeout=30, check=False,
        )
