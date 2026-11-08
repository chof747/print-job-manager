import re
from pathlib import Path


def test_obsolete_docker_interception_wrapper_is_absent(repo_root: Path) -> None:
    assert not (repo_root / ".github/scripts/docker").exists(), (
        "the superseded Docker interception wrapper must be removed"
    )


def test_image_publication_checks_use_explicit_prebuilt_image_references(
    repo_root: Path,
) -> None:
    workflow = (repo_root / ".github/workflows/publish-images.yml").read_text()
    for component in ("BACKEND", "FRONTEND"):
        assert re.search(rf"\bPJM_{component}_IMAGE\s*[:=]\s*\S", workflow), (
            f"CI must supply the {component.lower()} prebuilt image to its image suite"
        )
    assert ".github/scripts/docker" not in workflow, (
        "CI must not intercept Docker commands to retain checked images"
    )
