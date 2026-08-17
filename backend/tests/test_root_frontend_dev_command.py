from pathlib import Path
import unittest


class FrontendDevServerTestRemediationContract(unittest.TestCase):
    def test_frontend_dev_server_smoke_tests_have_been_removed_from_committed_tests(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        frontend_root_tests = sorted((repo_root / "backend" / "tests").glob("test_root_frontend*.py"))

        invalid_files = []
        for test_file in frontend_root_tests:
            if test_file.name == Path(__file__).name:
                continue

            source = test_file.read_text(encoding="utf-8")
            if "import subprocess" in source or "subprocess." in source:
                invalid_files.append(test_file.relative_to(repo_root).as_posix())

        self.assertEqual(
            [],
            invalid_files,
            "frontend dev-server startup verification belongs in manual QA, not committed tests",
        )
