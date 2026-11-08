from pathlib import Path


def test_deployment_docs_identify_both_ghcr_images(repo_root: Path) -> None:
    documents = [repo_root / "README.md", *(repo_root / "docs").rglob("*.md")]
    assert any(
        all(
            reference in text
            for reference in (
                "ghcr.io/",
                "print-job-manager-backend",
                "print-job-manager-frontend",
            )
        )
        for path in documents
        if (text := path.read_text(encoding="utf-8").lower())
    ), "deployment documentation must identify both GHCR images"


def test_deployment_docs_describe_runtime_configuration(repo_root: Path) -> None:
    documents = [repo_root / "README.md", *(repo_root / "docs").rglob("*.md")]
    deployment_docs = [
        text
        for path in documents
        if "ghcr.io/" in (text := path.read_text(encoding="utf-8").lower())
        and "print-job-manager-backend" in text
        and "print-job-manager-frontend" in text
    ]
    assert deployment_docs, "deployment documentation must identify both GHCR images"
    required = (
        "print_job_manager_database_url",
        "print_job_manager_artifact_storage_path",
        "runtime-config.json",
        "8000",
        "8080",
        "65532",
        "migration",
        "rollback",
    )
    assert any(all(item in doc for item in required) for doc in deployment_docs), (
        "image deployment documentation must cover configuration, ports, user, "
        "storage, migrations, and rollback"
    )


def test_frontend_deployment_docs_describe_runtime_identity_and_mount_access(
    repo_root: Path,
) -> None:
    import re

    documents = [repo_root / "README.md", *(repo_root / "docs").rglob("*.md")]
    texts = [path.read_text(encoding="utf-8").lower() for path in documents]
    assert any(
        "frontend" in text
        and "runtime-config.json" in text
        and re.search(r"uid(?:/gid)?[^\n]*\b101\b", text)
        and re.search(r"(?:gid[^\n]*\b101\b|uid/gid[^\n]*\b101\b)", text)
        and re.search(r"(?:readable|read access)[\s\S]{0,200}runtime-config\.json|"
                      r"runtime-config\.json[\s\S]{0,200}(?:readable|read access)", text)
        for text in texts
    ), "frontend deployment docs must identify UID/GID 101 and runtime config read access"
