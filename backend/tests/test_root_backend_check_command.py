import json
from pathlib import Path
import unittest


class RootBackendCheckCommandContractTest(unittest.TestCase):
    def test_root_backend_check_command_declares_a_static_pytest_flow(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        package_json = json.loads((repo_root / "package.json").read_text())

        script = package_json["scripts"].get("check:backend")

        self.assertTrue(script, "package.json must define a check:backend root convenience command")
        self.assertIn("pytest", script, "check:backend should run pytest through the root command")
        self.assertNotIn(
            "pip install",
            script,
            "check:backend must not install dependencies; dependency setup belongs outside the repo check command",
        )
        self.assertNotIn(
            "npm install",
            script,
            "check:backend must not install dependencies; dependency setup belongs outside the repo check command",
        )
