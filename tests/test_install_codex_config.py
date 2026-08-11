from __future__ import annotations

import importlib.util
import tomllib
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
        self.assertEqual(14, len(agent_files))

    def test_ui_agents_are_read_only_high_reasoning_and_synchronized(self) -> None:
        with (MODULE.SOURCE / "config.toml").open("rb") as handle:
            source_config = tomllib.load(handle)
        with (ROOT / ".codex/config.toml").open("rb") as handle:
            installed_config = tomllib.load(handle)

        for name in ("game_ux_designer", "pro_trader_ux"):
            expected_ref = f"./agents/{name}.toml"
            self.assertEqual(expected_ref, source_config["agents"][name]["config_file"])
            self.assertEqual(expected_ref, installed_config["agents"][name]["config_file"])
            source = MODULE.SOURCE / "agents" / f"{name}.toml"
            installed = ROOT / ".codex/agents" / f"{name}.toml"
            self.assertEqual(source.read_bytes(), installed.read_bytes())
            with source.open("rb") as handle:
                agent = tomllib.load(handle)
            self.assertEqual("gpt-5.6", agent["model"])
            self.assertEqual("high", agent["model_reasoning_effort"])
            self.assertEqual("read-only", agent["sandbox_mode"])


if __name__ == "__main__":
    unittest.main()
