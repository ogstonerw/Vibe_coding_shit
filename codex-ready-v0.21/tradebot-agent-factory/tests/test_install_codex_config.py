from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("install_codex_config", ROOT / "scripts/install_codex_config.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class InstallerTests(unittest.TestCase):
    def test_source_contains_config_and_all_agents(self) -> None:
        self.assertTrue((MODULE.SOURCE / "config.toml").is_file())
        agent_files = {path.stem for path in (MODULE.SOURCE / "agents").glob("*.toml")}
        self.assertEqual(12, len(agent_files))


if __name__ == "__main__":
    unittest.main()
