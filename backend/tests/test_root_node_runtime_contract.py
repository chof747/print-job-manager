import json
from pathlib import Path
import re
import unittest


class RootNodeRuntimeContractTest(unittest.TestCase):
    def test_root_package_declares_a_modern_node_runtime_contract_for_frontend_tooling(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        package_json = json.loads((repo_root / "package.json").read_text())

        engines = package_json.get("engines", {})
        node_contract = engines.get("node")

        self.assertTrue(
            node_contract,
            "package.json must declare an engines.node runtime contract for the repo-level frontend toolchain",
        )
        self.assertRegex(
            node_contract,
            re.compile(r"(?:^|[^\d])(20|2[1-9]|[3-9]\d)(?:[^\d]|$)"),
            "engines.node should explicitly target Node 20+ for the Vite/Vitest toolchain",
        )
