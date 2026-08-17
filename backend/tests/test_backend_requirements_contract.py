from pathlib import Path
import unittest


class BackendRequirementsContractTest(unittest.TestCase):
    def test_backend_runtime_and_test_requirements_declare_the_shell_stack(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        backend_requirements = (repo_root / "backend" / "requirements.txt").read_text(encoding="utf-8")
        backend_test_requirements = (
            repo_root / "backend" / "tests" / "requirements.txt"
        ).read_text(encoding="utf-8")

        self.assertIn("fastapi==", backend_requirements)
        self.assertIn("uvicorn==", backend_requirements)
        self.assertIn("pytest==", backend_test_requirements)
        self.assertIn("fastapi==", backend_test_requirements)
        self.assertIn("httpx==", backend_test_requirements)
