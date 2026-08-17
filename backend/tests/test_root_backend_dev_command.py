import json
from pathlib import Path
import unittest


class RootBackendDevCommandContractTest(unittest.TestCase):
    def test_root_backend_dev_command_declares_a_static_uvicorn_entrypoint(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        package_json = json.loads((repo_root / "package.json").read_text())

        script = package_json["scripts"].get("dev:backend")

        self.assertTrue(script, "package.json must define a dev:backend root convenience command")
        self.assertIn("uvicorn", script, "dev:backend should invoke the FastAPI backend through uvicorn")
        self.assertIn(
            "backend.app.main:app",
            script,
            "dev:backend should target the backend ASGI entrypoint from the repo root",
        )
        self.assertNotIn(
            "pip install",
            script,
            "dev:backend must not install dependencies; dependency setup belongs outside the repo command",
        )
