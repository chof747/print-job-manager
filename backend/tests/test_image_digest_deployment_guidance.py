import re
from pathlib import Path


def test_deployment_guidance_identifies_paired_digest_artifact(repo_root: Path) -> None:
    documentation = (repo_root / "README.md").read_text().lower()
    assert re.search(r"\bartifact\b", documentation), (
        "deployment guidance must tell operators where to find the digest pair"
    )
    assert re.search(r"\bdigests?\b", documentation), (
        "deployment guidance must direct consistent deployments to the paired digests"
    )
