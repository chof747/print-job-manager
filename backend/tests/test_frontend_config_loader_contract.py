import json
from pathlib import Path
import unittest


class FrontendConfigLoaderContractTest(unittest.TestCase):
    def test_vite_and_vitest_configs_use_module_filenames_under_a_commonjs_package_boundary(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        package_json = json.loads((repo_root / "package.json").read_text(encoding="utf-8"))

        self.assertEqual(
            "commonjs",
            package_json.get("type"),
            "this contract applies only while the repo package boundary remains CommonJS",
        )

        expected_module_configs = [repo_root / "vitest.config.mts", repo_root / "frontend" / "vite.config.mts"]
        legacy_ts_configs = [repo_root / "vitest.config.ts", repo_root / "frontend" / "vite.config.ts"]

        missing_module_configs = [
            config_path.relative_to(repo_root).as_posix()
            for config_path in expected_module_configs
            if not config_path.is_file()
        ]
        legacy_configs_still_present = [
            config_path.relative_to(repo_root).as_posix()
            for config_path in legacy_ts_configs
            if config_path.exists()
        ]

        self.assertEqual([], missing_module_configs, "expected module-signaling config filenames are missing")
        self.assertEqual(
            [],
            legacy_configs_still_present,
            "legacy .ts Vite and Vitest config filenames should not remain under a CommonJS package boundary",
        )
