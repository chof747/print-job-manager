import json
from pathlib import Path
import unittest


class RootFrontendCheckCommandContractTest(unittest.TestCase):
    def test_root_frontend_check_command_declares_an_explicit_frontend_vitest_flow(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        package_json = json.loads((repo_root / "package.json").read_text())

        script = package_json["scripts"].get("check:frontend")

        self.assertTrue(script, "package.json must define a check:frontend root convenience command")
        self.assertIn("vitest", script, "check:frontend should run Vitest through the root command")
        self.assertNotIn(
            "npm install",
            script,
            "check:frontend must not install dependencies; dependency setup belongs outside the repo check command",
        )
        self.assertIn(
            "frontend/",
            script,
            "check:frontend should explicitly scope Vitest to the frontend app from the repo root",
        )
