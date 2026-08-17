from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[2]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.main import app


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def package_json(repo_root: Path) -> dict:
    import json

    return json.loads((repo_root / "package.json").read_text(encoding="utf-8"))


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
