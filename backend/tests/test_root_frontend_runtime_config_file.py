import json
from pathlib import Path


def test_frontend_runtime_config_file_exists_with_api_base_url() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    runtime_config_path = repo_root / "frontend" / "public" / "runtime-config.json"

    assert runtime_config_path.is_file()

    runtime_config = json.loads(runtime_config_path.read_text(encoding="utf-8"))

    assert runtime_config["apiBaseUrl"]
