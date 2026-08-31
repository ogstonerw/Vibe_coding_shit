from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_product_graph_bootstrap.py"
BOOTSTRAP = ROOT / "docs" / "product" / "PRODUCT_GRAPH_BOOTSTRAP.toml"

SPEC = importlib.util.spec_from_file_location("check_product_graph_bootstrap", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)


class ProductGraphBootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = validator.load_bootstrap(BOOTSTRAP)

    def assert_rejected(self, data: object, expected_code: str) -> None:
        issues = validator.validate_graph(data)
        codes = {issue.code for issue in issues}
        self.assertIn(expected_code, codes, [str(issue) for issue in issues])

    def test_repository_bootstrap_passes_with_expected_shape(self) -> None:
        self.assertEqual([], validator.validate_graph(self.data))
        self.assertEqual(21, len(self.data["domains"]))
        self.assertEqual(13, len(self.data["waves"]))
        self.assertEqual(14, len(self.data["epics"]))

    def test_accepted_factory_and_wave_current_state(self) -> None:
        authority = self.data["authority"]
        stages = {item["id"]: item for item in self.data["factory_autonomy"]}
        waves = {item["id"]: item for item in self.data["waves"]}
        domains = {item["id"]: item for item in self.data["domains"]}
        lock_subjects = {item["subject"] for item in self.data["locks"]}

        self.assertEqual("FACTORY-001B", authority["current_factory_stage"])
        self.assertEqual("PRODUCT_CHANGE_LEVEL_A", authority["current_product_change_scope"])
        self.assertEqual("DONE", stages["FACTORY-001B"]["status"])
        self.assertFalse(stages["FACTORY-001B"]["locked"])
        self.assertNotIn("FACTORY-001B", lock_subjects)
        self.assertEqual("DONE", waves["W0"]["status"])
        self.assertEqual("ACTIVE", waves["W1"]["status"])
        self.assertEqual("PLANNED", waves["W2"]["status"])
        self.assertEqual(
            "FACTORY_001B_PRODUCT_CHANGE_LEVEL_A",
            domains["DOM-SOFTWARE-FACTORY"]["current_authority"],
        )

    def test_duplicate_global_id_is_rejected(self) -> None:
        data = deepcopy(self.data)
        data["domains"][1]["id"] = data["domains"][0]["id"]
        self.assert_rejected(data, "E_ID_DUPLICATE")

    def test_duplicate_dependency_pair_is_rejected(self) -> None:
        data = deepcopy(self.data)
        duplicate = deepcopy(data["dependencies"][0])
        duplicate["id"] = "DEP-DUPLICATE-PAIR"
        duplicate["dependency_type"] = "AUTHORITY"
        data["dependencies"].append(duplicate)
        self.assert_rejected(data, "E_DEPENDENCY_PAIR_DUPLICATE")

    def test_unresolved_dependency_target_is_rejected(self) -> None:
        data = deepcopy(self.data)
        data["dependencies"][0]["depends_on"] = "MISSING"
        self.assert_rejected(data, "E_DEPENDENCY_TARGET_MISSING")

    def test_dependency_cycle_is_rejected(self) -> None:
        data = deepcopy(self.data)
        data["dependencies"].append(
            {
                "id": "DEP-TEST-CYCLE",
                "source_id": "W0",
                "depends_on": "W1",
                "kind": "WAVE",
                "dependency_type": "READINESS",
            }
        )
        self.assert_rejected(data, "E_DEPENDENCY_CYCLE")

    def test_missing_mandatory_dependency_is_rejected(self) -> None:
        data = deepcopy(self.data)
        data["dependencies"] = [
            item for item in data["dependencies"] if item["id"] != "DEP-W7-W6"
        ]
        self.assert_rejected(data, "E_MANDATORY_DEPENDENCY_MISSING")

    def test_duplicate_lock_subject_is_rejected(self) -> None:
        data = deepcopy(self.data)
        duplicate = deepcopy(data["locks"][0])
        duplicate["id"] = "LOCK-DUPLICATE-SUBJECT"
        data["locks"].append(duplicate)
        self.assert_rejected(data, "E_LOCK_SUBJECT_DUPLICATE")

    def test_duplicate_gate_subject_is_rejected(self) -> None:
        data = deepcopy(self.data)
        duplicate = deepcopy(data["authority_gates"][0])
        duplicate["id"] = "GATE-DUPLICATE-SUBJECT"
        data["authority_gates"].append(duplicate)
        self.assert_rejected(data, "E_GATE_SUBJECT_DUPLICATE")

    def test_malformed_collection_type_is_rejected_without_exception(self) -> None:
        data = deepcopy(self.data)
        data["domains"] = {"id": "NOT-A-LIST"}
        self.assert_rejected(data, "E_COLLECTION_TYPE")

    def test_wrong_scalar_or_list_type_is_rejected_without_exception(self) -> None:
        data = deepcopy(self.data)
        data["product"]["cycle"] = "OWNER_INTENT"
        self.assert_rejected(data, "E_FIELD_TYPE")

    def test_malformed_table_type_is_rejected_without_exception(self) -> None:
        data = deepcopy(self.data)
        data["authority"] = ["NOT-A-TABLE"]
        self.assert_rejected(data, "E_OBJECT_TYPE")

    def test_unhashable_reference_types_are_rejected_without_exception(self) -> None:
        mutations = (
            ("epics", "wave_id"),
            ("capabilities", "epic_id"),
            ("tasks", "capability_id"),
            ("work_units", "task_id"),
            ("dependencies", "source_id"),
            ("dependencies", "depends_on"),
        )
        for collection, field in mutations:
            with self.subTest(collection=collection, field=field):
                data = deepcopy(self.data)
                data[collection][0][field] = ["WRONG-TYPE"]
                self.assert_rejected(data, "E_FIELD_TYPE")

    def test_invalid_status_is_rejected(self) -> None:
        data = deepcopy(self.data)
        data["domains"][0]["status"] = "EIGHTY_TWO_PERCENT_READY"
        self.assert_rejected(data, "E_STATUS_INVALID")

    def test_invalid_authority_vocabulary_is_rejected(self) -> None:
        data = deepcopy(self.data)
        data["waves"][0]["authority_state"] = "UNBOUNDED"
        self.assert_rejected(data, "E_AUTHORITY_INVALID")

    def test_factory_001b_non_done_state_is_rejected(self) -> None:
        data = deepcopy(self.data)
        stage = next(item for item in data["factory_autonomy"] if item["id"] == "FACTORY-001B")
        stage["status"] = "READY"
        self.assert_rejected(data, "E_FACTORY_STATE")

    def test_factory_001b_relock_is_rejected(self) -> None:
        data = deepcopy(self.data)
        stage = next(item for item in data["factory_autonomy"] if item["id"] == "FACTORY-001B")
        stage["locked"] = True
        self.assert_rejected(data, "E_FACTORY_STATE")

    def test_required_safety_locks_cannot_be_removed_or_reversed(self) -> None:
        for subject in (
            "FACTORY-001C",
            "FACTORY-001D",
            "FACTORY-001E",
            "PAPER",
            "LIMITED_LIVE",
            "LIVE",
            "CAPITAL_AUTHORITY",
        ):
            with self.subTest(subject=subject, mutation="removed"):
                data = deepcopy(self.data)
                data["locks"] = [item for item in data["locks"] if item["subject"] != subject]
                self.assert_rejected(data, "E_LOCK_SUBJECT_SET")
            with self.subTest(subject=subject, mutation="unlocked"):
                data = deepcopy(self.data)
                lock = next(item for item in data["locks"] if item["subject"] == subject)
                lock["locked"] = False
                self.assert_rejected(data, "E_LOCK_STATE")

    def test_paper_unlock_is_rejected(self) -> None:
        data = deepcopy(self.data)
        lock = next(item for item in data["locks"] if item["subject"] == "PAPER")
        lock["locked"] = False
        self.assert_rejected(data, "E_LOCK_STATE")

    def test_limited_live_unlock_is_rejected(self) -> None:
        data = deepcopy(self.data)
        lock = next(item for item in data["locks"] if item["subject"] == "LIMITED_LIVE")
        lock["locked"] = False
        self.assert_rejected(data, "E_LOCK_STATE")

    def test_live_unlock_is_rejected(self) -> None:
        data = deepcopy(self.data)
        lock = next(item for item in data["locks"] if item["subject"] == "LIVE")
        lock["locked"] = False
        self.assert_rejected(data, "E_LOCK_STATE")

    def test_owner_gate_cannot_grant_authority_in_bootstrap(self) -> None:
        data = deepcopy(self.data)
        gate = next(item for item in data["authority_gates"] if item["subject"] == "PAPER")
        gate["grants_authority"] = True
        self.assert_rejected(data, "E_GATE_STATE")

    def test_all_trading_authority_flags_true_are_rejected(self) -> None:
        for field in (
            "capital_authority",
            "paper_authority",
            "limited_live_authority",
            "live_authority",
        ):
            with self.subTest(field=field):
                data = deepcopy(self.data)
                data["authority"][field] = True
                self.assert_rejected(data, "E_AUTHORITY_STATE")

    def test_done_without_evidence_is_rejected(self) -> None:
        data = deepcopy(self.data)
        data["waves"][0]["evidence_refs"] = []
        self.assert_rejected(data, "E_EVIDENCE_REQUIRED")

    def test_malformed_object_shape_is_rejected(self) -> None:
        data = deepcopy(self.data)
        data["unknown_frontier"][0] = "NOT-A-TABLE"
        self.assert_rejected(data, "E_OBJECT_TYPE")

    def test_invalid_operational_runtime_claim_is_rejected(self) -> None:
        data = deepcopy(self.data)
        data["operational"] = True
        data["writable_runtime_truth"] = True
        self.assert_rejected(data, "E_BOOTSTRAP_AUTHORITY")

    def test_nested_planning_object_cannot_claim_operational_status(self) -> None:
        for collection in ("tasks", "work_units"):
            with self.subTest(collection=collection):
                data = deepcopy(self.data)
                data[collection][0]["non_operational"] = False
                self.assert_rejected(data, "E_BOOTSTRAP_AUTHORITY")

    def test_locked_trading_wave_authority_cannot_drift(self) -> None:
        data = deepcopy(self.data)
        wave = next(item for item in data["waves"] if item["id"] == "W7")
        wave["authority_state"] = "ENVIRONMENT_SCOPED_AND_SEPARATELY_GATED"
        self.assert_rejected(data, "E_AUTHORITY_CROSS_FIELD")

    def test_unknown_top_level_and_object_fields_are_rejected(self) -> None:
        data = deepcopy(self.data)
        data["runtime_registry"] = {"enabled": True}
        data["domains"][0]["implementation"] = "postgres"
        self.assert_rejected(data, "E_TOP_LEVEL_UNKNOWN")
        self.assert_rejected(data, "E_FIELD_UNKNOWN")

    def test_invalid_evidence_type_is_rejected_without_exception(self) -> None:
        data = deepcopy(self.data)
        stage = next(item for item in data["factory_autonomy"] if item["id"] == "FACTORY-001A")
        stage["evidence_refs"] = 42
        self.assert_rejected(data, "E_FIELD_TYPE")

    def test_factory_lock_cross_field_mismatch_is_rejected(self) -> None:
        data = deepcopy(self.data)
        lock = next(item for item in data["locks"] if item["subject"] == "FACTORY-001C")
        lock["status"] = "NEEDS_OWNER"
        self.assert_rejected(data, "E_FACTORY_LOCK_MISMATCH")

    def test_factory_baseline_sha_drift_is_rejected(self) -> None:
        data = deepcopy(self.data)
        data["baseline"]["git_head"] = "0" * 40
        self.assert_rejected(data, "E_BASELINE_STATE")

    def test_wave_numbering_drift_is_rejected(self) -> None:
        data = deepcopy(self.data)
        data["waves"][0]["number"] = 99
        self.assert_rejected(data, "E_WAVE_NUMBERING")

    def test_cli_default_path_is_repository_anchored(self) -> None:
        with tempfile.TemporaryDirectory() as outside_repo:
            result = subprocess.run(
                [sys.executable, str(SCRIPT)],
                cwd=outside_repo,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("PRODUCT_GRAPH_BOOTSTRAP: PASS", result.stdout)

    def test_cli_malformed_toml_fails_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            malformed = Path(temp_dir) / "malformed.toml"
            malformed.write_text("domains = [", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(malformed)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(1, result.returncode)
        self.assertIn("E_TOML_PARSE", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
