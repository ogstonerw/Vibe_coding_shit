from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("factory_self_check", ROOT / "scripts/self_check.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FactorySelfCheckTests(unittest.TestCase):
    def test_repository_passes_self_check(self) -> None:
        self.assertEqual([], MODULE.run_checks())

    def test_risk_legs_match_total_cap(self) -> None:
        policy = MODULE.load_toml(ROOT / "governance/risk-policy.toml")
        total = float(policy["position_risk"]["risk_total_cap_pct"])
        legs = sum(float(value) for value in policy["position_risk"]["risk_legs_pct"])
        self.assertEqual(total, legs)

    def test_live_trading_is_disabled(self) -> None:
        policy = MODULE.load_toml(ROOT / "governance/risk-policy.toml")
        self.assertIs(False, policy["live_trading"]["enabled"])


if __name__ == "__main__":
    unittest.main()

