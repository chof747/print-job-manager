import re
from pathlib import Path


def test_published_image_digests_are_recorded_together_for_deployment(
    repo_root: Path,
) -> None:
    workflow = (repo_root / ".github/workflows/publish-images.yml").read_text()
    assert re.search(r"uses:\s*actions/upload-artifact@", workflow), (
        "publish a successful-run artifact containing the backend and frontend digest pair"
    )
