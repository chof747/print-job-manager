import json
from pathlib import Path


def test_image_publication_checks_frontend_dependency_sync(repo_root: Path) -> None:
    package = json.loads((repo_root / "package.json").read_text(encoding="utf-8"))
    scripts = package.get("scripts", {})
    assert "check:frontend-image-deps" in scripts, (
        "a frontend image dependency synchronization check is required"
    )
    workflow = (repo_root / ".github" / "workflows" / "publish-images.yml").read_text()
    assert "check:frontend-image-deps" in workflow, (
        "image publication must run the dependency synchronization check"
    )
