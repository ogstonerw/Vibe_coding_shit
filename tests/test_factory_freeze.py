from __future__ import annotations

import ast
import unittest
from pathlib import Path

from factory.configuration import load_daily_config
from factory.integrity import canonical_sha256, parse_manifest, verify_manifest


ROOT = Path(__file__).resolve().parents[1]


class FactoryFreezeTests(unittest.TestCase):
    def test_v11_is_preserved_and_v12_changes_only_self_check_hash(self) -> None:
        v11 = dict(parse_manifest(ROOT, "docs/FROZEN_CORE_V11.sha256"))
        v12 = dict(parse_manifest(ROOT, "docs/FROZEN_CORE_V12.sha256"))
        self.assertEqual(10, len(v11))
        self.assertEqual(set(v11), set(v12))
        changed = {path for path in v11 if v11[path] != v12[path]}
        self.assertEqual({"scripts/self_check.py"}, changed)
        self.assertNotEqual(v11["scripts/self_check.py"], canonical_sha256(ROOT / "scripts/self_check.py"))
        self.assertEqual(v12["scripts/self_check.py"], canonical_sha256(ROOT / "scripts/self_check.py"))

    def test_active_v12_and_pm_dec_007_manifests_pass(self) -> None:
        config = load_daily_config(ROOT / "factory/daily_run.toml")
        self.assertEqual(
            (),
            verify_manifest(ROOT, config.active_core_manifest, config.active_core_manifest_sha256),
        )
        self.assertEqual(
            (),
            verify_manifest(ROOT, config.pm_dec_007_manifest, config.pm_dec_007_manifest_sha256),
        )
        self.assertEqual("docs/FROZEN_CORE_V12.sha256", config.active_core_manifest)
        self.assertEqual(
            "docs/FROZEN_PM_DEC_007_HYBRID_V2.sha256",
            config.pm_dec_007_manifest,
        )

    def test_pm_v1_is_historical_and_v2_changes_only_operational_checks(self) -> None:
        v1 = dict(parse_manifest(ROOT, "docs/FROZEN_PM_DEC_007_HYBRID_V1.sha256"))
        v2 = dict(parse_manifest(ROOT, "docs/FROZEN_PM_DEC_007_HYBRID_V2.sha256"))
        self.assertEqual(9, len(v1))
        self.assertEqual(set(v1), set(v2))
        self.assertEqual(
            {"scripts/check_pm_dec007_hybrid.py", "tests/test_pm_dec007_hybrid.py"},
            {path for path in v1 if v1[path] != v2[path]},
        )

    def test_factory_has_no_forbidden_runtime_imports(self) -> None:
        forbidden = {
            "openai",
            "codex",
            "telethon",
            "telegram",
            "aiogram",
            "bitget",
            "requests",
            "httpx",
            "websocket",
        }
        findings: list[str] = []
        for path in sorted((ROOT / "factory").glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name.split(".", 1)[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module.split(".", 1)[0]]
                else:
                    continue
                findings.extend(f"{path.name}:{name}" for name in names if name in forbidden)
        self.assertEqual([], findings)

    def test_workflow_is_dry_run_only_at_0700_utc(self) -> None:
        workflow = (ROOT / ".github/workflows/daily-factory-control-plane.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn('cron: "0 7 * * *"', workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("python3 -m factory.daily_run --dry-run", workflow)
        for forbidden in ("git commit", "git push", "gh pr", "OPENAI_API_KEY", "secrets."):
            self.assertNotIn(forbidden, workflow)

    def test_limits_and_authorities_are_fixed(self) -> None:
        config = load_daily_config(ROOT / "factory/daily_run.toml")
        self.assertEqual((1, 1, 2, 90), (
            config.max_tasks_per_day,
            config.max_parallel_writers,
            config.max_correction_loops,
            config.max_run_time_minutes,
        ))
        self.assertFalse(config.auto_merge)
        self.assertFalse(config.auto_product_approval)
        self.assertFalse(config.paper_authority)
        self.assertFalse(config.live_authority)


if __name__ == "__main__":
    unittest.main()
