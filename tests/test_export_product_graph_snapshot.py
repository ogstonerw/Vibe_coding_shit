from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from product_graph import ProductGraph
from scripts.export_product_graph_snapshot import (
    CANONICAL_SOURCE,
    DEFAULT_OUTPUT,
    build_owner_hq_snapshot,
    export_owner_hq_snapshot,
)


class OwnerHqSnapshotExporterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = ProductGraph.load(CANONICAL_SOURCE)
        self.snapshot = build_owner_hq_snapshot(self.graph)

    def test_loads_real_graph_and_derives_owner_hq_summary(self) -> None:
        self.assertEqual("AI Trading Operating System", self.snapshot["product"]["name"])
        self.assertEqual(len(self.graph.domains()), self.snapshot["summary"]["domain_count"])
        self.assertEqual(len(self.graph.waves()), self.snapshot["summary"]["wave_count"])
        self.assertEqual(len(self.graph.epics()), self.snapshot["summary"]["epic_count"])
        self.assertEqual(len(self.graph.locked()), self.snapshot["summary"]["locked_object_count"])

    def test_export_is_deterministic_and_checked_in_projection_is_current(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            first_path = Path(temp_dir) / "first.json"
            second_path = Path(temp_dir) / "second.json"
            first = export_owner_hq_snapshot(output_path=first_path)
            second = export_owner_hq_snapshot(output_path=second_path)

        self.assertEqual(first, second)
        self.assertEqual(first, DEFAULT_OUTPUT.read_bytes())

    def test_projection_metadata_is_explicitly_read_only(self) -> None:
        self.assertEqual(
            {
                "classification": "NON_OPERATIONAL_PRODUCT_GRAPH_BOOTSTRAP",
                "generated_from": "docs/product/PRODUCT_GRAPH_BOOTSTRAP.toml",
                "name": "PRODUCT_GRAPH_BOOTSTRAP",
                "operational": False,
                "projection": "READ_ONLY",
                "writable_runtime_truth": False,
            },
            self.snapshot["source"],
        )

    def test_foundation_and_active_wave_keep_canonical_statuses(self) -> None:
        waves = {item["id"]: item for item in self.snapshot["development"]["waves"]}
        self.assertEqual("W1", self.snapshot["development"]["current_wave_id"])
        self.assertEqual("DONE", waves["W0"]["status"])
        self.assertEqual("DONE", waves["W0"]["display_state"])
        self.assertEqual("ACTIVE", waves["W1"]["status"])
        self.assertEqual("CURRENT", waves["W1"]["display_state"])
        self.assertEqual("PLANNED", waves["W2"]["status"])
        self.assertIsNone(self.snapshot["development"]["next_wave_id"])

    def test_factory_001b_no_longer_requires_owner_attention(self) -> None:
        self.assertEqual([], self.snapshot["owner_decisions_required"])

    def test_authority_remains_fail_closed(self) -> None:
        environments = {
            item["subject"]: item for item in self.snapshot["authority"]["environments"]
        }
        for subject in ("PAPER", "LIMITED_LIVE", "LIVE"):
            with self.subTest(subject=subject):
                self.assertTrue(environments[subject]["locked"])
                self.assertEqual("LOCKED", environments[subject]["status"])
        self.assertFalse(self.snapshot["authority"]["capital_authority"])

    def test_exported_json_round_trips_without_non_deterministic_fields(self) -> None:
        rendered = json.dumps(self.snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        self.assertEqual(self.snapshot, json.loads(rendered))
        self.assertNotIn("generated_at", self.snapshot["source"])


if __name__ == "__main__":
    unittest.main()
