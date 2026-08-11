from __future__ import annotations

import copy
import hashlib
import io
import subprocess
import sys
import tempfile
import tomllib
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from scripts.check_pm_dec007_hybrid import (
    ACTIVE_CORE_MANIFEST,
    ACTIVE_CORE_MANIFEST_SHA256,
    ACTIVE_PM_MANIFEST,
    DIGEST_FIELDS,
    DISTINCT_FIELDS,
    EQUAL_BINDING_FIELDS,
    FACTOR_FIELDS,
    FROZEN_CORE_V11_PATHS,
    FROZEN_CORE_V12_PATHS,
    FROZEN_PM_DEC007_PATHS,
    HISTORICAL_CORE_MANIFEST,
    HISTORICAL_CORE_MANIFEST_SHA256,
    HISTORICAL_PM_MANIFEST,
    HISTORICAL_PM_MANIFEST_SHA256,
    PM_DEC007_BINDING_VALID,
    PM_DEC007_CALLER_AUTHORITY_CLAIM,
    PM_DEC007_CHECKPOINT_UNAVAILABLE,
    PM_DEC007_FACTORS_NOT_INDEPENDENT,
    PM_DEC007_FACTOR_SHAPE_INVALID,
    PM_DEC007_PAYLOAD_BINDING_MISMATCH,
    PM_DEC007_RECORD_INVALID,
    PM_DEC007_RECORD_VALID,
    PM_DEC007_RUNTIME_TRUST_INCOMPLETE,
    POSITIVE_INTEGER_FIELDS,
    REQUIRED_ARTIFACT_HASHES,
    TOKEN_FIELDS,
    main,
    pm_dec007_authority_readiness_result,
    pm_dec007_checkpoint_claim_result,
    pm_dec007_hybrid_binding_shape_result,
    pm_dec007_payload_digest,
    pm_dec007_record_result,
    run_checks,
    validate_pm_dec007_record,
)


ROOT = Path(__file__).resolve().parents[1]
ADDENDUM = ROOT / "specs/pm-dec-007-hybrid-trust-v1"
DECISION = ADDENDUM / "decisions/PM-DEC-007.toml"
# Written as adjacent exact fragments to make accidental substitution visible.
PM_DEC003_V1_SHA256 = (
    "618dd1da08fb6a8f7f0631fa6824bea1"
    "cc527d071e035b20b9250bcd374789ce"
)


def _load_decision() -> dict:
    with DECISION.open("rb") as handle:
        return tomllib.load(handle)


def _manifest_entries(relative: str) -> list[tuple[str, str]]:
    entries = []
    for line in (ROOT / relative).read_text(encoding="utf-8").splitlines():
        digest, path = line.split("  ", 1)
        entries.append((path, digest))
    return entries


def _redigest(record: dict) -> dict:
    record["integrity"]["decision_payload_sha256"] = pm_dec007_payload_digest(record)
    return record


def _replace_with_string_subclass_key(mapping: dict, key: str) -> None:
    class StringSubclass(str):
        pass

    value = mapping.pop(key)
    mapping[StringSubclass(key)] = value


def _factor_pair(
    payload: bytes = b"\xff\x00opaque-not-json\x80",
) -> tuple[dict, dict]:
    payload_digest = hashlib.sha256(payload).hexdigest()
    common = {
        "factor_record_version": 1,
        "trust_set_id": "trust-set:owner-epoch-2",
        "owner_identity_ref": "owner:opaque-ref-1",
        "owner_trust_epoch": 2,
        "global_sequence_namespace_id": "level-b:global-sequence-v1",
        "manifest_id": "manifest:level-b-17",
        "manifest_version": 4,
        "monotonic_sequence": 17,
        "action_class": "REAL_SCOPE_EXPANSION",
        "payload_sha256": payload_digest,
        "scope_sha256": "1" * 64,
        "limits_sha256": "2" * 64,
        "artifact_set_sha256": "3" * 64,
        "configuration_sha256": "4" * 64,
        "effective_from": "2026-07-24T00:00:00Z",
        "review_due_at": "2026-07-24T12:00:00.123456Z",
        "expires_at": "2026-07-25T00:00:00Z",
    }
    primary = {
        **common,
        "role": "PRIMARY_CRYPTOGRAPHIC_SIGNATURE",
        "factor_class": "PHYSICAL_HARDWARE_SIGNING_KEY",
        "factor_id": "factor:primary-1",
        "trust_root_id": "root:primary-1",
        "failure_domain_id": "failure:primary-1",
        "key_material_id": "key:primary-1",
        "device_id": "device:primary-1",
        "session_id": "session:primary-1",
        "admin_domain_id": "admin:primary-1",
        "recovery_path_id": "recovery:primary-1",
        "factor_evidence_ref": "evidence:primary-1",
    }
    confirmation = {
        **common,
        "role": "INDEPENDENT_SECOND_CONFIRMATION",
        "factor_class": "SEPARATE_DEVICE_CONFIRMATION",
        "factor_id": "factor:confirmation-1",
        "trust_root_id": "root:confirmation-1",
        "failure_domain_id": "failure:confirmation-1",
        "key_material_id": "key:confirmation-1",
        "device_id": "device:confirmation-1",
        "session_id": "session:confirmation-1",
        "admin_domain_id": "admin:confirmation-1",
        "recovery_path_id": "recovery:confirmation-1",
        "factor_evidence_ref": "evidence:confirmation-1",
    }
    return primary, confirmation


def _binding_result(
    primary: object,
    confirmation: object,
    primary_payload: object = b"\xff\x00opaque-not-json\x80",
    confirmation_payload: object = b"\xff\x00opaque-not-json\x80",
) -> str:
    return pm_dec007_hybrid_binding_shape_result(
        primary,
        confirmation,
        primary_payload,
        confirmation_payload,
    )


class PMDec007DecisionRecordTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = _load_decision()

    def test_exact_record_is_only_non_authorizing_shape_valid(self) -> None:
        self.assertEqual(
            self.record["integrity"]["decision_payload_sha256"],
            pm_dec007_payload_digest(self.record),
        )
        self.assertEqual([], validate_pm_dec007_record(self.record, ROOT))
        self.assertEqual(PM_DEC007_RECORD_VALID, pm_dec007_record_result(self.record, ROOT))
        self.assertEqual("NONE", self.record["authorization_effect"])
        self.assertIs(False, self.record["eligible_for_real_capital_authorization"])
        self.assertIs(False, self.record["live_trading_enabled"])

    def test_every_top_level_missing_field_and_extra_field_deny_after_redigest(self) -> None:
        for field in tuple(self.record):
            with self.subTest(missing=field):
                mutated = copy.deepcopy(self.record)
                mutated.pop(field)
                if field != "integrity":
                    _redigest(mutated)
                self.assertTrue(validate_pm_dec007_record(mutated, ROOT))
                self.assertEqual(
                    PM_DEC007_RECORD_INVALID,
                    pm_dec007_record_result(mutated, ROOT),
                )
        extra = copy.deepcopy(self.record)
        extra["runtime_authority"] = "ACTIVE"
        _redigest(extra)
        self.assertEqual(PM_DEC007_RECORD_INVALID, pm_dec007_record_result(extra, ROOT))

    def test_each_nested_table_rejects_missing_and_extra_fields(self) -> None:
        nested_tables = (
            "primary_factor",
            "independent_confirmation",
            "factor_independence",
            "same_payload_binding",
            "factor_lifecycle",
            "current_checkpoint",
            "unresolved_dependencies",
            "safety",
        )
        for table in nested_tables:
            field = next(iter(self.record[table]))
            with self.subTest(table=table, mutation="missing"):
                missing = copy.deepcopy(self.record)
                missing[table].pop(field)
                _redigest(missing)
                self.assertEqual(
                    PM_DEC007_RECORD_INVALID,
                    pm_dec007_record_result(missing, ROOT),
                )
            with self.subTest(table=table, mutation="extra"):
                extra = copy.deepcopy(self.record)
                extra[table]["extra"] = False
                _redigest(extra)
                self.assertEqual(
                    PM_DEC007_RECORD_INVALID,
                    pm_dec007_record_result(extra, ROOT),
                )

        artifact_extra = copy.deepcopy(self.record)
        artifact_extra["artifact_hashes"][0]["extra"] = "not-allowed"
        _redigest(artifact_extra)
        self.assertEqual(
            PM_DEC007_RECORD_INVALID,
            pm_dec007_record_result(artifact_extra, ROOT),
        )

        integrity_extra = copy.deepcopy(self.record)
        integrity_extra["integrity"]["extra"] = False
        self.assertEqual(
            PM_DEC007_RECORD_INVALID,
            pm_dec007_record_result(integrity_extra, ROOT),
        )

    def test_string_subclass_keys_deny_at_every_record_dictionary_depth(self) -> None:
        mutations = []

        top_level = copy.deepcopy(self.record)
        _replace_with_string_subclass_key(top_level, "decision_id")
        mutations.append(("top-level", top_level))

        nested_table = copy.deepcopy(self.record)
        _replace_with_string_subclass_key(nested_table["primary_factor"], "role")
        mutations.append(("nested-table", nested_table))

        artifact_item = copy.deepcopy(self.record)
        _replace_with_string_subclass_key(
            artifact_item["artifact_hashes"][0],
            "path",
        )
        mutations.append(("list-item-dictionary", artifact_item))

        for location, mutated in mutations:
            with self.subTest(location=location):
                mutated["integrity"]["decision_payload_sha256"] = (
                    pm_dec007_payload_digest(mutated)
                )
                self.assertEqual("", mutated["integrity"]["decision_payload_sha256"])
                self.assertTrue(validate_pm_dec007_record(mutated, ROOT))
                self.assertEqual(
                    PM_DEC007_RECORD_INVALID,
                    pm_dec007_record_result(mutated, ROOT),
                )

    def test_explosive_non_string_keys_deny_without_equality_lookup(self) -> None:
        class ExplosiveKey:
            def __init__(self) -> None:
                self.equality_calls = 0

            def __hash__(self) -> int:
                return hash("integrity")

            def __eq__(self, other: object) -> bool:
                self.equality_calls += 1
                raise AssertionError("hostile key equality must not execute")

        mutations = []

        top_level = copy.deepcopy(self.record)
        top_key = ExplosiveKey()
        top_level[top_key] = top_level.pop("integrity")
        mutations.append(("top-level", top_level, top_key))

        nested_table = copy.deepcopy(self.record)
        nested_key = ExplosiveKey()
        nested = nested_table["primary_factor"]
        nested[nested_key] = nested.pop("role")
        mutations.append(("nested-table", nested_table, nested_key))

        artifact_item = copy.deepcopy(self.record)
        artifact_key = ExplosiveKey()
        artifact = artifact_item["artifact_hashes"][0]
        artifact[artifact_key] = artifact.pop("path")
        mutations.append(("artifact-item", artifact_item, artifact_key))

        for location, mutated, hostile_key in mutations:
            with self.subTest(location=location):
                self.assertEqual("", pm_dec007_payload_digest(mutated))
                self.assertTrue(validate_pm_dec007_record(mutated, ROOT))
                self.assertEqual(
                    PM_DEC007_RECORD_INVALID,
                    pm_dec007_record_result(mutated, ROOT),
                )
                self.assertEqual(0, hostile_key.equality_calls)

    def test_authority_model_and_bool_int_coercion_mutations_deny(self) -> None:
        mutations = {
            "status": "RESOLVED",
            "implementation_status": "COMPLETE",
            "authorization_effect": "ALLOW",
            "eligible_for_real_capital_authorization": True,
            "artifact_ratification_eligible": True,
            "real_capital_authority": True,
            "pilot_status": "APPROVED",
            "production_status": "ACTIVE",
            "live_trading_enabled": True,
            "moex_status": "PRODUCTION",
            "selected_model": "SINGLE_FACTOR",
            "selected_option": True,
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                mutated = copy.deepcopy(self.record)
                mutated[field] = value
                _redigest(mutated)
                self.assertEqual(
                    PM_DEC007_RECORD_INVALID,
                    pm_dec007_record_result(mutated, ROOT),
                )

    def test_parent_governance_and_record_digest_mutations_deny(self) -> None:
        bound_paths = (
            "docs/FROZEN_CORE_V11.sha256",
            "governance/approval-policy.toml",
            "governance/risk-policy.toml",
            "specs/portfolio-mandate-v1/decisions/PM-DEC-003.toml",
        )
        for path in bound_paths:
            with self.subTest(path=path):
                mutated = copy.deepcopy(self.record)
                entry = next(
                    item for item in mutated["artifact_hashes"] if item["path"] == path
                )
                entry["sha256"] = "0" * 64
                _redigest(mutated)
                self.assertEqual(
                    PM_DEC007_RECORD_INVALID,
                    pm_dec007_record_result(mutated, ROOT),
                )

        parent_binding = copy.deepcopy(self.record)
        parent_binding["parent_frozen_manifest_sha256"] = "0" * 64
        _redigest(parent_binding)
        self.assertEqual(
            PM_DEC007_RECORD_INVALID,
            pm_dec007_record_result(parent_binding, ROOT),
        )

        bad_digest = copy.deepcopy(self.record)
        bad_digest["integrity"]["decision_payload_sha256"] = "0" * 64
        self.assertEqual(
            PM_DEC007_RECORD_INVALID,
            pm_dec007_record_result(bad_digest, ROOT),
        )

    def test_payload_digest_rejects_non_dictionary_or_non_json_types(self) -> None:
        self.assertEqual("", pm_dec007_payload_digest([]))
        mutated = copy.deepcopy(self.record)
        mutated["opaque_runtime_object"] = object()
        self.assertEqual("", pm_dec007_payload_digest(mutated))


class PMDec007HybridBindingTests(unittest.TestCase):
    payload = b"\xff\x00opaque-not-json\x80"

    def setUp(self) -> None:
        self.primary, self.confirmation = _factor_pair(self.payload)

    def assertShapeValid(self, primary: dict, confirmation: dict) -> None:
        self.assertEqual(
            PM_DEC007_BINDING_VALID,
            _binding_result(primary, confirmation, self.payload, self.payload),
        )

    def test_valid_pair_binds_two_identical_opaque_bytes_without_parsing(self) -> None:
        self.assertEqual(FACTOR_FIELDS, frozenset(self.primary))
        self.assertEqual(FACTOR_FIELDS, frozenset(self.confirmation))
        self.assertShapeValid(self.primary, self.confirmation)

    def test_each_factor_field_is_required_and_objects_are_closed(self) -> None:
        for side in ("primary", "confirmation"):
            for field in sorted(FACTOR_FIELDS):
                with self.subTest(side=side, missing=field):
                    primary = copy.deepcopy(self.primary)
                    confirmation = copy.deepcopy(self.confirmation)
                    target = primary if side == "primary" else confirmation
                    target.pop(field)
                    self.assertEqual(
                        PM_DEC007_FACTOR_SHAPE_INVALID,
                        _binding_result(primary, confirmation),
                    )
            with self.subTest(side=side, extra="benign_note"):
                primary = copy.deepcopy(self.primary)
                confirmation = copy.deepcopy(self.confirmation)
                target = primary if side == "primary" else confirmation
                target["benign_note"] = 7
                self.assertEqual(
                    PM_DEC007_FACTOR_SHAPE_INVALID,
                    _binding_result(primary, confirmation),
                )

    def test_each_distinct_dimension_must_differ(self) -> None:
        self.assertEqual(
            {
                "factor_id",
                "trust_root_id",
                "failure_domain_id",
                "key_material_id",
                "device_id",
                "session_id",
                "admin_domain_id",
                "recovery_path_id",
                "factor_evidence_ref",
            },
            set(DISTINCT_FIELDS),
        )
        for field in DISTINCT_FIELDS:
            with self.subTest(shared=field):
                confirmation = copy.deepcopy(self.confirmation)
                confirmation[field] = self.primary[field]
                self.assertEqual(
                    PM_DEC007_FACTORS_NOT_INDEPENDENT,
                    _binding_result(self.primary, confirmation),
                )

    def test_each_equal_binding_mismatch_denies(self) -> None:
        alternate_values = {
            "trust_set_id": "trust-set:other",
            "owner_identity_ref": "owner:other",
            "owner_trust_epoch": 3,
            "global_sequence_namespace_id": "level-b:other-sequence",
            "manifest_id": "manifest:other",
            "manifest_version": 5,
            "monotonic_sequence": 18,
            "action_class": "HARD_LIMIT_INCREASE",
            "payload_sha256": "5" * 64,
            "scope_sha256": "6" * 64,
            "limits_sha256": "7" * 64,
            "artifact_set_sha256": "8" * 64,
            "configuration_sha256": "9" * 64,
            "effective_from": "2026-07-24T00:00:01Z",
            "review_due_at": "2026-07-24T12:00:01Z",
            "expires_at": "2026-07-25T00:00:01Z",
        }
        self.assertEqual(
            {"factor_record_version", *alternate_values},
            set(EQUAL_BINDING_FIELDS),
        )
        for field, value in alternate_values.items():
            with self.subTest(mismatched=field):
                confirmation = copy.deepcopy(self.confirmation)
                confirmation[field] = value
                self.assertEqual(
                    PM_DEC007_PAYLOAD_BINDING_MISMATCH,
                    _binding_result(self.primary, confirmation),
                )

        version_mismatch = copy.deepcopy(self.confirmation)
        version_mismatch["factor_record_version"] = 2
        self.assertEqual(
            PM_DEC007_FACTOR_SHAPE_INVALID,
            _binding_result(self.primary, version_mismatch),
        )

    def test_strict_integer_types_reject_bool_float_string_and_subclasses(self) -> None:
        class IntegerSubclass(int):
            pass

        invalid_values = (True, False, 1.0, "1", IntegerSubclass(1))
        for field in ("factor_record_version", *POSITIVE_INTEGER_FIELDS):
            for value in invalid_values:
                with self.subTest(field=field, value_type=type(value).__name__):
                    primary = copy.deepcopy(self.primary)
                    primary[field] = value
                    self.assertEqual(
                        PM_DEC007_FACTOR_SHAPE_INVALID,
                        _binding_result(primary, self.confirmation),
                    )
        for field in POSITIVE_INTEGER_FIELDS:
            for value in (0, -1):
                with self.subTest(field=field, nonpositive=value):
                    primary = copy.deepcopy(self.primary)
                    primary[field] = value
                    self.assertEqual(
                        PM_DEC007_FACTOR_SHAPE_INVALID,
                        _binding_result(primary, self.confirmation),
                    )

    def test_token_grammar_and_strict_string_type(self) -> None:
        class StringSubclass(str):
            pass

        invalid_values = (
            "",
            "-starts-with-punctuation",
            "contains/slash",
            "nonascii-é",
            "a" * 129,
            7,
            True,
            StringSubclass("apparently-valid"),
        )
        for field in TOKEN_FIELDS:
            for value in invalid_values:
                with self.subTest(field=field, value=repr(value)):
                    primary = copy.deepcopy(self.primary)
                    primary[field] = value
                    self.assertEqual(
                        PM_DEC007_FACTOR_SHAPE_INVALID,
                        _binding_result(primary, self.confirmation),
                    )

    def test_hash_grammar_is_lowercase_exact_and_locally_recomputed(self) -> None:
        for field in DIGEST_FIELDS:
            for value in ("A" * 64, "a" * 63, "g" * 64, True, 7):
                with self.subTest(field=field, value=repr(value)):
                    primary = copy.deepcopy(self.primary)
                    primary[field] = value
                    self.assertEqual(
                        PM_DEC007_FACTOR_SHAPE_INVALID,
                        _binding_result(primary, self.confirmation),
                    )

        wrong_digest_primary = copy.deepcopy(self.primary)
        wrong_digest_confirmation = copy.deepcopy(self.confirmation)
        wrong_digest_primary["payload_sha256"] = "a" * 64
        wrong_digest_confirmation["payload_sha256"] = "a" * 64
        self.assertEqual(
            PM_DEC007_PAYLOAD_BINDING_MISMATCH,
            _binding_result(wrong_digest_primary, wrong_digest_confirmation),
        )

    def test_payload_inputs_require_exact_equal_bytes(self) -> None:
        class BytesSubclass(bytes):
            pass

        cases = (
            ("primary-string", "opaque", self.payload),
            ("confirmation-bytearray", self.payload, bytearray(self.payload)),
            ("memoryview", memoryview(self.payload), self.payload),
            ("bytes-subclass", BytesSubclass(self.payload), self.payload),
            ("unequal", self.payload, self.payload + b"!"),
        )
        for name, primary_payload, confirmation_payload in cases:
            with self.subTest(name=name):
                self.assertEqual(
                    PM_DEC007_PAYLOAD_BINDING_MISMATCH,
                    _binding_result(
                        self.primary,
                        self.confirmation,
                        primary_payload,
                        confirmation_payload,
                    ),
                )

    def test_exact_roles_and_factor_classes_are_not_caller_labels(self) -> None:
        mutations = (
            ("primary", "role", "INDEPENDENT_SECOND_CONFIRMATION"),
            ("primary", "factor_class", "SEPARATE_DEVICE_CONFIRMATION"),
            ("confirmation", "role", "PRIMARY_CRYPTOGRAPHIC_SIGNATURE"),
            ("confirmation", "factor_class", "PHYSICAL_HARDWARE_SIGNING_KEY"),
        )
        for side, field, value in mutations:
            with self.subTest(side=side, field=field):
                primary = copy.deepcopy(self.primary)
                confirmation = copy.deepcopy(self.confirmation)
                target = primary if side == "primary" else confirmation
                target[field] = value
                self.assertEqual(
                    PM_DEC007_FACTOR_SHAPE_INVALID,
                    _binding_result(primary, confirmation),
                )

    def test_strict_utc_grammar_and_real_calendar_validation(self) -> None:
        invalid_timestamps = (
            "2026-07-24 00:00:00Z",
            "2026-07-24T00:00:00+00:00",
            "2026-07-24T00:00:00.1234567Z",
            "2026-02-30T00:00:00Z",
            "2026-07-24T24:00:00Z",
            "۲۰۲۶-07-24T00:00:00Z",
            True,
        )
        for field in ("effective_from", "review_due_at", "expires_at"):
            for value in invalid_timestamps:
                with self.subTest(field=field, value=repr(value)):
                    primary = copy.deepcopy(self.primary)
                    confirmation = copy.deepcopy(self.confirmation)
                    primary[field] = value
                    confirmation[field] = value
                    self.assertEqual(
                        PM_DEC007_FACTOR_SHAPE_INVALID,
                        _binding_result(primary, confirmation),
                    )

    def test_timestamps_must_be_strictly_ordered(self) -> None:
        invalid_orders = (
            (
                "2026-07-24T12:00:00Z",
                "2026-07-24T12:00:00Z",
                "2026-07-25T00:00:00Z",
            ),
            (
                "2026-07-24T00:00:00Z",
                "2026-07-25T00:00:00Z",
                "2026-07-25T00:00:00Z",
            ),
            (
                "2026-07-25T00:00:00Z",
                "2026-07-24T12:00:00Z",
                "2026-07-24T00:00:00Z",
            ),
        )
        for effective, review, expires in invalid_orders:
            with self.subTest(order=(effective, review, expires)):
                primary = copy.deepcopy(self.primary)
                confirmation = copy.deepcopy(self.confirmation)
                for factor in (primary, confirmation):
                    factor["effective_from"] = effective
                    factor["review_due_at"] = review
                    factor["expires_at"] = expires
                self.assertEqual(
                    PM_DEC007_FACTOR_SHAPE_INVALID,
                    _binding_result(primary, confirmation),
                )

    def test_caller_boolean_and_string_truth_claims_deny(self) -> None:
        claims = {
            "signature_valid": True,
            "device_valid": True,
            "checkpoint_current": True,
            "factors_independent": True,
            "authority_status": "APPROVED",
            "stage": "PILOT",
            "evidence_status": "EVIDENCE_READY",
            "runtime_truth": "VERIFIED",
            "production_status": "ACTIVE",
        }
        for key, value in claims.items():
            with self.subTest(key=key, value=value):
                primary = copy.deepcopy(self.primary)
                primary[key] = value
                self.assertEqual(
                    PM_DEC007_CALLER_AUTHORITY_CLAIM,
                    _binding_result(primary, self.confirmation),
                )

        for action_claim in ("ACTIVE", "VERIFIED", "PILOT", "PRODUCTION"):
            with self.subTest(action_claim=action_claim):
                primary = copy.deepcopy(self.primary)
                confirmation = copy.deepcopy(self.confirmation)
                primary["action_class"] = action_claim
                confirmation["action_class"] = action_claim
                self.assertEqual(
                    PM_DEC007_CALLER_AUTHORITY_CLAIM,
                    _binding_result(primary, confirmation),
                )

    def test_old_positive_sequence_and_arbitrary_interval_are_shape_only(self) -> None:
        primary = copy.deepcopy(self.primary)
        confirmation = copy.deepcopy(self.confirmation)
        for factor in (primary, confirmation):
            factor["monotonic_sequence"] = 1
            factor["effective_from"] = "1900-01-01T00:00:00Z"
            factor["review_due_at"] = "2099-01-01T00:00:00Z"
            factor["expires_at"] = "9999-12-31T23:59:59.999999Z"

        self.assertShapeValid(primary, confirmation)
        self.assertShapeValid(primary, confirmation)
        self.assertEqual(
            PM_DEC007_RUNTIME_TRUST_INCOMPLETE,
            pm_dec007_authority_readiness_result(
                primary=primary,
                confirmation=confirmation,
                interval_status="ACTIVE",
                replay_status="FRESH",
            ),
        )

    def test_dictionary_subclasses_are_rejected(self) -> None:
        class DictSubclass(dict):
            pass

        self.assertEqual(
            PM_DEC007_FACTOR_SHAPE_INVALID,
            _binding_result(DictSubclass(self.primary), self.confirmation),
        )

    def test_string_subclass_keys_deny_for_both_factor_objects(self) -> None:
        for side in ("primary", "confirmation"):
            with self.subTest(side=side):
                primary = copy.deepcopy(self.primary)
                confirmation = copy.deepcopy(self.confirmation)
                target = primary if side == "primary" else confirmation
                _replace_with_string_subclass_key(target, "factor_id")
                self.assertEqual(
                    PM_DEC007_FACTOR_SHAPE_INVALID,
                    _binding_result(primary, confirmation),
                )

    def test_explosive_non_string_factor_keys_deny_without_equality_lookup(self) -> None:
        class ExplosiveKey:
            def __init__(self) -> None:
                self.equality_calls = 0

            def __hash__(self) -> int:
                return hash("integrity")

            def __eq__(self, other: object) -> bool:
                self.equality_calls += 1
                raise AssertionError("hostile key equality must not execute")

        for side in ("primary", "confirmation"):
            with self.subTest(side=side):
                primary = copy.deepcopy(self.primary)
                confirmation = copy.deepcopy(self.confirmation)
                target = primary if side == "primary" else confirmation
                hostile_key = ExplosiveKey()
                target[hostile_key] = target.pop("factor_id")
                self.assertEqual(
                    PM_DEC007_FACTOR_SHAPE_INVALID,
                    _binding_result(primary, confirmation),
                )
                self.assertEqual(0, hostile_key.equality_calls)


class PMDec007CheckpointAndReadinessTests(unittest.TestCase):
    def test_all_checkpoint_claim_variants_have_the_same_unavailable_result(self) -> None:
        claims = {
            "empty-none": None,
            "empty-dict": {},
            "malformed": {"head": object()},
            "apparently-complete": {
                "registry_id": "registry-1",
                "genesis_sha256": "a" * 64,
                "head_sequence": 17,
                "head_sha256": "b" * 64,
            },
            "self-declared-current": {"current": True, "trusted": True},
            "self-declared-durable": {"durable": True, "complete": True},
            "old-well-formed": {"head_sequence": 1, "status": "OLD"},
            "cached-genesis": {"head_sequence": 0, "source": "CACHE"},
            "truncated": {"head_sequence": 17, "records": []},
            "exact-replay": [{"sequence": 17}, {"sequence": 17}],
            "forked": {"heads": ["a" * 64, "b" * 64]},
            "wrong-root": {"checkpoint_trust_root_id": "factor-root"},
            "replacement-old-epoch": {"owner_trust_epoch": 1, "replacement": True},
        }
        for name, claim in claims.items():
            with self.subTest(name=name):
                self.assertEqual(
                    PM_DEC007_CHECKPOINT_UNAVAILABLE,
                    pm_dec007_checkpoint_claim_result(claim),
                )

    def test_checkpoint_claim_is_not_inspected(self) -> None:
        class ExplosiveClaim:
            def __getattribute__(self, name: str) -> object:
                raise AssertionError(f"checkpoint claim was inspected: {name}")

        self.assertEqual(
            PM_DEC007_CHECKPOINT_UNAVAILABLE,
            pm_dec007_checkpoint_claim_result(ExplosiveClaim()),
        )

    def test_readiness_always_denies_and_never_calls_adapter(self) -> None:
        class AdapterSpy:
            def __init__(self) -> None:
                self.calls = 0

            def __call__(self, *args: object, **kwargs: object) -> object:
                self.calls += 1
                raise AssertionError("adapter must never be called")

        primary, confirmation = _factor_pair()
        keyword_spy = AdapterSpy()
        positional_spy = AdapterSpy()
        result = pm_dec007_authority_readiness_result(
            positional_spy,
            record=_load_decision(),
            primary=primary,
            confirmation=confirmation,
            checkpoint={"current": True},
            stage="PRODUCTION",
            evidence_status="EVIDENCE_READY",
            arbitrary_interval_seconds=10**12,
            adapter_call=keyword_spy,
        )
        self.assertEqual(PM_DEC007_RUNTIME_TRUST_INCOMPLETE, result)
        self.assertEqual(0, keyword_spy.calls)
        self.assertEqual(0, positional_spy.calls)

        self.assertEqual(
            PM_DEC007_RUNTIME_TRUST_INCOMPLETE,
            pm_dec007_authority_readiness_result(),
        )
        self.assertEqual(
            PM_DEC007_RUNTIME_TRUST_INCOMPLETE,
            pm_dec007_authority_readiness_result(
                adapter_call="caller-says-adapter-already-called"
            ),
        )


class PMDec007RepositoryEvidenceTests(unittest.TestCase):
    def test_historical_v11_is_immutable_and_active_v12_passes_10_of_10(self) -> None:
        historical = ROOT / HISTORICAL_CORE_MANIFEST
        self.assertEqual(
            HISTORICAL_CORE_MANIFEST_SHA256,
            hashlib.sha256(historical.read_bytes()).hexdigest(),
        )
        historical_entries = _manifest_entries(HISTORICAL_CORE_MANIFEST)
        self.assertEqual(
            FROZEN_CORE_V11_PATHS,
            tuple(path for path, _ in historical_entries),
        )
        self.assertNotEqual(
            dict(historical_entries)["scripts/self_check.py"],
            hashlib.sha256((ROOT / "scripts/self_check.py").read_bytes()).hexdigest(),
        )

        active = ROOT / ACTIVE_CORE_MANIFEST
        self.assertEqual(
            ACTIVE_CORE_MANIFEST_SHA256,
            hashlib.sha256(active.read_bytes()).hexdigest(),
        )
        active_entries = _manifest_entries(ACTIVE_CORE_MANIFEST)
        self.assertEqual(FROZEN_CORE_V12_PATHS, tuple(path for path, _ in active_entries))
        self.assertEqual(10, len(active_entries))
        for relative, expected_digest in active_entries:
            with self.subTest(relative=relative):
                self.assertEqual(
                    expected_digest,
                    hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(),
                )

    def test_historical_pm_v1_is_immutable_and_active_pm_v2_passes(self) -> None:
        historical = ROOT / HISTORICAL_PM_MANIFEST
        self.assertEqual(
            HISTORICAL_PM_MANIFEST_SHA256,
            hashlib.sha256(historical.read_bytes()).hexdigest(),
        )
        v1_entries = _manifest_entries(HISTORICAL_PM_MANIFEST)
        v2_entries = _manifest_entries(ACTIVE_PM_MANIFEST)
        self.assertEqual(FROZEN_PM_DEC007_PATHS, tuple(path for path, _ in v1_entries))
        self.assertEqual(FROZEN_PM_DEC007_PATHS, tuple(path for path, _ in v2_entries))
        v1 = dict(v1_entries)
        v2 = dict(v2_entries)
        self.assertEqual(
            {"scripts/check_pm_dec007_hybrid.py", "tests/test_pm_dec007_hybrid.py"},
            {path for path in v1 if v1[path] != v2[path]},
        )
        for relative, expected_digest in v2_entries:
            with self.subTest(relative=relative):
                self.assertEqual(
                    expected_digest,
                    hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(),
                )

    def test_pm_dec003_v1_bytes_and_live_disabled_invariants_are_unchanged(self) -> None:
        pm_dec003 = ROOT / "specs/portfolio-mandate-v1/decisions/PM-DEC-003.toml"
        self.assertEqual(
            PM_DEC003_V1_SHA256,
            hashlib.sha256(pm_dec003.read_bytes()).hexdigest(),
        )
        record = _load_decision()
        bound = {
            entry["path"]: entry["sha256"] for entry in record["artifact_hashes"]
        }
        self.assertEqual(
            PM_DEC003_V1_SHA256,
            bound["specs/portfolio-mandate-v1/decisions/PM-DEC-003.toml"],
        )
        self.assertIs(False, record["live_trading_enabled"])
        self.assertEqual("BLOCKED", record["pilot_status"])
        self.assertEqual("BLOCKED", record["production_status"])

    def test_cli_record_spec_acceptance_and_task_traceability_passes(self) -> None:
        self.assertEqual([], run_checks(ROOT))
        completed = subprocess.run(
            [sys.executable, "scripts/check_pm_dec007_hybrid.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertIn("PM-DEC-007 HYBRID CHECK: PASS", completed.stdout)

    def test_cli_prints_fail_and_returns_nonzero_on_deterministic_error(self) -> None:
        output = io.StringIO()
        with mock.patch(
            "scripts.check_pm_dec007_hybrid.run_checks",
            return_value=["deterministic failure"],
        ):
            with redirect_stdout(output):
                result = main()
        self.assertEqual(1, result)
        self.assertIn("PM-DEC-007 HYBRID CHECK: FAIL", output.getvalue())
        self.assertIn("deterministic failure", output.getvalue())

    def test_malformed_toml_fails_deterministically_without_traceback(self) -> None:
        malformed_documents = {
            "invalid-utf8": b"\xff",
            "toml-syntax": b"[",
            "oversized-integer": (
                b"decision_version = " + (b"9" * 5000) + b"\n"
            ),
        }
        for name, raw_document in malformed_documents.items():
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as temporary:
                    temporary_root = Path(temporary)
                    decision = (
                        temporary_root
                        / "specs/pm-dec-007-hybrid-trust-v1/decisions/PM-DEC-007.toml"
                    )
                    decision.parent.mkdir(parents=True)
                    decision.write_bytes(raw_document)

                    self.assertEqual(
                        ["PM-DEC-007 decision record unavailable or malformed"],
                        run_checks(temporary_root),
                    )
                    output = io.StringIO()
                    with redirect_stdout(output):
                        result = main(temporary_root)
                    self.assertEqual(1, result)
                    self.assertEqual(
                        "PM-DEC-007 HYBRID CHECK: FAIL\n"
                        "- PM-DEC-007 decision record unavailable or malformed\n",
                        output.getvalue(),
                    )
                    self.assertNotIn("Traceback", output.getvalue())

        with mock.patch(
            "scripts.check_pm_dec007_hybrid._load_toml",
            side_effect=RecursionError("nested TOML"),
        ):
            self.assertEqual(
                ["PM-DEC-007 decision record unavailable or malformed"],
                run_checks(ROOT),
            )

    def test_invalid_utf8_frozen_manifest_fails_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            copied_paths = {
                "specs/pm-dec-007-hybrid-trust-v1/decisions/PM-DEC-007.toml",
                "specs/pm-dec-007-hybrid-trust-v1/tasks.md",
                *[path for path, _ in REQUIRED_ARTIFACT_HASHES],
                ACTIVE_CORE_MANIFEST,
                HISTORICAL_PM_MANIFEST,
                ACTIVE_PM_MANIFEST,
                *FROZEN_CORE_V12_PATHS,
                *FROZEN_PM_DEC007_PATHS,
            }
            for relative in copied_paths:
                destination = temporary_root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((ROOT / relative).read_bytes())

            frozen_manifest = temporary_root / HISTORICAL_CORE_MANIFEST
            frozen_manifest.write_bytes(b"\xff")

            errors = run_checks(temporary_root)
            self.assertEqual(
                [
                    "PM-DEC-007 bound artifact hash mismatch: "
                    "docs/FROZEN_CORE_V11.sha256",
                    "historical v11 manifest unavailable or malformed",
                ],
                errors,
            )
            output = io.StringIO()
            with redirect_stdout(output):
                result = main(temporary_root)
            self.assertEqual(1, result)
            self.assertIn("PM-DEC-007 HYBRID CHECK: FAIL", output.getvalue())
            self.assertIn(
                "- historical v11 manifest unavailable or malformed",
                output.getvalue(),
            )
            self.assertNotIn("Traceback", output.getvalue())


if __name__ == "__main__":
    unittest.main()
