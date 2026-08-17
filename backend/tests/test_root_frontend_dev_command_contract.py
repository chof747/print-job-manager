import json
from pathlib import Path
import unittest


class RootFrontendDevCommandContractTest(unittest.TestCase):
    def test_root_frontend_dev_command_declares_a_static_vite_flow(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        package_json = json.loads((repo_root / "package.json").read_text())

        script = package_json["scripts"].get("dev:frontend")
        dependencies = package_json.get("dependencies", {})
        dev_dependencies = package_json.get("devDependencies", {})

        self.assertTrue(script, "package.json must define a dev:frontend root convenience command")
        self.assertIn("vite", script, "dev:frontend should invoke the frontend through Vite")
        self.assertIn("frontend", script, "dev:frontend should explicitly target the frontend app from the repo root")
        self.assertNotIn(
            "pip install",
            script,
            "dev:frontend must not install dependencies; dependency setup belongs outside the repo command",
        )
        self.assertNotIn(
            "npm install",
            script,
            "dev:frontend must not install dependencies; dependency setup belongs outside the repo command",
        )
        self.assertTrue(
            "vite" in dependencies or "vite" in dev_dependencies,
            "dev:frontend should be backed by a declared vite dependency in package.json",
        )
