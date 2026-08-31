from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import tempfile
import tomllib
import unittest
import zipfile
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.self_check import (
    PM_DEC002_BOUND_FACTOR_FIELDS,
    PM_DEC002_REAL_CAPITAL_ACTIONS,
    PM_DEC003_INDEPENDENT_VALIDITY_OBJECTS,
    PM_NORMATIVE_CAPITAL_STAGES,
    ACTIVE_SCHEMA_UNAVAILABLE,
    B4_CANONICAL_PAYLOAD_FIELDS,
    CROSS_RISK_SCOPE_FIELDS,
    RUNTIME_SEMANTIC_SCOPE_FIELDS,
    _venue_mechanics_result,
    canonical_json_bytes,
    canonical_json_bytes_result,
    level_b_factor_binding_result,
    evaluate_pm_dec003_temporal_validity,
    pm_dec003_independent_validity_result,
    pm_dec003_protective_exposure_result,
    pm_dec003_working_order_sunset_result,
    pm_dec002_payload_digest,
    pm_dec003_payload_digest,
    validate_schema_subset,
    validate_level_b_factor_binding,
    validate_pm_dec002_record,
    validate_pm_dec003_record,
    validate_pm_dec003_v2_record,
    validate_validity_profile_draft,
    validity_profile_lookup_result,
    validity_profile_monotone_result,
    validity_profile_feasibility_result,
    validity_profile_transition_result,
    validity_profile_payload_digest,
    validity_profile_tuple_result,
    validity_profile_owner_authority_result,
    validity_profile_owner_bounds_result,
    validity_profile_timestamp_binding_result,
    validity_artifact_scope_result,
    validity_evidence_manifest_result,
    validity_active_runtime_contract_result,
    validity_profile_b4_registry_shape_result,
    validity_profile_authority_change_result,
    validity_profile_operating_manifest_result,
    validity_reconciliation_escalation_result,
    validity_profile_sunset_result,
    validity_profile_cross_risk_result,
    validate_release_snapshot_members,
)


ROOT = Path(__file__).resolve().parents[1]
MANDATE = ROOT / "specs/portfolio-mandate-v1/mandate.example.toml"
DECISION_002 = ROOT / "specs/portfolio-mandate-v1/decisions/PM-DEC-002.toml"
DECISION_003 = ROOT / "specs/portfolio-mandate-v1/decisions/PM-DEC-003.toml"
DECISION_003_V2 = ROOT / "specs/portfolio-mandate-v1/decisions/PM-DEC-003-v2.toml"
PROFILE = ROOT / "specs/portfolio-mandate-v1/validity-profiles/bitget-pilot-draft-v1.toml"
PROFILE_SCHEMA = ROOT / "specs/portfolio-mandate-v1/validity-profiles/validity-profile.schema.json"


class PortfolioMandateTests(unittest.TestCase):
    def setUp(self) -> None:
        with MANDATE.open("rb") as handle:
            self.mandate = tomllib.load(handle)
        with DECISION_002.open("rb") as handle:
            self.decision_002 = tomllib.load(handle)
        with DECISION_003.open("rb") as handle:
            self.decision_003 = tomllib.load(handle)
        with DECISION_003_V2.open("rb") as handle:
            self.decision_003_v2 = tomllib.load(handle)
        with PROFILE.open("rb") as handle:
            self.profile = tomllib.load(handle)
        self.profile_schema = json.loads(PROFILE_SCHEMA.read_text(encoding="utf-8"))

    def test_draft_grants_no_real_trading_authority(self) -> None:
        self.assertEqual("NON_AUTHORIZING_DRAFT_EXAMPLE", self.mandate["artifact_purpose"])
        self.assertEqual("BLOCKED", self.mandate["status"])
        self.assertEqual("DENY", self.mandate["authorization_result"])
        self.assertIs(False, self.mandate["live_trading_enabled"])
        self.assertTrue(
            all(book["real_trading_authority"] is False for book in self.mandate["capital_books"])
        )
        self.assertTrue(
            all(
                scope["authorization_effect"] == "DENY_REAL_ORDERS"
                and scope["trading_endpoint_access"] is False
                and scope["real_capital_authority"] is False
                and scope["credential_profile_ref"] == "NO_REAL_ORDER_CREDENTIAL"
                for scope in self.mandate["scopes"]
            )
        )

    def test_adaptive_layer_can_only_follow_owner_hard_cap(self) -> None:
        self.assertEqual(
            [
                "OWNER_HARD_CAP",
                "PROTECTION_STATE",
                "ADAPTIVE_ONLY_DOWN",
                "PORTFOLIO_ALLOCATOR",
                "STRATEGY_BOT_CAP",
                "ORDER_INTENT",
            ],
            self.mandate["risk_hierarchy"],
        )

    def test_non_capital_overlay_is_active_without_order_authority(self) -> None:
        self.assertEqual("ACTIVE_NON_CAPITAL", self.mandate["normative_overlay_status"])
        self.assertEqual(
            ["DEVELOPMENT", "RESEARCH", "REPLAY", "DRY_RUN", "PAPER"],
            self.mandate["permitted_non_capital_lifecycle"],
        )
        self.assertEqual(
            ["decisions/PM-DEC-001.toml", "decisions/PM-DEC-002.toml"],
            self.mandate["resolved_decision_refs"],
        )
        self.assertEqual(
            ["decisions/PM-DEC-003-v2.toml"],
            self.mandate["partially_resolved_decision_refs"],
        )
        self.assertEqual("DENY", self.mandate["authorization_result"])

    def test_normative_stage_enum_matches_schema_and_tuple_validator(self) -> None:
        normative = [
            "DEVELOPMENT",
            "RESEARCH",
            "REPLAY",
            "DRY_RUN",
            "PAPER",
            "PILOT_LIMITED_LIVE",
            "PRODUCTION_LIVE",
        ]
        stage_section = (
            (ROOT / "specs/portfolio-mandate-v1/spec.md")
            .read_text(encoding="utf-8")
            .split("### 3.2. Стадия", 1)[1]
            .split("### 3.3. Книги капитала", 1)[0]
        )
        documented = [
            line.split("`", 2)[1]
            for line in stage_section.splitlines()
            if line.startswith("- `")
        ]
        self.assertEqual(normative, documented)
        self.assertEqual(normative, list(PM_NORMATIVE_CAPITAL_STAGES))
        self.assertEqual(
            normative,
            self.profile_schema["properties"]["exact_key"]["properties"][
                "capital_stage"
            ]["enum"],
        )
        accepted: list[str] = []
        for stage in normative:
            candidate = copy.deepcopy(self.profile)
            if stage in normative[:5]:
                candidate["exact_key"].update({
                    "venue_environment": "PAPER_SIMULATOR",
                    "capital_stage": stage,
                    "approval_tier": "LEVEL_A",
                    "validity_mode": "LONG_LIVED_NON_CAPITAL",
                    "action_class": "NON_CAPITAL",
                    "risk_class": "A0_NON_CAPITAL",
                })
            elif stage == "PILOT_LIMITED_LIVE":
                candidate["exact_key"].update({
                    "capital_stage": stage,
                    "action_class": "PILOT_OPERATING_SCOPE",
                    "risk_class": "B1_LIMITED_PILOT",
                })
            else:
                candidate["exact_key"].update({
                    "capital_stage": stage,
                    "action_class": "PRODUCTION_OPERATING_SCOPE",
                    "risk_class": "B2_EXISTING_PRODUCTION",
                })
            if validity_profile_tuple_result(
                candidate,
                require_numeric_values=False,
            ) == "NON_AUTHORIZING_COHERENT_PROFILE_TUPLE":
                accepted.append(stage)
        self.assertEqual(normative, accepted)
        unknown = copy.deepcopy(self.profile)
        unknown["exact_key"]["capital_stage"] = "STAGING"
        self.assertEqual(
            "DENY_UNKNOWN_CLOSED_TAXONOMY_VALUE",
            validity_profile_tuple_result(
                unknown,
                require_numeric_values=False,
            ),
        )

    def test_differentiated_validity_model_is_partial_and_non_authorizing(self) -> None:
        self.assertEqual(
            "EXACT_VENUE_RISK_STAGE_PROFILE", self.mandate["validity_model"]
        )
        self.assertEqual("LONG_LIVED_NON_CAPITAL", self.mandate["level_a_validity_mode"])
        self.assertEqual(
            ["TIME_BOXED_REAL_CAPITAL", "ONE_TIME_REAL_CAPITAL"],
            self.mandate["level_b_allowed_validity_modes"],
        )
        self.assertEqual("OWNER_INPUT_REQUIRED", self.mandate["numeric_validity_profile_status"])
        self.assertIs(False, self.mandate["real_capital_validity_eligible"])
        self.assertIs(False, self.decision_003["baseline_snapshot_authoritative"])
        self.assertEqual(
            "PENDING_PM-DEC-007",
            self.decision_003["baseline_snapshot_trust_anchor_status"],
        )
        self.assertIs(False, self.decision_003["artifact_ratification_eligible"])
        self.assertEqual(
            [f"PM-DEC-{index:03d}" for index in range(4, 16)],
            [item["decision_id"] for item in self.mandate["unresolved_decisions"]],
        )
        self.assertEqual([], validate_pm_dec003_record(self.decision_003, ROOT))

    def test_two_tier_owner_approval_is_fail_closed_for_real_capital(self) -> None:
        self.assertEqual("TWO_TIER", self.mandate["owner_approval_model"])
        self.assertEqual("VERSIONED_OWNER_DECISION_RECORD", self.mandate["non_capital_approval"])
        self.assertEqual(
            "CRYPTOGRAPHIC_SIGNATURE_PLUS_INDEPENDENT_SECOND_CONFIRMATION",
            self.mandate["real_capital_approval"],
        )
        self.assertIs(False, self.mandate["real_capital_approval_eligible"])
        self.assertEqual("PM-DEC-007", self.mandate["real_capital_approval_blocked_until"])

    def test_level_a_record_rejects_artifact_and_payload_mutation(self) -> None:
        self.assertEqual([], validate_pm_dec002_record(self.decision_002, ROOT))

        artifact_mutation = copy.deepcopy(self.decision_002)
        artifact_mutation["artifact_hashes"][0]["sha256"] = "0" * 64
        artifact_mutation["integrity"]["decision_payload_sha256"] = pm_dec002_payload_digest(
            artifact_mutation
        )
        self.assertTrue(validate_pm_dec002_record(artifact_mutation, ROOT))

        payload_mutation = copy.deepcopy(self.decision_002)
        payload_mutation["level_a_non_capital"]["may_ratify_results_post_hoc"] = True
        self.assertTrue(validate_pm_dec002_record(payload_mutation, ROOT))

        narrowed_real_actions = copy.deepcopy(self.decision_002)
        narrowed_real_actions["level_b_real_capital"]["applies_to"].remove(
            "HARD_LIMIT_INCREASE"
        )
        narrowed_real_actions["integrity"]["decision_payload_sha256"] = (
            pm_dec002_payload_digest(narrowed_real_actions)
        )
        self.assertTrue(validate_pm_dec002_record(narrowed_real_actions, ROOT))
        self.assertEqual(
            list(PM_DEC002_REAL_CAPITAL_ACTIONS),
            self.decision_002["level_b_real_capital"]["applies_to"],
        )

        missing_hash = copy.deepcopy(self.decision_002)
        missing_hash["artifact_hashes"].pop()
        missing_hash["integrity"]["decision_payload_sha256"] = pm_dec002_payload_digest(
            missing_hash
        )
        self.assertTrue(validate_pm_dec002_record(missing_hash, ROOT))

    def test_pm_dec002_v04_snapshot_is_non_authoritative_and_prevents_rebinding(self) -> None:
        """The snapshot is a consistency check, never ratification evidence."""
        with tempfile.TemporaryDirectory() as temporary:
            archive_root = Path(temporary)
            shutil.copy(ROOT / "portfolio-mandate-v0.4.zip", archive_root)
            self.assertEqual([], validate_pm_dec002_record(self.decision_002, archive_root))
        with zipfile.ZipFile(ROOT / "portfolio-mandate-v0.4.zip") as archive:
            snapshot = archive.read(
                "specs/portfolio-mandate-v1/decisions/PM-DEC-002.toml"
            )
        self.assertEqual(DECISION_002.read_bytes(), snapshot)

    def test_level_b_factors_deny_every_binding_or_independence_mismatch(self) -> None:
        signature = {
            "manifest_id": "manifest-1",
            "payload_sha256": "a" * 64,
            "sequence": 7,
            "scope_sha256": "b" * 64,
            "limits_sha256": "c" * 64,
            "expires_at": "2026-07-18T00:00:00Z",
            "trust_root_id": "owner-signing-key",
            "failure_domain_id": "hardware-token",
        }
        second = {
            **signature,
            "trust_root_id": "owner-confirmation-root",
            "failure_domain_id": "separate-confirmation-channel",
        }
        validation = {
            "now_utc": datetime(2026, 7, 17, tzinfo=timezone.utc),
            "last_accepted_sequence": 6,
            "max_ttl_seconds": 86_400,
        }
        self.assertEqual([], validate_level_b_factor_binding(signature, second, **validation))
        self.assertEqual("DENY", level_b_factor_binding_result(signature, second, **validation))
        for field in PM_DEC002_BOUND_FACTOR_FIELDS:
            mismatched = copy.deepcopy(second)
            mismatched[field] = f"different-{field}"
            self.assertTrue(validate_level_b_factor_binding(signature, mismatched, **validation))
            self.assertEqual(
                "DENY", level_b_factor_binding_result(signature, mismatched, **validation)
            )
        for field in PM_DEC002_BOUND_FACTOR_FIELDS:
            incomplete_signature = copy.deepcopy(signature)
            incomplete_second = copy.deepcopy(second)
            incomplete_signature.pop(field)
            incomplete_second.pop(field)
            self.assertTrue(
                validate_level_b_factor_binding(
                    incomplete_signature, incomplete_second, **validation
                )
            )
            self.assertEqual(
                "DENY",
                level_b_factor_binding_result(
                    incomplete_signature, incomplete_second, **validation
                ),
            )
            empty_signature = copy.deepcopy(signature)
            empty_second = copy.deepcopy(second)
            empty_signature[field] = None
            empty_second[field] = None
            self.assertTrue(
                validate_level_b_factor_binding(empty_signature, empty_second, **validation)
            )
        for independence_field in ("trust_root_id", "failure_domain_id"):
            same_domain = copy.deepcopy(second)
            same_domain[independence_field] = signature[independence_field]
            self.assertTrue(validate_level_b_factor_binding(signature, same_domain, **validation))
        malformed_hash = copy.deepcopy(second)
        malformed_hash["payload_sha256"] = "not-a-sha256"
        malformed_signature = copy.deepcopy(signature)
        malformed_signature["payload_sha256"] = "not-a-sha256"
        self.assertTrue(
            validate_level_b_factor_binding(
                malformed_signature, malformed_hash, **validation
            )
        )
        empty_manifest_signature = copy.deepcopy(signature)
        empty_manifest_second = copy.deepcopy(second)
        empty_manifest_signature["manifest_id"] = ""
        empty_manifest_second["manifest_id"] = ""
        self.assertTrue(
            validate_level_b_factor_binding(
                empty_manifest_signature, empty_manifest_second, **validation
            )
        )
        replay_validation = {**validation, "last_accepted_sequence": 7}
        self.assertTrue(
            validate_level_b_factor_binding(signature, second, **replay_validation)
        )
        non_monotonic_validation = {**validation, "last_accepted_sequence": 8}
        self.assertTrue(
            validate_level_b_factor_binding(signature, second, **non_monotonic_validation)
        )
        malformed_expiry_signature = copy.deepcopy(signature)
        malformed_expiry_second = copy.deepcopy(second)
        malformed_expiry_signature["expires_at"] = "not-a-time"
        malformed_expiry_second["expires_at"] = "not-a-time"
        self.assertTrue(
            validate_level_b_factor_binding(
                malformed_expiry_signature, malformed_expiry_second, **validation
            )
        )
        self.assertEqual(
            "DENY",
            level_b_factor_binding_result(
                signature, second, signature_valid=False, **validation
            ),
        )
        self.assertEqual(
            "DENY",
            level_b_factor_binding_result(signature, second, expired=True, **validation),
        )
        self.assertEqual(
            "DENY",
            level_b_factor_binding_result(signature, second, revoked=True, **validation),
        )

    def test_policy_hashes_match_reviewed_baseline(self) -> None:
        references = {item["path"]: item["sha256"] for item in self.mandate["policy_refs"]}
        for relative in ("governance/approval-policy.toml", "governance/risk-policy.toml"):
            actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, references[relative])

    def test_pm_dec003_rejects_artifact_payload_and_model_mutation(self) -> None:
        artifact_mutation = copy.deepcopy(self.decision_003)
        artifact_mutation["artifact_hashes"][0]["sha256"] = "0" * 64
        artifact_mutation["integrity"]["decision_payload_sha256"] = pm_dec003_payload_digest(
            artifact_mutation
        )
        self.assertTrue(
            any(
                "artifact hash mismatch" in error
                for error in validate_pm_dec003_record(artifact_mutation, ROOT)
            )
        )

        payload_mutation = copy.deepcopy(self.decision_003)
        payload_mutation["safety"]["missing_numeric_profile_result"] = "ALLOW"
        self.assertTrue(
            any(
                "payload hash mismatch" in error
                for error in validate_pm_dec003_record(payload_mutation, ROOT)
            )
        )

        inferred_ttl = copy.deepcopy(self.decision_003)
        inferred_ttl["pending_owner_values"]["pilot_operating_ttl"] = "FIXTURE_VALUE"
        inferred_ttl["integrity"]["decision_payload_sha256"] = pm_dec003_payload_digest(
            inferred_ttl
        )
        self.assertTrue(
            any(
                "must not infer or import" in error
                for error in validate_pm_dec003_record(inferred_ttl, ROOT)
            )
        )
        self.assertTrue(
            all(value == "UNRESOLVED" for value in self.decision_003["pending_owner_values"].values())
        )

    def test_pm_dec003_temporal_and_state_boundaries_fail_closed(self) -> None:
        approval = {
            "approval_tier": "LEVEL_A",
            "validity_mode": "LONG_LIVED_NON_CAPITAL",
            "state": "ACTIVE",
            "issued_at": "2030-01-01T00:00:00Z",
            "effective_from": "2030-01-01T01:00:00Z",
            "review_due_at": "2030-01-01T03:00:00Z",
            "expires_at": "2030-01-01T04:00:00Z",
        }
        at = lambda hour, minute=0: datetime(2030, 1, 1, hour, minute, tzinfo=timezone.utc)
        self.assertEqual(
            "DENY_NOT_YET_EFFECTIVE",
            evaluate_pm_dec003_temporal_validity(approval, evaluation_time=at(0, 59)),
        )
        self.assertEqual(
            "NON_CAPITAL_ACTIVE",
            evaluate_pm_dec003_temporal_validity(approval, evaluation_time=at(1)),
        )
        self.assertEqual(
            "NON_CAPITAL_REVIEW_REQUIRED",
            evaluate_pm_dec003_temporal_validity(approval, evaluation_time=at(3)),
        )
        self.assertEqual(
            "DENY_EXPIRED",
            evaluate_pm_dec003_temporal_validity(approval, evaluation_time=at(4)),
        )
        self.assertEqual(
            "DENY_UNTRUSTED_CLOCK",
            evaluate_pm_dec003_temporal_validity(
                approval, evaluation_time=at(2), trusted_clock=False
            ),
        )
        self.assertEqual(
            "DENY_UNTRUSTED_CLOCK",
            evaluate_pm_dec003_temporal_validity(
                approval, evaluation_time=at(2), trusted_clock=1  # type: ignore[arg-type]
            ),
        )
        self.assertEqual(
            "DENY_UNTRUSTED_CLOCK",
            evaluate_pm_dec003_temporal_validity(
                approval, evaluation_time=None,  # type: ignore[arg-type]
            ),
        )
        self.assertEqual(
            "DENY_UNTRUSTED_CLOCK",
            evaluate_pm_dec003_temporal_validity(
                approval,
                evaluation_time=datetime(
                    2030, 1, 1, 2, tzinfo=timezone(timedelta(hours=2))
                ),
            ),
        )

        level_b = {
            **approval,
            "approval_tier": "LEVEL_B",
            "validity_mode": "TIME_BOXED_REAL_CAPITAL",
        }
        self.assertEqual(
            "DENY_NUMERIC_PROFILE_UNRATIFIED",
            evaluate_pm_dec003_temporal_validity(level_b, evaluation_time=at(2)),
        )
        self.assertEqual(
            "NON_AUTHORIZING_LEVEL_B_WINDOW_VALID",
            evaluate_pm_dec003_temporal_validity(
                level_b, evaluation_time=at(2), numeric_profile_ratified=True
            ),
        )
        terminal = {**level_b, "state": "REVOKED"}
        self.assertEqual(
            "DENY_TERMINAL_STATE",
            evaluate_pm_dec003_temporal_validity(terminal, evaluation_time=at(2)),
        )
        malformed = {**approval, "review_due_at": "2030-01-01T05:00:00Z"}
        self.assertEqual(
            "DENY_MALFORMED_TEMPORAL_ORDER",
            evaluate_pm_dec003_temporal_validity(malformed, evaluation_time=at(2)),
        )
        for malformed_timestamp in (
            "2030-01-01 00:00:00Z",
            "2030-01-01T00:00:00+02:00",
            "2030-1-1T00:00:00Z",
        ):
            malformed = {**approval, "issued_at": malformed_timestamp}
            self.assertEqual(
                "DENY_MALFORMED_TEMPORAL_ORDER",
                evaluate_pm_dec003_temporal_validity(malformed, evaluation_time=at(2)),
            )

        state_mutation = copy.deepcopy(self.decision_003)
        state_mutation["approval_lifecycle"]["terminal_reactivation_allowed"] = True
        state_mutation["integrity"]["decision_payload_sha256"] = pm_dec003_payload_digest(
            state_mutation
        )
        self.assertTrue(
            any(
                "approval lifecycle" in error
                for error in validate_pm_dec003_record(state_mutation, ROOT)
            )
        )

    def test_mandate_schema_subset_rejects_unknown_and_nested_fields(self) -> None:
        schema = json.loads(
            (ROOT / "specs/portfolio-mandate-v1/mandate.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual([], validate_schema_subset(self.mandate, schema))
        top_level_unknown = copy.deepcopy(self.mandate)
        top_level_unknown["unexpected_authority"] = False
        self.assertTrue(validate_schema_subset(top_level_unknown, schema))
        nested_unknown = copy.deepcopy(self.mandate)
        nested_unknown["scopes"][0]["unexpected_authority"] = False
        self.assertTrue(validate_schema_subset(nested_unknown, schema))
        for malformed_timestamp in (
            "2026-07-17 00:00:00Z",
            "2026-07-17T02:00:00+02:00",
            "not-a-time",
        ):
            malformed = copy.deepcopy(self.mandate)
            malformed["issued_at"] = malformed_timestamp
            self.assertTrue(validate_schema_subset(malformed, schema))

    def test_pm_dec003_reconciliation_contract_rejects_weakened_exposure_proof(self) -> None:
        mutations = (
            ("signed_net_comparison", "POST_LE_PRE"),
            ("unknown_ambiguous_or_incomparable_exposure_result", "ALLOW"),
            ("pre_and_post_values_required_for_every_applicable_dimension", False),
        )
        for field, unsafe_value in mutations:
            mutated = copy.deepcopy(self.decision_003)
            mutated["reconciliation"][field] = unsafe_value
            mutated["integrity"]["decision_payload_sha256"] = pm_dec003_payload_digest(mutated)
            self.assertTrue(
                any(
                    "reconciliation contract" in error
                    for error in validate_pm_dec003_record(mutated, ROOT)
                )
            )

        missing_dimension = copy.deepcopy(self.decision_003)
        missing_dimension["reconciliation"]["owner_approved_exposure_dimensions"].remove(
            "STRESS_EXPOSURE"
        )
        missing_dimension["integrity"]["decision_payload_sha256"] = pm_dec003_payload_digest(
            missing_dimension
        )
        self.assertTrue(
            any(
                "reconciliation contract" in error
                for error in validate_pm_dec003_record(missing_dimension, ROOT)
            )
        )

    def test_pm_dec003_dimension_specific_exposure_comparisons_are_fail_closed(self) -> None:
        bindings = {
            "metric_id": "btc-net-delta",
            "unit": "BTC",
            "currency": "BTC",
            "valuation_timestamp": "2030-01-01T00:00:00Z",
            "horizon": "INSTANTANEOUS",
            "netting_set": "account-1:BTCUSDT",
            "convention": "SIGNED_BASE_ASSET_DELTA_V1",
        }
        pre_net = {**bindings, "kind": "SIGNED_NET", "value": "-10"}
        self.assertEqual(
            "DENY_EXPOSURE_INCREASE",
            pm_dec003_protective_exposure_result(
                pre_net, {**pre_net, "value": "-30"}
            ),
        )
        self.assertEqual(
            "NON_AUTHORIZING_PROTECTIVE_SHAPE_VALID",
            pm_dec003_protective_exposure_result(
                pre_net, {**pre_net, "value": "-5"}
            ),
        )
        self.assertEqual(
            "DENY_SIGN_CROSSING",
            pm_dec003_protective_exposure_result(
                pre_net, {**pre_net, "value": "5"}
            ),
        )

        stress_pre = {
            **bindings,
            "metric_id": "btc-stress-loss",
            "unit": "RUB_LOSS_MAGNITUDE",
            "currency": "RUB",
            "convention": "NONNEGATIVE_STRESS_LOSS_V1",
            "kind": "STRESS_VECTOR",
            "scenario_set_sha256": "a" * 64,
            "scenario_values": {"gap-down": "100", "vol-spike": "80"},
        }
        stress_increase = copy.deepcopy(stress_pre)
        stress_increase["scenario_values"]["vol-spike"] = "81"
        self.assertEqual(
            "DENY_STRESS_EXPOSURE_INCREASE",
            pm_dec003_protective_exposure_result(stress_pre, stress_increase),
        )
        binding_mismatch = {**pre_net, "currency": "USD", "value": "-5"}
        self.assertEqual(
            "DENY_INCOMPARABLE_EXPOSURE_PROOF",
            pm_dec003_protective_exposure_result(pre_net, binding_mismatch),
        )

    def test_pm_dec003_working_order_sunset_handles_late_fill_uncertainty(self) -> None:
        bounded = {
            "risk_effect": "NEW_OR_INCREASING_RISK",
            "order_type": "CONDITIONAL",
            "time_in_force": "GTD",
            "venue_enforced_expiry": True,
            "expiry_not_after_cancel_deadline": True,
            "deadline_reached": True,
            "revoked": False,
            "cancel_state": "PENDING",
            "venue_state_reconciled": False,
            "remaining_opening_or_conditional_orders": 1,
            "protective_path_verified": False,
        }
        self.assertEqual(
            "DENY_UNBOUNDED_WORKING_ORDER",
            pm_dec003_working_order_sunset_result(
                {**bounded, "time_in_force": "GTC"}
            ),
        )
        for uncertain_state in ("PENDING", "LOST_ACK", "HALT", "RESTART"):
            self.assertEqual(
                "RECONCILIATION_REQUIRED_NO_ZERO_EFFECT_PROMISE",
                pm_dec003_working_order_sunset_result(
                    {**bounded, "cancel_state": uncertain_state}
                ),
            )
        self.assertEqual(
            "RECONCILIATION_REQUIRED_NO_ZERO_EFFECT_PROMISE",
            pm_dec003_working_order_sunset_result(
                {
                    **bounded,
                    "cancel_state": "CONFIRMED_CANCELLED",
                    "venue_state_reconciled": True,
                    "remaining_opening_or_conditional_orders": 0,
                }
            ),
        )
        revoked_unknown = {**bounded, "deadline_reached": False, "revoked": True}
        self.assertEqual(
            "RECONCILIATION_REQUIRED_NO_ZERO_EFFECT_PROMISE",
            pm_dec003_working_order_sunset_result(revoked_unknown),
        )

        weakened = copy.deepcopy(self.decision_003)
        weakened["working_order_sunset"]["zero_external_side_effect_promised_after_cancel_request"] = True
        weakened["integrity"]["decision_payload_sha256"] = pm_dec003_payload_digest(weakened)
        self.assertTrue(
            any(
                "working-order sunset contract" in error
                for error in validate_pm_dec003_record(weakened, ROOT)
            )
        )

    def test_pm_dec003_single_use_contract_rejects_replay_and_blind_retry_mutation(self) -> None:
        for field, unsafe_value in (
            ("blind_retry_allowed", True),
            ("durable_atomic_reservation_required", False),
            ("duplicate_success_result", "CREATE_NEW_SIDE_EFFECT"),
            ("unknown_or_lost_ack_state", "RETRY"),
        ):
            mutated = copy.deepcopy(self.decision_003)
            mutated["single_use"][field] = unsafe_value
            mutated["integrity"]["decision_payload_sha256"] = pm_dec003_payload_digest(mutated)
            self.assertTrue(
                any(
                    "single-use contract" in error
                    for error in validate_pm_dec003_record(mutated, ROOT)
                )
            )

        missing_binding = copy.deepcopy(self.decision_003)
        missing_binding["single_use"]["required_bindings"].remove("idempotency_key_ref")
        missing_binding["integrity"]["decision_payload_sha256"] = pm_dec003_payload_digest(
            missing_binding
        )
        self.assertTrue(
            any(
                "single-use contract" in error
                for error in validate_pm_dec003_record(missing_binding, ROOT)
            )
        )

    def test_pm_dec003_validity_objects_are_independent_and_most_restrictive(self) -> None:
        all_valid = {name: True for name in PM_DEC003_INDEPENDENT_VALIDITY_OBJECTS}
        self.assertEqual(
            "NON_AUTHORIZING_ALL_VALID", pm_dec003_independent_validity_result(all_valid)
        )
        for name in PM_DEC003_INDEPENDENT_VALIDITY_OBJECTS:
            one_invalid = {**all_valid, name: False}
            self.assertEqual(
                "DENY_MOST_RESTRICTIVE_INTERSECTION",
                pm_dec003_independent_validity_result(one_invalid),
            )
        missing = dict(all_valid)
        missing.pop("EVIDENCE")
        self.assertEqual(
            "DENY_MISSING_OR_UNKNOWN_VALIDITY_OBJECT",
            pm_dec003_independent_validity_result(missing),
        )

        renewed_evidence = copy.deepcopy(self.decision_003)
        renewed_evidence["independent_validity"]["one_object_renews_another"] = True
        renewed_evidence["integrity"]["decision_payload_sha256"] = pm_dec003_payload_digest(
            renewed_evidence
        )
        self.assertTrue(
            any(
                "independent-validity" in error
                for error in validate_pm_dec003_record(renewed_evidence, ROOT)
            )
        )

    def test_pm_dec003_v2_exactly_supersedes_unchanged_v1(self) -> None:
        with zipfile.ZipFile(ROOT / "portfolio-mandate-v0.5.zip") as archive:
            archived = archive.read("specs/portfolio-mandate-v1/decisions/PM-DEC-003.toml")
        self.assertEqual(archived, DECISION_003.read_bytes())
        self.assertEqual([], validate_pm_dec003_v2_record(self.decision_003_v2, self.decision_003, ROOT))
        self.assertEqual(hashlib.sha256(archived).hexdigest(), self.decision_003_v2["supersedes_sha256"])
        mutation = copy.deepcopy(self.decision_003_v2)
        mutation["supersedes_sha256"] = "0" * 64
        mutation["integrity"]["decision_payload_sha256"] = pm_dec003_payload_digest(mutation)
        self.assertTrue(validate_pm_dec003_v2_record(mutation, self.decision_003, ROOT))
        safety_mutations = (
            ("calibration_method", "holdout_parameter_tuning_allowed", True),
            ("calibration_method", "censored_unknown_timeout_and_lost_ack_retained", False),
            ("risk_taxonomy", "higher_class_may_be_less_conservative", True),
            ("profile_lifecycle", "terminal_reactivation_allowed", True),
            ("validity_profile_model", "zero_match_result", "ALLOW"),
            ("validity_profile_model", "multiple_match_result", "FIRST_MATCH"),
            ("validity_profile_model", "wildcard_or_default_result", "DEFAULT"),
            ("numeric_feasibility", "operating_ttl_constraint", "OPERATING_TTL_MS >= CANCEL_RECONCILIATION_BUFFER_MS"),
            ("numeric_feasibility", "risk_increasing_order_constraint", "ORDER_EXPIRY_AT <= APPROVAL_EXPIRES_AT"),
            ("owner_authority_binding", "calibration_is_owner_authority", True),
            ("action_numeric_matrix", "missing_extra_or_inapplicable_result", "ALLOW"),
            ("reconciliation_escalation", "deadline_proves_no_fill", True),
            ("reconciliation_escalation", "deadline_releases_exposure_or_reservation", True),
            ("profile_artifact_security", "schema_exact_id_version_hash_required", False),
            ("profile_artifact_security", "signed_persistent_registry_status", "IMPLEMENTED"),
        )
        for section, field, unsafe in safety_mutations:
            mutated = copy.deepcopy(self.decision_003_v2)
            mutated[section][field] = unsafe
            mutated["integrity"]["decision_payload_sha256"] = pm_dec003_payload_digest(mutated)
            self.assertTrue(
                any("closed profile contract" in error or "fail-closed profile method" in error for error in validate_pm_dec003_v2_record(mutated, self.decision_003, ROOT)),
                (section, field),
            )
        transition_mutation = copy.deepcopy(self.decision_003_v2)
        transition_mutation["profile_lifecycle"]["allowed_transitions"].append("EXPIRED->ACTIVE")
        transition_mutation["integrity"]["decision_payload_sha256"] = pm_dec003_payload_digest(transition_mutation)
        self.assertTrue(validate_pm_dec003_v2_record(transition_mutation, self.decision_003, ROOT))
        duplicate_artifact = copy.deepcopy(self.decision_003_v2)
        duplicate_artifact["artifact_hashes"][1] = copy.deepcopy(duplicate_artifact["artifact_hashes"][0])
        duplicate_artifact["integrity"]["decision_payload_sha256"] = pm_dec003_payload_digest(duplicate_artifact)
        self.assertTrue(any("artifact hash set" in error for error in validate_pm_dec003_v2_record(duplicate_artifact, self.decision_003, ROOT)))
        wrong_snapshot = copy.deepcopy(self.decision_003_v2)
        wrong_snapshot["baseline_snapshot_archive"] = "portfolio-mandate-current.zip"
        wrong_snapshot["integrity"]["decision_payload_sha256"] = pm_dec003_payload_digest(wrong_snapshot)
        self.assertTrue(validate_pm_dec003_v2_record(wrong_snapshot, self.decision_003, ROOT))

    def test_validity_profile_schema_is_closed_typed_and_non_authorizing(self) -> None:
        self.assertEqual([], validate_validity_profile_draft(self.profile, self.profile_schema))
        for invalid in (True, 1.5, "1000"):
            mutated = copy.deepcopy(self.profile)
            mutated["calibration_recommendation"]["status"] = "NON_AUTHORIZING_RECOMMENDATION"
            mutated["calibration_recommendation"]["values"]["operating_ttl_ms"] = invalid
            self.assertTrue(validate_validity_profile_draft(mutated, self.profile_schema))
        for duration_field in self.profile_schema["$defs"]["duration_values"]["properties"]:
            mutated = copy.deepcopy(self.profile)
            mutated["calibration_recommendation"]["status"] = "NON_AUTHORIZING_RECOMMENDATION"
            mutated["calibration_recommendation"]["values"][duration_field] = 3_155_760_000_001
            self.assertTrue(validate_schema_subset(mutated, self.profile_schema), duration_field)
        unknown = copy.deepcopy(self.profile)
        unknown["exact_key"]["wildcard"] = "*"
        self.assertTrue(validate_validity_profile_draft(unknown, self.profile_schema))
        attempted_authorization = copy.deepcopy(self.profile)
        attempted_authorization["authorization_result"] = "ALLOW"
        self.assertTrue(validate_validity_profile_draft(attempted_authorization, self.profile_schema))

    def test_schema_const_and_enum_reject_boolean_integer_confusion(self) -> None:
        mutations = (
            ("eligible_for_authorization", 0),
            ("live_trading_enabled", 0),
        )
        for field, value in mutations:
            mutated = copy.deepcopy(self.profile)
            mutated[field] = value
            self.assertTrue(validate_schema_subset(mutated, self.profile_schema), field)
        nested = (
            ("safety", "recommendation_can_authorize", 0),
            ("lookup_policy", "exactly_one_active_match_required", 1),
            ("evidence", "stratified", 1),
            ("owner_authority", "calibration_is_owner_authority", 0),
        )
        for section, field, value in nested:
            mutated = copy.deepcopy(self.profile)
            mutated[section][field] = value
            self.assertTrue(validate_schema_subset(mutated, self.profile_schema), (section, field))
        enum_confusion = copy.deepcopy(self.profile)
        enum_confusion["exact_key"]["venue_capability_profile_version"] = True
        self.assertTrue(validate_schema_subset(enum_confusion, self.profile_schema))

    def test_action_matrix_and_tuple_coherence_are_closed(self) -> None:
        self.assertEqual("NON_AUTHORIZING_COHERENT_PROFILE_TUPLE", validity_profile_tuple_result(self.profile, require_numeric_values=False))
        for field, value in (
            ("venue_environment", "MOEX_BROKER_TEST"),
            ("capital_stage", "PRODUCTION_LIVE"),
            ("approval_tier", "LEVEL_A"),
            ("validity_mode", "ONE_TIME_REAL_CAPITAL"),
            ("action_class", "PRODUCTION_OPERATING_SCOPE"),
            ("risk_class", "B2_EXISTING_PRODUCTION"),
        ):
            mutated = copy.deepcopy(self.profile)
            mutated["exact_key"][field] = value
            self.assertTrue(validity_profile_tuple_result(mutated, require_numeric_values=False).startswith("DENY_"), field)
        operating = copy.deepcopy(self.profile)
        values = {field: 100 for field in ("operating_ttl_ms", "cancel_reconciliation_buffer_ms", "dispatch_guard_ms", "clock_skew_tolerance_ms", "revocation_snapshot_max_age_ms", "review_lead_time_ms", "reconciliation_escalation_deadline_ms")}
        for layer in ("owner_hard_bounds", "calibration_recommendation", "owner_selected_effective_values"):
            operating[layer]["values"] = copy.deepcopy(values)
        self.assertEqual("NON_AUTHORIZING_COHERENT_PROFILE_TUPLE", validity_profile_tuple_result(operating, require_numeric_values=True))
        operating["owner_hard_bounds"]["values"]["single_use_activation_window_ms"] = 1
        self.assertEqual("DENY_MISSING_EXTRA_OR_INAPPLICABLE_NUMERIC_FIELD", validity_profile_tuple_result(operating, require_numeric_values=True))
        single = copy.deepcopy(self.profile)
        single["exact_key"].update({"capital_stage": "PRODUCTION_LIVE", "validity_mode": "ONE_TIME_REAL_CAPITAL", "action_class": "REAL_BOOK_TRANSFER", "risk_class": "B3_CASH_ACTION"})
        single_values = {field: 100 for field in ("single_use_activation_window_ms", "dispatch_guard_ms", "clock_skew_tolerance_ms", "revocation_snapshot_max_age_ms", "reconciliation_escalation_deadline_ms")}
        for layer in ("owner_hard_bounds", "calibration_recommendation", "owner_selected_effective_values"):
            single[layer]["values"] = copy.deepcopy(single_values)
        self.assertEqual("NON_AUTHORIZING_COHERENT_PROFILE_TUPLE", validity_profile_tuple_result(single, require_numeric_values=True))
        single["owner_selected_effective_values"]["values"].pop("reconciliation_escalation_deadline_ms")
        self.assertEqual("DENY_MISSING_EXTRA_OR_INAPPLICABLE_NUMERIC_FIELD", validity_profile_tuple_result(single, require_numeric_values=True))

    def test_owner_authority_binding_detects_missing_mismatch_replay_and_layer_mutation(self) -> None:
        profile = copy.deepcopy(self.profile)
        owner_payload = {"profile_id": profile["profile_id"], "profile_version": profile["profile_version"], "profile_payload_sha256": profile["profile_payload_sha256"], "owner_hard_bounds": profile["owner_hard_bounds"], "owner_selected_effective_values": profile["owner_selected_effective_values"]}
        digest = hashlib.sha256(json.dumps(owner_payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()).hexdigest()
        manifest = {"manifest_ref": "owner/m1", "manifest_sha256": "a" * 64, "manifest_version": 1, "manifest_sequence": 2, "canonical_owner_payload_sha256": digest}
        profile["owner_authority"] = {**profile["owner_authority"], **manifest, "status": "VERIFIED"}
        self.assertEqual("NON_AUTHORIZING_OWNER_BINDING_SHAPE_VALID", validity_profile_owner_authority_result(profile, manifest, last_accepted_sequence=1))
        self.assertEqual("DENY_OWNER_AUTHORITY_REPLAY", validity_profile_owner_authority_result(profile, manifest, last_accepted_sequence=2))
        self.assertEqual("DENY_OWNER_AUTHORITY_MISMATCH", validity_profile_owner_authority_result(profile, {**manifest, "manifest_sha256": "b" * 64}, last_accepted_sequence=1))
        mutated = copy.deepcopy(profile)
        mutated["owner_hard_bounds"]["values"]["operating_ttl_ms"] = 1
        self.assertEqual("DENY_OWNER_CANONICAL_PAYLOAD_MISMATCH", validity_profile_owner_authority_result(mutated, manifest, last_accepted_sequence=1))
        self.assertEqual("DENY_OWNER_AUTHORITY_ABSENT", validity_profile_owner_authority_result(self.profile, {}, last_accepted_sequence=0))

    def test_v06_snapshot_closed_manifest_rejects_duplicates_and_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            release = root / "specs/portfolio-mandate-v1"
            release.mkdir(parents=True)
            (release / "a.txt").write_text("a", encoding="utf-8")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(root / "bad.zip", "w") as archive:
                    archive.writestr("specs/portfolio-mandate-v1/a.txt", "a")
                    archive.writestr("../escape", "x")
                    archive.writestr("specs/portfolio-mandate-v1/a.txt", "a")
            errors = validate_release_snapshot_members(root, "bad.zip", release)
            self.assertTrue(any("duplicate" in error for error in errors))
            self.assertTrue(any("unsafe member path" in error for error in errors))

    def test_profile_lookup_denies_cross_venue_risk_stage_and_duplicates(self) -> None:
        active = copy.deepcopy(self.profile)
        active["profile_status"] = "ACTIVE"
        active["lifecycle"]["state"] = "ACTIVE"
        active["capability_evidence_status"] = "VERIFIED"
        active["exact_key"]["venue_capability_profile_id"] = "bitget-api-capability-v1"
        active["exact_key"]["venue_capability_profile_sha256"] = "1" * 64
        active["profile_sequence"] = 2
        active["supersedes_ref"] = "profiles/bitget-pilot-v1.toml"
        active["supersedes_sha256"] = "2" * 64
        active["supersedes_sequence"] = 1
        operating_values = {
            "operating_ttl_ms": 1000,
            "cancel_reconciliation_buffer_ms": 200,
            "dispatch_guard_ms": 100,
            "clock_skew_tolerance_ms": 10,
            "revocation_snapshot_max_age_ms": 100,
            "review_lead_time_ms": 300,
            "reconciliation_escalation_deadline_ms": 400,
        }
        for layer in ("owner_hard_bounds", "owner_selected_effective_values"):
            active[layer] = {"status": "VERIFIED", "values": copy.deepcopy(operating_values)}
        active["calibration_recommendation"] = {"status": "NON_AUTHORIZING_RECOMMENDATION", "values": copy.deepcopy(operating_values)}
        active["evidence"].update({
            "status": "VERIFIED", "manifest_ref": "evidence/bitget-pilot-v1.toml",
            "manifest_sha256": "3" * 64, "issuer_ref": "MODEL_RISK_FUNCTION",
            "as_of": "2030-01-01T06:00:00Z", "freshness_status": "VERIFIED_CURRENT",
        })
        active["profile_payload_sha256"] = validity_profile_payload_digest(active)
        owner_payload = {
            "profile_id": active["profile_id"], "profile_version": active["profile_version"],
            "profile_payload_sha256": active["profile_payload_sha256"],
            "owner_hard_bounds": active["owner_hard_bounds"],
            "owner_selected_effective_values": active["owner_selected_effective_values"],
        }
        owner_digest = hashlib.sha256(json.dumps(owner_payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()).hexdigest()
        owner_manifest = {"manifest_ref": "owner/manifest-v7.toml", "manifest_sha256": "4" * 64, "manifest_version": 7, "manifest_sequence": 7, "canonical_owner_payload_sha256": owner_digest}
        active["owner_authority"] = {**active["owner_authority"], **owner_manifest, "status": "VERIFIED"}
        key = active["exact_key"]
        runtime_schema = copy.deepcopy(self.profile_schema)
        runtime_schema["properties"]["profile_status"] = {"const": "ACTIVE"}
        runtime_schema["properties"]["capability_evidence_status"] = {"const": "VERIFIED"}
        runtime_schema["properties"]["lifecycle"]["properties"]["state"] = {"const": "ACTIVE"}
        runtime_schema["properties"]["supersedes_ref"] = {"const": active["supersedes_ref"]}
        runtime_schema["properties"]["supersedes_sha256"] = {"const": active["supersedes_sha256"]}
        runtime_schema["properties"]["supersedes_sequence"] = {"const": 1}
        runtime_schema["$defs"]["numeric_layer"]["properties"]["status"]["enum"].append("VERIFIED")
        owner_properties = runtime_schema["properties"]["owner_authority"]["properties"]
        owner_properties["status"] = {"const": "VERIFIED"}
        owner_properties["manifest_ref"] = {"type": "string", "minLength": 1}
        owner_properties["manifest_sha256"] = {"$ref": "#/$defs/sha256"}
        owner_properties["manifest_version"] = {"type": "integer", "minimum": 1}
        owner_properties["manifest_sequence"] = {"type": "integer", "minimum": 1}
        owner_properties["canonical_owner_payload_sha256"] = {"$ref": "#/$defs/sha256"}
        for field in ("status", "manifest_ref", "manifest_sha256", "issuer_ref", "as_of", "freshness_status"):
            runtime_schema["properties"]["evidence"]["properties"][field] = {"const": active["evidence"][field]}
        runtime_schema_bytes = json.dumps(runtime_schema, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
        active["schema_sha256"] = hashlib.sha256(runtime_schema_bytes).hexdigest()
        active["profile_payload_sha256"] = validity_profile_payload_digest(active)
        owner_payload["profile_payload_sha256"] = active["profile_payload_sha256"]
        owner_digest = hashlib.sha256(json.dumps(owner_payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()).hexdigest()
        owner_manifest["canonical_owner_payload_sha256"] = owner_digest
        active["owner_authority"].update(owner_manifest)
        context = {
            "decision_sha256": active["decision_sha256"],
            "risk_policy_hashes": {"bitget-btc-v1:1": "4f34d45ac058bec6d5ce1ecc05dc242572a917bd6e2f6769ff53b7115f4b72e8"},
            "capability_hashes": {"bitget-api-capability-v1:1": "1" * 64},
            "schema_hashes": {f"{active['schema_id']}:{active['schema_version']}": active["schema_sha256"]},
            "profile_hashes": {active["supersedes_ref"]: active["supersedes_sha256"]},
            "evidence_hashes": {active["evidence"]["manifest_ref"]: active["evidence"]["manifest_sha256"]},
            "family_status": {"BITGET": "ENABLED_NONAUTHORIZING_VALIDATION", "MOEX": "FUTURE_BLOCKED"},
            "now_utc": "2030-01-01T12:00:00Z",
            "owner_manifest": owner_manifest,
            "last_owner_sequence": 6,
            "last_profile_sequence": 1,
        }
        lookup = lambda profiles, lookup_key=key, ctx=context, schema_blob=runtime_schema_bytes: validity_profile_lookup_result(profiles, lookup_key, schema_bytes=schema_blob, registry_context=ctx)
        self.assertEqual(ACTIVE_SCHEMA_UNAVAILABLE, lookup([active]))
        self.assertEqual(ACTIVE_SCHEMA_UNAVAILABLE, lookup([active, copy.deepcopy(active)]))
        for field, value in (("risk_class", "B2_EXISTING_PRODUCTION"), ("capital_stage", "PRODUCTION_LIVE")):
            mismatched = copy.deepcopy(key)
            mismatched[field] = value
            self.assertEqual(ACTIVE_SCHEMA_UNAVAILABLE, lookup([active], mismatched))
        moex = copy.deepcopy(key)
        moex.update({"venue_id": "MOEX", "venue_environment": "MOEX_BROKER_TEST", "market_id": "MOEX_UNRESOLVED_BLOCKED"})
        self.assertEqual(ACTIVE_SCHEMA_UNAVAILABLE, lookup([active], moex))
        wildcard = copy.deepcopy(key)
        wildcard["market_id"] = "*"
        self.assertEqual(ACTIVE_SCHEMA_UNAVAILABLE, lookup([active], wildcard))
        unknown = copy.deepcopy(key)
        unknown["venue_id"] = "UNKNOWN"
        self.assertEqual(ACTIVE_SCHEMA_UNAVAILABLE, lookup([active], unknown))
        stale = copy.deepcopy(active)
        stale["review_due_at"] = "2030-01-01T11:00:00Z"
        stale["profile_payload_sha256"] = validity_profile_payload_digest(stale)
        self.assertEqual(ACTIVE_SCHEMA_UNAVAILABLE, lookup([stale]))
        bad_decision = {**context, "decision_sha256": "2" * 64}
        self.assertEqual(ACTIVE_SCHEMA_UNAVAILABLE, lookup([active], ctx=bad_decision))
        bad_policy = copy.deepcopy(context)
        bad_policy["risk_policy_hashes"]["bitget-btc-v1:1"] = "3" * 64
        self.assertEqual(ACTIVE_SCHEMA_UNAVAILABLE, lookup([active], ctx=bad_policy))
        bad_capability = copy.deepcopy(context)
        bad_capability["capability_hashes"]["bitget-api-capability-v1:1"] = "4" * 64
        self.assertEqual(ACTIVE_SCHEMA_UNAVAILABLE, lookup([active], ctx=bad_capability))
        replay_owner = copy.deepcopy(context)
        replay_owner["last_owner_sequence"] = 7
        self.assertEqual(ACTIVE_SCHEMA_UNAVAILABLE, lookup([active], ctx=replay_owner))
        bad_owner = copy.deepcopy(context)
        bad_owner["owner_manifest"]["manifest_sha256"] = "5" * 64
        self.assertEqual(ACTIVE_SCHEMA_UNAVAILABLE, lookup([active], ctx=bad_owner))
        bad_schema = copy.deepcopy(context)
        bad_schema["schema_hashes"][f"{active['schema_id']}:{active['schema_version']}"] = "6" * 64
        self.assertEqual(ACTIVE_SCHEMA_UNAVAILABLE, lookup([active], ctx=bad_schema))
        mutated_schema = runtime_schema_bytes.replace(b'"title":"Strict', b'"title":"Mutated')
        self.assertEqual(ACTIVE_SCHEMA_UNAVAILABLE, lookup([active], schema_blob=mutated_schema))
        bad_supersedes = copy.deepcopy(context)
        bad_supersedes["profile_hashes"][active["supersedes_ref"]] = "7" * 64
        self.assertEqual(ACTIVE_SCHEMA_UNAVAILABLE, lookup([active], ctx=bad_supersedes))
        bad_evidence = copy.deepcopy(context)
        bad_evidence["evidence_hashes"][active["evidence"]["manifest_ref"]] = "8" * 64
        self.assertEqual(ACTIVE_SCHEMA_UNAVAILABLE, lookup([active], ctx=bad_evidence))
        draft_context = {**context, "last_profile_sequence": 0, "profile_hashes": {self.profile["supersedes_ref"]: self.profile["supersedes_sha256"]}, "capability_hashes": {}, "owner_manifest": {}, "last_owner_sequence": 0}
        self.assertEqual(
            "DENY_SCHEMA_ID_VERSION_HASH_MISMATCH",
            validity_profile_lookup_result([self.profile], self.profile["exact_key"], schema_bytes=PROFILE_SCHEMA.read_bytes(), registry_context=draft_context),
        )
        self.assertEqual("FUTURE_BLOCKED", self.decision_003_v2["venue_profile_families"]["moex_status"])

    def test_profile_lookup_denies_forged_active_before_other_evidence(self) -> None:
        active = copy.deepcopy(self.profile)
        active["profile_status"] = "ACTIVE"
        active["lifecycle"]["state"] = "ACTIVE"
        context = {
            "decision_sha256": active["decision_sha256"],
            "risk_policy_hashes": {},
            "capability_hashes": {},
            "schema_hashes": {},
            "profile_hashes": {},
            "evidence_hashes": {},
            "family_status": {
                "BITGET": "ENABLED_NONAUTHORIZING_VALIDATION",
                "MOEX": "FUTURE_BLOCKED",
            },
            "now_utc": "2030-01-01T12:00:00Z",
            "owner_manifest": {},
            "last_owner_sequence": 0,
            "last_profile_sequence": 0,
        }
        self.assertEqual(
            ACTIVE_SCHEMA_UNAVAILABLE,
            validity_profile_lookup_result(
                [active],
                active["exact_key"],
                schema_bytes=PROFILE_SCHEMA.read_bytes(),
                registry_context=context,
            ),
        )
        forged_schema = copy.deepcopy(self.profile_schema)
        forged_schema["$id"] = "https://tradebot.local/schemas/forged-active-v1.json"
        self.assertEqual(
            ACTIVE_SCHEMA_UNAVAILABLE,
            validity_profile_lookup_result(
                [self.profile],
                self.profile["exact_key"],
                schema_bytes=canonical_json_bytes(forged_schema),
                registry_context=context,
            ),
        )
        malformed_active = copy.deepcopy(active)
        malformed_active["exact_key"]["venue_id"] = "MOEX"
        self.assertEqual(
            ACTIVE_SCHEMA_UNAVAILABLE,
            validity_profile_lookup_result(
                [malformed_active],
                malformed_active["exact_key"],
                schema_bytes=PROFILE_SCHEMA.read_bytes(),
                registry_context={},
            ),
        )

    def test_automatic_profile_changes_are_monotone_safer_only(self) -> None:
        previous = {"operating_ttl_ms": 1000, "cancel_reconciliation_buffer_ms": 200, "dispatch_guard_ms": 50, "clock_skew_tolerance_ms": 20, "revocation_snapshot_max_age_ms": 100, "review_lead_time_ms": 100, "reconciliation_escalation_deadline_ms": 500}
        safer = {**previous, "operating_ttl_ms": 900, "cancel_reconciliation_buffer_ms": 250}
        kwargs = {
            "previous_authorized_actions": ["A", "B"],
            "proposed_authorized_actions": ["A"],
            "history": {
                "owner_epoch": 4,
                "complete": True,
                "immutable": True,
                "entries": [],
            },
            "action_class": "OPERATING",
            "overlay_id": "overlay-4-1",
            "owner_epoch": 4,
        }
        self.assertEqual("NON_AUTHORIZING_MONOTONE_SAFER_OVERLAY_SHAPE", validity_profile_monotone_result(previous, safer, **kwargs))
        self.assertEqual("DENY_AUTOMATIC_RELAXATION", validity_profile_monotone_result(previous, {**safer, "operating_ttl_ms": 1100}, **kwargs))
        self.assertEqual("DENY_TYPE_CONFUSION", validity_profile_monotone_result(previous, {**safer, "operating_ttl_ms": True}, **kwargs))
        incomplete = dict(safer)
        incomplete.pop("review_lead_time_ms")
        self.assertEqual("DENY_INCOMPLETE_NUMERIC_VECTOR", validity_profile_monotone_result(previous, incomplete, **kwargs))
        self.assertEqual("DENY_AUTHORIZED_ACTION_EXPANSION", validity_profile_monotone_result(previous, safer, **{**kwargs, "proposed_authorized_actions": ["A", "B", "C"]}))
        stricter_history = {**previous, "operating_ttl_ms": 800}
        rebound = {**safer, "operating_ttl_ms": 850}
        history = {
            "owner_epoch": 4,
            "complete": True,
            "immutable": True,
            "entries": [{
                "overlay_id": "overlay-4-0",
                "owner_epoch": 4,
                "action_class": "OPERATING",
                "values": stricter_history,
                "authorized_actions": ["A"],
            }],
        }
        self.assertEqual("DENY_REBOUND_OR_AUTOMATIC_RELAXATION", validity_profile_monotone_result(previous, rebound, **{**kwargs, "history": history}))
        self.assertEqual("DENY_INCOMPLETE_OR_UNTRUSTED_HISTORY", validity_profile_monotone_result(previous, safer, **{**kwargs, "history": {"owner_epoch": 4, "complete": False, "immutable": True, "entries": []}}))
        self.assertEqual("DENY_INCOMPARABLE_CHANGE", validity_profile_monotone_result(previous, safer, **{**kwargs, "overlay_id": ""}))
        self.assertEqual("DENY_DURATION_TECHNICAL_MAX_EXCEEDED", validity_profile_monotone_result(previous, {**safer, "operating_ttl_ms": 3_155_760_000_001}, **kwargs))

    def test_profile_lifecycle_and_numeric_feasibility_fail_closed(self) -> None:
        self.assertEqual("NON_AUTHORIZING_TRANSITION_SHAPE_VALID", validity_profile_transition_result("DRAFT", "EVIDENCE_READY"))
        for terminal in ("EXPIRED", "REVOKED", "SUPERSEDED", "INVALIDATED"):
            self.assertEqual("DENY_ILLEGAL_PROFILE_TRANSITION", validity_profile_transition_result(terminal, "ACTIVE"))
        self.assertEqual("DENY_MISSING_OWNER_VALUES", validity_profile_feasibility_result({}))
        base = {"operating_ttl_ms": 301, "cancel_reconciliation_buffer_ms": 200, "dispatch_guard_ms": 100, "reconciliation_escalation_deadline_ms": 50, "duration_unit": "ms", "mandatory_cutoffs": {"approval": "2030-01-01T00:00:01Z", "evidence": "2030-01-01T00:00:02Z", "capability": "2030-01-01T00:00:03Z", "risk_policy": "2030-01-01T00:00:04Z", "runtime_protection": "2030-01-01T00:00:05Z"}, "order_id": "order-feasibility-1", "order_expiry_at": "2030-01-01T00:00:00.800000Z", "late_fill_state": "VERIFIED_NO_LATE_FILL", "reconciliation_state": "VERIFIED_TERMINAL", "escalation_deadline_reached": False, "exposure_or_reservation_released": False, "no_new_risk_cleared": False}
        self.assertEqual("NON_AUTHORIZING_FEASIBLE_SHAPE", validity_profile_feasibility_result(base))
        self.assertEqual("DENY_INFEASIBLE_TTL_BUFFER_GUARD", validity_profile_feasibility_result({**base, "operating_ttl_ms": 300}))
        self.assertEqual("DENY_TYPE_CONFUSION", validity_profile_feasibility_result({**base, "operating_ttl_ms": True}))
        self.assertEqual("DENY_INCOMPATIBLE_UNIT", validity_profile_feasibility_result({**base, "duration_unit": "seconds"}))
        self.assertEqual("DENY_ORDER_EXPIRY_AFTER_SUNSET_DEADLINE", validity_profile_feasibility_result({**base, "order_expiry_at": "2030-01-01T00:00:00.801000Z"}))
        self.assertEqual("NON_AUTHORIZING_FEASIBLE_SHAPE", validity_profile_feasibility_result({**base, "order_expiry_at": "2030-01-01T00:00:00.800000Z"}))
        for cutoff_name in (
            "evidence",
            "capability",
            "risk_policy",
            "runtime_protection",
        ):
            nonapproval_earliest = {
                **base,
                "mandatory_cutoffs": {
                    **base["mandatory_cutoffs"],
                    cutoff_name: "2030-01-01T00:00:00.750000Z",
                },
                "order_expiry_at": "2030-01-01T00:00:00.550001Z",
            }
            self.assertEqual(
                "DENY_ORDER_EXPIRY_AFTER_SUNSET_DEADLINE",
                validity_profile_feasibility_result(nonapproval_earliest),
            )
            self.assertEqual(
                "NON_AUTHORIZING_FEASIBLE_SHAPE",
                validity_profile_feasibility_result({
                    **nonapproval_earliest,
                    "order_expiry_at": "2030-01-01T00:00:00.550000Z",
                }),
            )
        self.assertEqual(
            "DENY_MALFORMED_WORKING_ORDER_IDENTITY",
            validity_profile_feasibility_result({**base, "order_id": ""}),
        )
        self.assertEqual("DENY_INVALID_UTC_TIMESTAMP", validity_profile_feasibility_result({**base, "order_expiry_at": "2030-01-01T02:00:00+02:00"}))
        self.assertEqual("RECONCILIATION_REQUIRED_LATE_FILL_UNKNOWN", validity_profile_feasibility_result({**base, "late_fill_state": "UNKNOWN"}))
        self.assertEqual("RECONCILIATION_REQUIRED_LATE_FILL_UNKNOWN", validity_profile_feasibility_result({**base, "reconciliation_state": "REQUIRED"}))
        self.assertEqual("DENY_ESCALATION_DEADLINE_USED_AS_TERMINAL_PROOF", validity_profile_feasibility_result({**base, "escalation_deadline_reached": True, "exposure_or_reservation_released": True}))
        self.assertEqual("DENY_DURATION_TECHNICAL_MAX_EXCEEDED", validity_profile_feasibility_result({**base, "operating_ttl_ms": 3_155_760_000_001}))

    def test_canonical_json_rejects_duplicates_nonfinite_and_noncanonical_bytes(self) -> None:
        canonical = canonical_json_bytes({"b": [True, 2], "a": "x"})
        self.assertEqual(b'{"a":"x","b":[true,2]}', canonical)
        self.assertEqual(
            "NON_AUTHORIZING_CANONICAL_JSON_SHAPE_VALID",
            canonical_json_bytes_result(canonical),
        )
        for raw in (
            b'{"a":1,"a":2}',
            b'{"a":NaN}',
            b'{"a":Infinity}',
            b'{"a":1',
        ):
            self.assertEqual(
                "DENY_DUPLICATE_KEY_OR_MALFORMED_JSON",
                canonical_json_bytes_result(raw),
            )
        self.assertEqual(
            "DENY_NON_CANONICAL_JSON_BYTES",
            canonical_json_bytes_result(b'{ "a": 1 }'),
        )
        self.assertIsNone(canonical_json_bytes({"unsafe": 1.5}))
        cyclic: list[object] = []
        cyclic.append(cyclic)
        self.assertIsNone(canonical_json_bytes(cyclic))

    def test_canonical_json_deep_nesting_fails_closed_without_exception(self) -> None:
        malformed = b"[" * 10_000
        self.assertTrue(canonical_json_bytes_result(malformed).startswith("DENY_"))

    def test_release_snapshot_rejects_symlink_and_special_members(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            release = root / "specs/portfolio-mandate-v1"
            release.mkdir(parents=True)
            (release / "a.txt").write_text("a", encoding="utf-8")
            symlink = zipfile.ZipInfo("specs/portfolio-mandate-v1/a.txt")
            symlink.create_system = 3
            symlink.external_attr = 0o120777 << 16
            with zipfile.ZipFile(root / "bad.zip", "w") as archive:
                archive.writestr(symlink, "target")
            errors = validate_release_snapshot_members(root, "bad.zip", release)
            self.assertTrue(any("symlink or special" in error for error in errors))

    def test_release_snapshot_rejects_unsafe_directory_members(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            release = root / "specs/portfolio-mandate-v1"
            release.mkdir(parents=True)
            (release / "a.txt").write_text("a", encoding="utf-8")
            disguised_symlink = zipfile.ZipInfo("../escape/")
            disguised_symlink.create_system = 3
            disguised_symlink.external_attr = 0o120777 << 16
            with zipfile.ZipFile(root / "bad.zip", "w") as archive:
                archive.writestr("specs/portfolio-mandate-v1/a.txt", "a")
                archive.writestr(disguised_symlink, "target")
            errors = validate_release_snapshot_members(root, "bad.zip", release)
            self.assertTrue(any("unsafe member path" in error for error in errors))
            self.assertTrue(any("symlink or special" in error for error in errors))

    def test_release_snapshot_rejects_escaping_source_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            release = root / "specs/portfolio-mandate-v1"
            release.mkdir(parents=True)
            outside = root / "outside.txt"
            outside.write_text("outside", encoding="utf-8")
            (release / "escape.txt").symlink_to(outside)
            with zipfile.ZipFile(root / "bad.zip", "w") as archive:
                archive.writestr(
                    "specs/portfolio-mandate-v1/escape.txt", "outside"
                )
            errors = validate_release_snapshot_members(root, "bad.zip", release)
            self.assertTrue(any("source contains symlink" in error for error in errors))
            fifo = release / "runtime.pipe"
            os.mkfifo(fifo)
            errors = validate_release_snapshot_members(root, "bad.zip", release)
            self.assertTrue(
                any("source contains non-regular" in error for error in errors)
            )
            linked_specs = root / "linked-specs"
            linked_specs.symlink_to(root / "specs", target_is_directory=True)
            linked_release = linked_specs / "portfolio-mandate-v1"
            errors = validate_release_snapshot_members(
                root, "bad.zip", linked_release
            )
            self.assertTrue(
                any("source has symlink ancestor" in error for error in errors)
            )

    def test_development_tuple_and_limit_only_are_closed(self) -> None:
        development = copy.deepcopy(self.profile)
        development["exact_key"].update({
            "venue_environment": "PAPER_SIMULATOR",
            "capital_stage": "DEVELOPMENT",
            "approval_tier": "LEVEL_A",
            "validity_mode": "LONG_LIVED_NON_CAPITAL",
            "action_class": "NON_CAPITAL",
            "risk_class": "A0_NON_CAPITAL",
        })
        self.assertEqual(
            "NON_AUTHORIZING_COHERENT_PROFILE_TUPLE",
            validity_profile_tuple_result(development, require_numeric_values=False),
        )
        market = copy.deepcopy(self.profile)
        market["exact_key"].update({"order_type": "MARKET", "time_in_force": "IOC"})
        self.assertEqual(
            "DENY_MARKET_ORDER_WHILE_LIMIT_ONLY",
            validity_profile_tuple_result(market, require_numeric_values=False),
        )
        substituted_policy_market = copy.deepcopy(market)
        substituted_policy_market["exact_key"].update({
            "risk_policy_id": "substitute-policy",
            "risk_policy_version": 99,
            "risk_policy_sha256": "9" * 64,
        })
        self.assertTrue(
            validity_profile_tuple_result(
                substituted_policy_market, require_numeric_values=False
            ).startswith("DENY_")
        )
        mixed = copy.deepcopy(self.profile)
        mixed["exact_key"]["venue_id"] = "MOEX"
        self.assertEqual(
            "DENY_INCOHERENT_VENUE_ENVIRONMENT_MARKET",
            validity_profile_tuple_result(mixed, require_numeric_values=False),
        )
        blocked_moex = copy.deepcopy(self.profile)
        blocked_moex["exact_key"].update({
            "venue_id": "MOEX",
            "venue_environment": "MOEX_BROKER_TEST",
            "market_id": "MOEX_UNRESOLVED_BLOCKED",
        })
        self.assertEqual(
            "DENY_MOEX_FUTURE_BLOCKED",
            validity_profile_tuple_result(
                blocked_moex, require_numeric_values=False
            ),
        )
        unknown = copy.deepcopy(self.profile)
        unknown["exact_key"]["venue_id"] = "KRAKEN"
        self.assertTrue(
            validity_profile_tuple_result(
                unknown, require_numeric_values=False
            ).startswith("DENY_")
        )
        for field, value in (
            ("venue_environment", "KRAKEN_PRODUCTION"),
            ("market_id", "BITGET_SPOT"),
            ("api_or_protocol_version", "KRAKEN_API_V1"),
            ("account_mode", "CASH"),
            ("session_id", "KRAKEN_24X7"),
        ):
            incoherent = copy.deepcopy(self.profile)
            incoherent["exact_key"][field] = value
            self.assertTrue(
                validity_profile_tuple_result(
                    incoherent, require_numeric_values=False
                ).startswith("DENY_")
            )
        for order_type, time_in_force in (
            ("STOP", "GTC"),
            ("LIMIT", "DAY"),
        ):
            unsupported = copy.deepcopy(self.profile)
            unsupported["exact_key"].update({
                "order_type": order_type,
                "time_in_force": time_in_force,
            })
            self.assertEqual(
                "DENY_UNSUPPORTED_ORDER_TYPE_OR_TIF",
                validity_profile_tuple_result(
                    unsupported, require_numeric_values=False
                ),
            )

    def test_timestamp_duration_revocation_and_escalation_bindings_are_causal(self) -> None:
        values = {
            "operating_ttl_ms": 1000,
            "cancel_reconciliation_buffer_ms": 200,
            "dispatch_guard_ms": 100,
            "clock_skew_tolerance_ms": 10,
            "revocation_snapshot_max_age_ms": 400,
            "review_lead_time_ms": 300,
            "reconciliation_escalation_deadline_ms": 400,
        }
        timestamps = {
            "effective_from": "2030-01-01T00:00:00Z",
            "review_due_at": "2030-01-01T00:00:00.700000Z",
            "expires_at": "2030-01-01T00:00:01Z",
            "commit_at": "2030-01-01T00:00:00.600000Z",
            "evaluated_at": "2030-01-01T00:00:00.500000Z",
            "revocation_snapshot_at": "2030-01-01T00:00:00.450000Z",
            "first_durable_unknown_at": "2030-01-01T00:00:00.100000Z",
            "escalation_due_at": "2030-01-01T00:00:00.500000Z",
            "escalation_dispatched_at": "2030-01-01T00:00:00.400000Z",
            "escalation_ack_at": "2030-01-01T00:00:00.450000Z",
        }
        self.assertEqual(
            "NON_AUTHORIZING_TIMESTAMP_BINDING_SHAPE_VALID",
            validity_profile_timestamp_binding_result(
                "PILOT_OPERATING_SCOPE", values, timestamps
            ),
        )
        before = {**timestamps, "commit_at": "2029-12-31T23:59:59.999999Z"}
        self.assertEqual(
            "DENY_COMMIT_BEFORE_EFFECTIVE_FROM",
            validity_profile_timestamp_binding_result(
                "PILOT_OPERATING_SCOPE", values, before
            ),
        )
        bad_ack = {
            **timestamps,
            "escalation_ack_at": "2030-01-01T00:00:00.399999Z",
        }
        self.assertEqual(
            "DENY_CAUSALLY_INVALID_ESCALATION_ORDER",
            validity_profile_timestamp_binding_result(
                "PILOT_OPERATING_SCOPE", values, bad_ack
            ),
        )
        self.assertEqual(
            "DENY_MISSING_EXTRA_OR_INAPPLICABLE_TEMPORAL_FIELD",
            validity_profile_timestamp_binding_result(
                "PILOT_OPERATING_SCOPE",
                {**values, "dispatch_guard_ms": 0},
                timestamps,
            ),
        )
        for cutoff_commit in (
            "2030-01-01T00:00:00.700000Z",
            "2030-01-01T00:00:00.710000Z",
        ):
            cutoff = {
                **timestamps,
                "commit_at": cutoff_commit,
            }
            self.assertEqual(
                "DENY_REVIEW_CUTOFF_REACHED_OR_INVALID",
                validity_profile_timestamp_binding_result(
                    "PILOT_OPERATING_SCOPE", values, cutoff
                ),
            )
        for cutoff_evaluation in (
            "2030-01-01T00:00:00.700000Z",
            "2030-01-01T00:00:00.710000Z",
        ):
            cutoff = {
                **timestamps,
                "evaluated_at": cutoff_evaluation,
                "commit_at": cutoff_evaluation,
                "revocation_snapshot_at": cutoff_evaluation,
            }
            self.assertEqual(
                "DENY_REVIEW_CUTOFF_REACHED_OR_INVALID",
                validity_profile_timestamp_binding_result(
                    "PILOT_OPERATING_SCOPE", values, cutoff
                ),
            )
        review_at_effective_values = {
            **values,
            "review_lead_time_ms": 1000,
        }
        review_at_effective = {
            **timestamps,
            "review_due_at": timestamps["effective_from"],
            "commit_at": timestamps["effective_from"],
            "evaluated_at": timestamps["effective_from"],
            "revocation_snapshot_at": timestamps["effective_from"],
            "first_durable_unknown_at": None,
            "escalation_due_at": None,
            "escalation_dispatched_at": None,
            "escalation_ack_at": None,
        }
        self.assertEqual(
            "DENY_REVIEW_CUTOFF_REACHED_OR_INVALID",
            validity_profile_timestamp_binding_result(
                "PILOT_OPERATING_SCOPE",
                review_at_effective_values,
                review_at_effective,
            ),
        )
        evaluated_after_expiry = {
            **timestamps,
            "evaluated_at": "2030-01-01T00:00:02Z",
            "revocation_snapshot_at": "2030-01-01T00:00:01.950000Z",
        }
        self.assertTrue(
            validity_profile_timestamp_binding_result(
                "PILOT_OPERATING_SCOPE", values, evaluated_after_expiry
            ).startswith("DENY_")
        )
        evaluated_after_commit = {
            **timestamps,
            "evaluated_at": "2030-01-01T00:00:00.850000Z",
            "revocation_snapshot_at": "2030-01-01T00:00:00.600000Z",
        }
        self.assertTrue(
            validity_profile_timestamp_binding_result(
                "PILOT_OPERATING_SCOPE", values, evaluated_after_commit
            ).startswith("DENY_")
        )
        snapshot_after_evaluation = {
            **timestamps,
            "revocation_snapshot_at": "2030-01-01T00:00:00.550000Z",
        }
        self.assertTrue(
            validity_profile_timestamp_binding_result(
                "PILOT_OPERATING_SCOPE", values, snapshot_after_evaluation
            ).startswith("DENY_")
        )
        stale_at_commit = {
            **values,
            "revocation_snapshot_max_age_ms": 100,
        }
        self.assertEqual(
            "DENY_STALE_OR_CAUSALLY_INVALID_REVOCATION_SNAPSHOT",
            validity_profile_timestamp_binding_result(
                "PILOT_OPERATING_SCOPE", stale_at_commit, timestamps
            ),
        )
        future_unknown = {
            **timestamps,
            "first_durable_unknown_at": "2030-01-01T00:00:00.600000Z",
            "escalation_due_at": "2030-01-01T00:00:01Z",
            "escalation_dispatched_at": None,
            "escalation_ack_at": None,
        }
        self.assertTrue(
            validity_profile_timestamp_binding_result(
                "PILOT_OPERATING_SCOPE", values, future_unknown
            ).startswith("DENY_")
        )

    def test_exact_byte_scope_and_complete_evidence_remain_non_authorizing(self) -> None:
        request = {
            field: self.profile["exact_key"][field]
            for field in RUNTIME_SEMANTIC_SCOPE_FIELDS
        }
        request.update({
            "liquidity_regime": "NORMAL",
            "volatility_regime": "NORMAL",
            "degraded_state": "NORMAL",
        })
        base_artifact = {
            "artifact_kind": "VENUE_CAPABILITY",
            "artifact_id": "bitget-capability-v2",
            "artifact_version": 2,
            "lifecycle": "ACTIVE_VERIFIED_CURRENT",
            "effective_from": "2030-01-01T00:00:00Z",
            "review_due_at": "2030-01-02T00:00:00Z",
            "expires_at": "2030-01-03T00:00:00Z",
            "semantic_scope": request,
            "limit_only": True,
            "provenance": ["official-docs:bitget-api-v2"],
        }
        capability_bytes = canonical_json_bytes(base_artifact)
        capability_sha = hashlib.sha256(capability_bytes).hexdigest()
        self.assertEqual(
            "NON_AUTHORIZING_EXACT_BYTE_SEMANTIC_SCOPE_SHAPE_VALID",
            validity_artifact_scope_result(
                request,
                capability_bytes,
                expected_kind="VENUE_CAPABILITY",
                expected_sha256=capability_sha,
                now_utc="2030-01-01T12:00:00Z",
            ),
        )
        mutated_request = {**request, "account_mode": "HEDGE_MODE"}
        self.assertEqual(
            "DENY_ARTIFACT_LIFECYCLE_OR_SEMANTIC_SCOPE_MISMATCH",
            validity_artifact_scope_result(
                mutated_request,
                capability_bytes,
                expected_kind="VENUE_CAPABILITY",
                expected_sha256=capability_sha,
                now_utc="2030-01-01T12:00:00Z",
            ),
        )
        substitute_request = {
            **request,
            "risk_policy_id": "substitute-policy",
            "risk_policy_version": 99,
            "risk_policy_sha256": "9" * 64,
            "order_type": "MARKET",
            "time_in_force": "IOC",
        }
        substitute_policy = {
            **base_artifact,
            "artifact_kind": "RISK_POLICY",
            "artifact_id": "substitute-policy",
            "artifact_version": 99,
            "semantic_scope": substitute_request,
            "limit_only": False,
        }
        substitute_policy_bytes = canonical_json_bytes(substitute_policy)
        self.assertTrue(
            validity_artifact_scope_result(
                substitute_request,
                substitute_policy_bytes,
                expected_kind="RISK_POLICY",
                expected_sha256=hashlib.sha256(substitute_policy_bytes).hexdigest(),
                now_utc="2030-01-01T12:00:00Z",
            ).startswith("DENY_")
        )
        actual_policy_bytes = (
            ROOT / "governance/risk-policy.toml"
        ).read_bytes()
        actual_policy_sha = hashlib.sha256(actual_policy_bytes).hexdigest()
        self.assertEqual(
            "NON_AUTHORIZING_EXACT_GOVERNANCE_POLICY_SCOPE_SHAPE_VALID",
            validity_artifact_scope_result(
                request,
                actual_policy_bytes,
                expected_kind="RISK_POLICY",
                expected_sha256=actual_policy_sha,
                now_utc="2030-01-01T12:00:00Z",
            ),
        )
        for arbitrary_policy_bytes in (
            b'policy_id = "bitget-btc-v1"\nversion = 1\n',
            actual_policy_bytes + b"\n",
        ):
            self.assertEqual(
                "DENY_GOVERNANCE_RISK_POLICY_EXACT_BYTES_MISMATCH",
                validity_artifact_scope_result(
                    request,
                    arbitrary_policy_bytes,
                    expected_kind="RISK_POLICY",
                    expected_sha256=hashlib.sha256(
                        arbitrary_policy_bytes
                    ).hexdigest(),
                    now_utc="2030-01-01T12:00:00Z",
                ),
            )
        windows = {
            name: {
                "dataset_sha256": character * 64,
                "sealed_at": "2029-12-31T00:00:00Z",
                "observations": 10,
                "sealed": True,
            }
            for name, character in (
                ("ROLLING_RECENT", "1"),
                ("STRESS_ARCHIVE", "2"),
                ("FORWARD_CONFIRMATION", "3"),
            )
        }
        owner_bound_thresholds = {
            "binding_id": "owner-bound-evidence-thresholds-fixture-v1",
            "binding_version": 1,
            "status": "OWNER_APPROVED_BOUND_REFERENCE",
            "semantic_scope": request,
            "minimum_raw_sample_size": 10,
            "minimum_cluster_sample_size": 8,
            "minimum_effective_sample_size": 6,
            "minimum_window_observations": {
                "ROLLING_RECENT": 2,
                "STRESS_ARCHIVE": 2,
                "FORWARD_CONFIRMATION": 2,
            },
            "required_provenance_refs": [
                "telemetry:sealed:bitget:v1"
            ],
        }
        threshold_bytes = canonical_json_bytes(owner_bound_thresholds)
        threshold_sha = hashlib.sha256(threshold_bytes).hexdigest()
        evidence = {
            "manifest_id": "evidence-bitget-stratum-v1",
            "manifest_version": 1,
            "status": "VERIFIED_CURRENT",
            "issuer_ref": "MODEL_RISK_FUNCTION",
            "as_of": "2030-01-01T00:00:00Z",
            "expires_at": "2030-01-02T00:00:00Z",
            "semantic_scope": request,
            "censored_outcomes_retained": True,
            "unknown_outcomes_retained": True,
            "competing_risks": ["CANCELLED", "FILLED", "LATE_FILL"],
            "tail_quantile_ppm": 999000,
            "one_sided_confidence_level_ppm": 950000,
            "estimator_id": "AALEN_JOHANSEN_TAIL_V1",
            "clustering_rule_id": "ORDER_CHAIN_V1",
            "raw_sample_size": 100,
            "cluster_sample_size": 80,
            "effective_sample_size": 60,
            "sealed_windows": windows,
            "holdout_access_history": [{
                "accessed_at": "2029-12-31T12:00:00Z",
                "actor_ref": "MODEL_RISK_FUNCTION",
                "purpose": "FINAL_FORWARD_CONFIRMATION",
            }],
            "holdout_tuning_allowed": False,
            "provenance_refs": ["telemetry:sealed:bitget:v1"],
            "drift_status": "PASS",
            "owner_bound_thresholds_id": owner_bound_thresholds["binding_id"],
            "owner_bound_thresholds_version": owner_bound_thresholds[
                "binding_version"
            ],
            "owner_bound_thresholds_sha256": threshold_sha,
        }
        evidence_bytes = canonical_json_bytes(evidence)
        evidence_sha = hashlib.sha256(evidence_bytes).hexdigest()
        self.assertEqual(
            "NON_AUTHORIZING_DECLARED_EVIDENCE_SHAPE_CAUSALITY_VALID",
            validity_evidence_manifest_result(
                request,
                evidence_bytes,
                expected_sha256=evidence_sha,
                now_utc="2030-01-01T12:00:00Z",
                owner_bound_thresholds_bytes=threshold_bytes,
                owner_bound_thresholds_sha256=threshold_sha,
            ),
        )
        declared_unverified_estimator = copy.deepcopy(evidence)
        declared_unverified_estimator[
            "estimator_id"
        ] = "DECLARED_UNVERIFIED_ESTIMATOR_V9"
        declared_unverified_bytes = canonical_json_bytes(
            declared_unverified_estimator
        )
        self.assertEqual(
            "NON_AUTHORIZING_DECLARED_EVIDENCE_SHAPE_CAUSALITY_VALID",
            validity_evidence_manifest_result(
                request,
                declared_unverified_bytes,
                expected_sha256=hashlib.sha256(
                    declared_unverified_bytes
                ).hexdigest(),
                now_utc="2030-01-01T12:00:00Z",
                owner_bound_thresholds_bytes=threshold_bytes,
                owner_bound_thresholds_sha256=threshold_sha,
            ),
        )
        for field in (
            "liquidity_regime",
            "volatility_regime",
            "degraded_state",
        ):
            unknown_scope = {**request, field: "AD_HOC_UNKNOWN"}
            self.assertEqual(
                "DENY_EVIDENCE_SCOPE_TAXONOMY_UNKNOWN",
                validity_evidence_manifest_result(
                    unknown_scope,
                    evidence_bytes,
                    expected_sha256=evidence_sha,
                    now_utc="2030-01-01T12:00:00Z",
                    owner_bound_thresholds_bytes=threshold_bytes,
                    owner_bound_thresholds_sha256=threshold_sha,
                ),
            )
        unresolved_scope = {
            **request,
            "liquidity_regime": "UNRESOLVED_DENY",
        }
        self.assertEqual(
            "DENY_EVIDENCE_SCOPE_UNRESOLVED",
            validity_evidence_manifest_result(
                unresolved_scope,
                evidence_bytes,
                expected_sha256=evidence_sha,
                now_utc="2030-01-01T12:00:00Z",
                owner_bound_thresholds_bytes=threshold_bytes,
                owner_bound_thresholds_sha256=threshold_sha,
            ),
        )
        invalid_purpose = copy.deepcopy(evidence)
        invalid_purpose["holdout_access_history"][0][
            "purpose"
        ] = "POST_HOC_TUNING"
        invalid_purpose_bytes = canonical_json_bytes(invalid_purpose)
        self.assertEqual(
            "DENY_HOLDOUT_HISTORY_OR_PROVENANCE_MISSING",
            validity_evidence_manifest_result(
                request,
                invalid_purpose_bytes,
                expected_sha256=hashlib.sha256(
                    invalid_purpose_bytes
                ).hexdigest(),
                now_utc="2030-01-01T12:00:00Z",
                owner_bound_thresholds_bytes=threshold_bytes,
                owner_bound_thresholds_sha256=threshold_sha,
            ),
        )
        wrong_provenance = copy.deepcopy(evidence)
        wrong_provenance["provenance_refs"] = [
            "telemetry:unbound:bitget:v1"
        ]
        wrong_provenance_bytes = canonical_json_bytes(wrong_provenance)
        self.assertEqual(
            "DENY_HOLDOUT_HISTORY_OR_PROVENANCE_MISSING",
            validity_evidence_manifest_result(
                request,
                wrong_provenance_bytes,
                expected_sha256=hashlib.sha256(
                    wrong_provenance_bytes
                ).hexdigest(),
                now_utc="2030-01-01T12:00:00Z",
                owner_bound_thresholds_bytes=threshold_bytes,
                owner_bound_thresholds_sha256=threshold_sha,
            ),
        )
        size_one_without_bound = copy.deepcopy(evidence)
        size_one_without_bound.update({
            "raw_sample_size": 1,
            "cluster_sample_size": 1,
            "effective_sample_size": 1,
        })
        for window in size_one_without_bound["sealed_windows"].values():
            window["observations"] = 1
        size_one_bytes = canonical_json_bytes(size_one_without_bound)
        self.assertTrue(
            validity_evidence_manifest_result(
                request,
                size_one_bytes,
                expected_sha256=hashlib.sha256(size_one_bytes).hexdigest(),
                now_utc="2030-01-01T12:00:00Z",
            ).startswith("DENY_")
        )
        self.assertEqual(
            "DENY_EVIDENCE_BELOW_OWNER_BOUND_MINIMUM",
            validity_evidence_manifest_result(
                request,
                size_one_bytes,
                expected_sha256=hashlib.sha256(size_one_bytes).hexdigest(),
                now_utc="2030-01-01T12:00:00Z",
                owner_bound_thresholds_bytes=threshold_bytes,
                owner_bound_thresholds_sha256=threshold_sha,
            ),
        )
        future_sealed = copy.deepcopy(evidence)
        future_sealed["sealed_windows"]["FORWARD_CONFIRMATION"][
            "sealed_at"
        ] = "2030-01-03T00:00:00Z"
        future_sealed_bytes = canonical_json_bytes(future_sealed)
        self.assertTrue(
            validity_evidence_manifest_result(
                request,
                future_sealed_bytes,
                expected_sha256=hashlib.sha256(future_sealed_bytes).hexdigest(),
                now_utc="2030-01-01T12:00:00Z",
                owner_bound_thresholds_bytes=threshold_bytes,
                owner_bound_thresholds_sha256=threshold_sha,
            ).startswith("DENY_")
        )
        future_access = copy.deepcopy(evidence)
        future_access["holdout_access_history"][0][
            "accessed_at"
        ] = "2030-01-01T06:00:00Z"
        future_access_bytes = canonical_json_bytes(future_access)
        self.assertTrue(
            validity_evidence_manifest_result(
                request,
                future_access_bytes,
                expected_sha256=hashlib.sha256(future_access_bytes).hexdigest(),
                now_utc="2030-01-01T12:00:00Z",
                owner_bound_thresholds_bytes=threshold_bytes,
                owner_bound_thresholds_sha256=threshold_sha,
            ).startswith("DENY_")
        )
        incomplete = copy.deepcopy(evidence)
        incomplete["sealed_windows"].pop("FORWARD_CONFIRMATION")
        incomplete_bytes = canonical_json_bytes(incomplete)
        self.assertEqual(
            "DENY_UNSEALED_OR_MISSING_EVIDENCE_WINDOW",
            validity_evidence_manifest_result(
                request,
                incomplete_bytes,
                expected_sha256=hashlib.sha256(incomplete_bytes).hexdigest(),
                now_utc="2030-01-01T12:00:00Z",
                owner_bound_thresholds_bytes=threshold_bytes,
                owner_bound_thresholds_sha256=threshold_sha,
            ),
        )
        policy_bytes = actual_policy_bytes
        active_schema = canonical_json_bytes({
            "$id": "https://tradebot.local/schemas/future-active-v1.json"
        })
        self.assertEqual(
            ACTIVE_SCHEMA_UNAVAILABLE,
            validity_active_runtime_contract_result(
                request,
                schema_bytes=active_schema,
                capability_bytes=capability_bytes,
                capability_sha256=capability_sha,
                policy_bytes=policy_bytes,
                policy_sha256=actual_policy_sha,
                evidence_bytes=evidence_bytes,
                evidence_sha256=evidence_sha,
                owner_bound_thresholds_bytes=threshold_bytes,
                owner_bound_thresholds_sha256=threshold_sha,
                now_utc="2030-01-01T12:00:00Z",
            ),
        )

    def test_b4_authority_change_is_single_use_and_invalidates_old_manifest(self) -> None:
        prior_manifest = {
            "manifest_ref": "operating/bitget-pilot-v1.json",
            "manifest_version": 1,
            "manifest_sequence": 1,
            "change_action_id": "authority-change-previous-8",
            "change_payload_sha256": "a" * 64,
            "profile_sha256": "1" * 64,
            "configuration_sha256": "5" * 64,
            "effective_from": "2029-12-01T00:00:00Z",
            "expires_at": "2030-01-01T00:00:00.900000Z",
            "status": "SEPARATELY_APPROVED_NON_AUTHORIZING_SHAPE",
        }
        prior_manifest_bytes = canonical_json_bytes(prior_manifest)
        prior_manifest_sha = hashlib.sha256(prior_manifest_bytes).hexdigest()
        prior_manifest_record = {
            "manifest_ref": prior_manifest["manifest_ref"],
            "manifest_version": prior_manifest["manifest_version"],
            "manifest_sequence": prior_manifest["manifest_sequence"],
            "manifest_sha256": prior_manifest_sha,
            "manifest_bytes": prior_manifest_bytes,
        }

        def authority_result(
            candidate: object,
            candidate_registry: object,
        ) -> str:
            return validity_profile_authority_change_result(
                candidate,
                candidate_registry,
                prior_operating_manifest_bytes=prior_manifest_bytes,
                prior_operating_manifest_record=prior_manifest_record,
            )

        change = {
            "action_id": "authority-change-9",
            "action_class": "VALIDITY_PROFILE_AUTHORITY_CHANGE",
            "risk_class": "B4_AUTHORITY_MUTATION",
            "approval_tier": "LEVEL_B",
            "owner_epoch": 9,
            "profile_id": "bitget-pilot-v2",
            "previous_profile_sha256": "1" * 64,
            "new_profile_sha256": "2" * 64,
            "previous_configuration_sha256": prior_manifest[
                "configuration_sha256"
            ],
            "new_configuration_sha256": "3" * 64,
            "previous_operating_manifest_sha256": prior_manifest_sha,
            "effective_from": "2030-01-01T00:00:00Z",
            "expires_at": "2030-01-01T00:00:01Z",
            "commit_at": "2030-01-01T00:00:00.500000Z",
            "owner_selected_activation_window_ms": 1000,
            "level_b_signature_id": "signature-owner-9",
            "second_factor_id": "factor-independent-9",
            "level_b_signature_verified": True,
            "second_factor_verified": True,
            "canonical_action_payload_sha256": "",
            "consumption_state": "PROPOSED",
            "durable_consumed_at": None,
            "invalidated_profile_sha256": "1" * 64,
            "invalidated_operating_manifest_sha256": prior_manifest_sha,
            "new_operating_manifest_ref": "PENDING_SEPARATE_OPERATING_MANIFEST",
        }
        payload = {field: change[field] for field in B4_CANONICAL_PAYLOAD_FIELDS}
        change["canonical_action_payload_sha256"] = hashlib.sha256(
            canonical_json_bytes(payload)
        ).hexdigest()
        registry = {
            "registry_id": "validity-profile-authority-global-v1",
            "registry_scope": "GLOBAL_ACROSS_OWNER_EPOCHS",
            "genesis_owner_epoch": 0,
            "genesis_sha256": (
                "00d45207979fc16245c40b9c850d7cad99b664e4678a2f100350ebae15705c34"
            ),
            "latest_owner_epoch": 0,
            "durable": True,
            "append_only": True,
            "history_complete": True,
            "base_sequence": 0,
            "latest_sequence": 0,
            "records": [],
        }
        self.assertEqual(
            "NON_AUTHORIZING_B4_REGISTRY_SHAPE_VALID",
            validity_profile_b4_registry_shape_result(registry),
        )
        self.assertEqual(
            "DENY_B4_CURRENT_REGISTRY_CHECKPOINT_OR_RUNTIME_TRUST_UNAVAILABLE",
            authority_result(change, registry),
        )
        self.assertEqual(
            "DENY_B4_PREVIOUS_CONFIGURATION_BINDING_INVALID",
            validity_profile_authority_change_result(change, registry),
        )
        mismatched_previous_configuration = {
            **change,
            "previous_configuration_sha256": "6" * 64,
        }
        mismatched_payload = {
            field: mismatched_previous_configuration[field]
            for field in B4_CANONICAL_PAYLOAD_FIELDS
        }
        mismatched_previous_configuration[
            "canonical_action_payload_sha256"
        ] = hashlib.sha256(
            canonical_json_bytes(mismatched_payload)
        ).hexdigest()
        self.assertEqual(
            "DENY_B4_PREVIOUS_CONFIGURATION_BINDING_INVALID",
            authority_result(
                mismatched_previous_configuration,
                registry,
            ),
        )
        unchanged_configuration = {
            **change,
            "new_configuration_sha256": change[
                "previous_configuration_sha256"
            ],
        }
        unchanged_payload = {
            field: unchanged_configuration[field]
            for field in B4_CANONICAL_PAYLOAD_FIELDS
        }
        unchanged_configuration[
            "canonical_action_payload_sha256"
        ] = hashlib.sha256(
            canonical_json_bytes(unchanged_payload)
        ).hexdigest()
        self.assertEqual(
            "DENY_B4_HASH_ROTATION_OR_INVALIDATION_PROOF_MISMATCH",
            authority_result(unchanged_configuration, registry),
        )
        consumed = {
            **change,
            "consumption_state": "CONSUMED",
            "durable_consumed_at": "2030-01-01T00:00:00.600000Z",
        }
        durable_record = {
            "action_id": change["action_id"],
            "owner_epoch": 9,
            "parent_profile_sha256": change["previous_profile_sha256"],
            "parent_operating_manifest_sha256": change[
                "previous_operating_manifest_sha256"
            ],
            "child_profile_sha256": change["new_profile_sha256"],
            "child_configuration_sha256": change["new_configuration_sha256"],
            "canonical_action_payload_sha256": change[
                "canonical_action_payload_sha256"
            ],
            "previous_sequence": 0,
            "sequence": 1,
            "cas_token_sha256": "5" * 64,
            "consumed_at": consumed["durable_consumed_at"],
            "state": "CONSUMED_AND_PARENTS_INVALIDATED",
            "atomic_parent_consumption": True,
            "parent_profile_invalidated": True,
            "parent_operating_manifest_invalidated": True,
        }
        consumed_registry = {
            **registry,
            "latest_owner_epoch": 9,
            "latest_sequence": 1,
            "records": [durable_record],
        }
        self.assertEqual(
            "NON_AUTHORIZING_B4_REGISTRY_SHAPE_VALID",
            validity_profile_b4_registry_shape_result(consumed_registry),
        )
        self.assertEqual(
            "DENY_B4_CURRENT_REGISTRY_CHECKPOINT_OR_RUNTIME_TRUST_UNAVAILABLE",
            authority_result(consumed, consumed_registry),
        )
        consumed_after_expiry = {
            **consumed,
            "durable_consumed_at": "2030-01-01T00:00:02Z",
        }
        self.assertTrue(
            authority_result(
                consumed_after_expiry, consumed_registry
            ).startswith("DENY_")
        )
        self.assertEqual(
            "DENY_B4_SINGLE_USE_REPLAY",
            authority_result(change, consumed_registry),
        )
        hidden_prefix_registry = {
            **registry,
            "base_sequence": 6,
            "latest_sequence": 6,
        }
        self.assertEqual(
            "DENY_B4_DURABLE_REGISTRY_PROOF_INVALID",
            authority_result(
                change, hidden_prefix_registry
            ),
        )
        malformed_registry = {**registry, "latest_sequence": 1, "records": [{}]}
        self.assertEqual(
            "DENY_B4_DURABLE_REGISTRY_PROOF_INVALID",
            authority_result(change, malformed_registry),
        )
        duplicate_parent_record = {
            **durable_record,
            "action_id": "authority-change-duplicate-parent",
            "previous_sequence": 1,
            "sequence": 2,
            "cas_token_sha256": "6" * 64,
        }
        duplicate_parent_registry = {
            **consumed_registry,
            "latest_sequence": 2,
            "records": [durable_record, duplicate_parent_record],
        }
        self.assertEqual(
            "DENY_B4_DURABLE_REGISTRY_PROOF_INVALID",
            authority_result(
                consumed, duplicate_parent_registry
            ),
        )
        branch = {
            **change,
            "action_id": "authority-change-branch-10",
            "new_profile_sha256": "6" * 64,
            "new_configuration_sha256": "7" * 64,
        }
        branch_payload = {
            field: branch[field] for field in B4_CANONICAL_PAYLOAD_FIELDS
        }
        branch["canonical_action_payload_sha256"] = hashlib.sha256(
            canonical_json_bytes(branch_payload)
        ).hexdigest()
        self.assertEqual(
            "DENY_B4_PARENT_ALREADY_CONSUMED",
            authority_result(branch, consumed_registry),
        )
        profile_component_reuse = {
            **branch,
            "previous_operating_manifest_sha256": "9" * 64,
            "invalidated_operating_manifest_sha256": "9" * 64,
        }
        profile_component_payload = {
            field: profile_component_reuse[field]
            for field in B4_CANONICAL_PAYLOAD_FIELDS
        }
        profile_component_reuse["canonical_action_payload_sha256"] = (
            hashlib.sha256(
                canonical_json_bytes(profile_component_payload)
            ).hexdigest()
        )
        self.assertEqual(
            "DENY_B4_PREVIOUS_CONFIGURATION_BINDING_INVALID",
            authority_result(
                profile_component_reuse, consumed_registry
            ),
        )
        manifest_component_reuse = {
            **branch,
            "previous_profile_sha256": "8" * 64,
            "invalidated_profile_sha256": "8" * 64,
        }
        manifest_component_payload = {
            field: manifest_component_reuse[field]
            for field in B4_CANONICAL_PAYLOAD_FIELDS
        }
        manifest_component_reuse["canonical_action_payload_sha256"] = (
            hashlib.sha256(
                canonical_json_bytes(manifest_component_payload)
            ).hexdigest()
        )
        self.assertEqual(
            "DENY_B4_PARENT_ALREADY_CONSUMED",
            authority_result(
                manifest_component_reuse, consumed_registry
            ),
        )
        epoch_ten = {
            **branch,
            "action_id": "authority-change-epoch-10",
            "owner_epoch": 10,
        }
        epoch_ten_payload = {
            field: epoch_ten[field] for field in B4_CANONICAL_PAYLOAD_FIELDS
        }
        epoch_ten["canonical_action_payload_sha256"] = hashlib.sha256(
            canonical_json_bytes(epoch_ten_payload)
        ).hexdigest()
        self.assertEqual(
            "NON_AUTHORIZING_B4_REGISTRY_SHAPE_VALID",
            validity_profile_b4_registry_shape_result(registry),
        )
        self.assertEqual(
            "DENY_B4_CURRENT_REGISTRY_CHECKPOINT_OR_RUNTIME_TRUST_UNAVAILABLE",
            authority_result(epoch_ten, registry),
        )
        reset_empty_epoch_ten_registry = {
            **registry,
            "latest_owner_epoch": 10,
        }
        self.assertEqual(
            "DENY_B4_DURABLE_REGISTRY_PROOF_INVALID",
            authority_result(
                epoch_ten, reset_empty_epoch_ten_registry
            ),
        )
        reset_genesis_and_head_epoch_ten_registry = {
            **registry,
            "genesis_owner_epoch": 10,
            "latest_owner_epoch": 10,
        }
        self.assertEqual(
            "DENY_B4_DURABLE_REGISTRY_PROOF_INVALID",
            authority_result(
                epoch_ten, reset_genesis_and_head_epoch_ten_registry
            ),
        )
        for binding_mutation in (
            {"registry_id": "fresh-epoch-ten-registry"},
            {"registry_scope": "EPOCH_SCOPED"},
            {"genesis_sha256": "0" * 64},
        ):
            self.assertEqual(
                "DENY_B4_DURABLE_REGISTRY_PROOF_INVALID",
                authority_result(
                    epoch_ten,
                    {**registry, **binding_mutation},
                ),
            )
        global_epoch_ten_registry = {
            **consumed_registry,
        }
        self.assertEqual(
            "DENY_B4_PARENT_ALREADY_CONSUMED",
            authority_result(
                epoch_ten, global_epoch_ten_registry
            ),
        )
        manifest_registry = {
            "trusted": True,
            "complete": True,
            "append_only": True,
            "latest_sequence": 1,
            "records": [prior_manifest_record],
        }
        self.assertEqual(
            "DENY_OLD_OPERATING_MANIFEST_REUSE",
            validity_profile_operating_manifest_result(
                consumed,
                prior_manifest_bytes,
                manifest_sha256=prior_manifest_sha,
                prior_manifest_bytes=prior_manifest_bytes,
                prior_manifest_sha256=prior_manifest_sha,
                manifest_registry=manifest_registry,
            ),
        )
        new_manifest = {
            "manifest_ref": "operating/bitget-pilot-v2-v2.json",
            "manifest_version": 2,
            "manifest_sequence": 2,
            "supersedes_ref": prior_manifest["manifest_ref"],
            "supersedes_version": prior_manifest["manifest_version"],
            "supersedes_sequence": prior_manifest["manifest_sequence"],
            "supersedes_sha256": prior_manifest_sha,
            "change_action_id": consumed["action_id"],
            "change_payload_sha256": consumed[
                "canonical_action_payload_sha256"
            ],
            "profile_sha256": consumed["new_profile_sha256"],
            "configuration_sha256": consumed["new_configuration_sha256"],
            "effective_from": "2030-01-01T00:00:00.700000Z",
            "expires_at": "2030-01-01T00:00:00.900000Z",
            "status": "SEPARATELY_APPROVED_NON_AUTHORIZING_SHAPE",
        }
        new_manifest_bytes = canonical_json_bytes(new_manifest)
        self.assertEqual(
            "NON_AUTHORIZING_NEW_OPERATING_MANIFEST_BINDING_SHAPE_VALID",
            validity_profile_operating_manifest_result(
                consumed,
                new_manifest_bytes,
                manifest_sha256=hashlib.sha256(new_manifest_bytes).hexdigest(),
                prior_manifest_bytes=prior_manifest_bytes,
                prior_manifest_sha256=prior_manifest_sha,
                manifest_registry=manifest_registry,
            ),
        )
        reused_configuration_manifest = {
            **new_manifest,
            "configuration_sha256": prior_manifest[
                "configuration_sha256"
            ],
        }
        reused_configuration_bytes = canonical_json_bytes(
            reused_configuration_manifest
        )
        self.assertEqual(
            "DENY_OLD_CONFIGURATION_REUSE",
            validity_profile_operating_manifest_result(
                consumed,
                reused_configuration_bytes,
                manifest_sha256=hashlib.sha256(
                    reused_configuration_bytes
                ).hexdigest(),
                prior_manifest_bytes=prior_manifest_bytes,
                prior_manifest_sha256=prior_manifest_sha,
                manifest_registry=manifest_registry,
            ),
        )
        manifest_mutations = (
            {"manifest_ref": "operating/Bitget-v2.json"},
            {"manifest_ref": "./operating/bitget-pilot-v2-v2.json"},
            {"manifest_ref": "operating//bitget-pilot-v2-v2.json"},
            {"manifest_ref": "operating/x/../bitget-pilot-v2-v2.json"},
            {"manifest_version": True},
            {"manifest_sequence": 0},
            {"manifest_sequence": 1},
            {"supersedes_ref": "operating/other-v1.json"},
            {"supersedes_version": 2},
            {"supersedes_sequence": 2},
            {"supersedes_sha256": "8" * 64},
            {"change_action_id": "wrong-change"},
            {"change_payload_sha256": "8" * 64},
            {"profile_sha256": "8" * 64},
            {"configuration_sha256": "8" * 64},
            {"effective_from": "2030-01-01T00:00:00.500000Z"},
            {"expires_at": "2030-01-01T00:00:00.500000Z"},
        )
        for mutation in manifest_mutations:
            mutated_manifest = {**new_manifest, **mutation}
            mutated_bytes = canonical_json_bytes(mutated_manifest)
            self.assertTrue(
                validity_profile_operating_manifest_result(
                    consumed,
                    mutated_bytes,
                    manifest_sha256=hashlib.sha256(mutated_bytes).hexdigest(),
                    prior_manifest_bytes=prior_manifest_bytes,
                    prior_manifest_sha256=prior_manifest_sha,
                    manifest_registry=manifest_registry,
                ).startswith("DENY_")
            )
        same_identity_different_digest = {
            **new_manifest,
            "manifest_ref": prior_manifest["manifest_ref"],
            "manifest_version": prior_manifest["manifest_version"],
            "manifest_sequence": prior_manifest["manifest_sequence"],
        }
        conflicting_candidate_bytes = canonical_json_bytes(
            same_identity_different_digest
        )
        self.assertEqual(
            "DENY_OPERATING_MANIFEST_IDENTITY_DIGEST_CONFLICT",
            validity_profile_operating_manifest_result(
                consumed,
                conflicting_candidate_bytes,
                manifest_sha256=hashlib.sha256(
                    conflicting_candidate_bytes
                ).hexdigest(),
                prior_manifest_bytes=prior_manifest_bytes,
                prior_manifest_sha256=prior_manifest_sha,
                manifest_registry=manifest_registry,
            ),
        )
        conflicting_prior = {
            **prior_manifest,
            "configuration_sha256": "6" * 64,
        }
        conflicting_prior_bytes = canonical_json_bytes(conflicting_prior)
        conflicting_registry = {
            **manifest_registry,
            "latest_sequence": 2,
            "records": [
                *manifest_registry["records"],
                {
                    **manifest_registry["records"][0],
                    "manifest_sha256": hashlib.sha256(
                        conflicting_prior_bytes
                    ).hexdigest(),
                    "manifest_bytes": conflicting_prior_bytes,
                },
            ],
        }
        self.assertEqual(
            "DENY_OPERATING_MANIFEST_IDENTITY_DIGEST_CONFLICT",
            validity_profile_operating_manifest_result(
                consumed,
                new_manifest_bytes,
                manifest_sha256=hashlib.sha256(
                    new_manifest_bytes
                ).hexdigest(),
                prior_manifest_bytes=prior_manifest_bytes,
                prior_manifest_sha256=prior_manifest_sha,
                manifest_registry=conflicting_registry,
            ),
        )
        self.assertEqual(
            "DENY_OPERATING_MANIFEST_REGISTRY_OR_PRIOR_INVALID",
            validity_profile_operating_manifest_result(
                consumed,
                new_manifest_bytes,
                manifest_sha256=hashlib.sha256(
                    new_manifest_bytes
                ).hexdigest(),
                prior_manifest_bytes=prior_manifest_bytes,
                prior_manifest_sha256=prior_manifest_sha,
                manifest_registry={**manifest_registry, "trusted": False},
            ),
        )
        noncanonical_manifest_bytes = json.dumps(
            new_manifest, sort_keys=True, indent=2
        ).encode("utf-8")
        self.assertEqual(
            "DENY_MALFORMED_OPERATING_MANIFEST",
            validity_profile_operating_manifest_result(
                consumed,
                noncanonical_manifest_bytes,
                manifest_sha256=hashlib.sha256(
                    noncanonical_manifest_bytes
                ).hexdigest(),
                prior_manifest_bytes=prior_manifest_bytes,
                prior_manifest_sha256=prior_manifest_sha,
                manifest_registry=manifest_registry,
            ),
        )
        for malformed_bytes, malformed_hash in (
            (b"", hashlib.sha256(b"").hexdigest()),
            (new_manifest_bytes, ""),
            (new_manifest_bytes, None),
        ):
            self.assertTrue(
                validity_profile_operating_manifest_result(
                    consumed,
                    malformed_bytes,
                    manifest_sha256=malformed_hash,
                    prior_manifest_bytes=prior_manifest_bytes,
                    prior_manifest_sha256=prior_manifest_sha,
                    manifest_registry=manifest_registry,
                ).startswith("DENY_")
            )

    def test_late_ack_sunset_and_cross_risk_remain_fail_closed(self) -> None:
        escalation = {
            "first_durable_unknown_at": "2030-01-01T00:00:00Z",
            "escalation_due_at": "2030-01-01T00:00:00.500000Z",
            "now_utc": "2030-01-01T00:00:01Z",
            "dispatch_at": "2030-01-01T00:00:00.600000Z",
            "ack_at": "2030-01-01T00:00:00.700000Z",
            "profile_state": "INVALIDATED",
            "exposure_retained": True,
            "reservation_retained": True,
            "reconciliation_required": True,
            "authority_restored": False,
            "terminal_outcome_verified": False,
        }
        self.assertEqual(
            "NON_AUTHORIZING_SUSPEND_OR_INVALIDATE_RETAIN_BLOCK",
            validity_reconciliation_escalation_result(
                escalation, reconciliation_escalation_deadline_ms=500
            ),
        )
        future_ack = {
            **escalation,
            "escalation_due_at": "2030-01-01T00:00:02Z",
            "now_utc": "2030-01-01T00:00:00.100000Z",
            "dispatch_at": "2030-01-01T00:00:00.800000Z",
            "ack_at": "2030-01-01T00:00:00.900000Z",
            "profile_state": "ACTIVE",
        }
        self.assertTrue(
            validity_reconciliation_escalation_result(
                future_ack, reconciliation_escalation_deadline_ms=2000
            ).startswith("DENY_")
        )
        future_first = {
            **escalation,
            "first_durable_unknown_at": "2030-01-01T00:00:02Z",
            "escalation_due_at": "2030-01-01T00:00:02.500000Z",
            "dispatch_at": None,
            "ack_at": None,
            "now_utc": "2030-01-01T00:00:01Z",
            "profile_state": "ACTIVE",
        }
        self.assertTrue(
            validity_reconciliation_escalation_result(
                future_first, reconciliation_escalation_deadline_ms=500
            ).startswith("DENY_")
        )
        self.assertEqual(
            "DENY_LATE_ACK_AUTHORITY_REBOUND",
            validity_reconciliation_escalation_result(
                {**escalation, "authority_restored": True},
                reconciliation_escalation_deadline_ms=500,
            ),
        )
        sunset = {
            "mandatory_cutoffs": {
                "approval": "2030-01-01T00:00:01Z",
                "evidence": "2030-01-01T00:00:02Z",
                "capability": "2030-01-01T00:00:03Z",
                "risk_policy": "2030-01-01T00:00:04Z",
                "runtime_protection": "2030-01-01T00:00:05Z",
            },
            "cancel_reconciliation_buffer_ms": 100,
            "computed_sunset_deadline": "2030-01-01T00:00:00.900000Z",
            "order_id": "strict-sunset-order-1",
            "order_expiry_at": "2030-01-01T00:00:00.900000Z",
            "now_utc": "2030-01-01T00:00:01Z",
            "revoked": False,
            "remaining_opening_or_conditional_orders": 0,
            "unknown_or_possible_fills": False,
            "completion_proof": {
                "terminal_order_outcomes_complete": True,
                "fill_trade_watermark_complete": False,
                "positions_reconciled": True,
                "balances_reconciled": True,
                "child_orders_reconciled": True,
                "reservation_proof_status": "DURABLE_TERMINAL_RELEASE_OR_TRANSFER",
            },
        }
        self.assertEqual(
            "RECONCILIATION_REQUIRED_UNKNOWN_FILLS_OR_INCOMPLETE_PROOF",
            validity_profile_sunset_result(sunset),
        )
        complete = copy.deepcopy(sunset)
        complete["completion_proof"]["fill_trade_watermark_complete"] = True
        self.assertEqual(
            "NON_AUTHORIZING_SUNSET_DURABLY_RECONCILED",
            validity_profile_sunset_result(complete),
        )
        for cutoff_name in (
            "evidence",
            "capability",
            "risk_policy",
            "runtime_protection",
        ):
            nonapproval_earliest = copy.deepcopy(sunset)
            nonapproval_earliest["mandatory_cutoffs"][
                cutoff_name
            ] = "2030-01-01T00:00:00.800000Z"
            nonapproval_earliest[
                "computed_sunset_deadline"
            ] = "2030-01-01T00:00:00.700000Z"
            nonapproval_earliest[
                "order_expiry_at"
            ] = "2030-01-01T00:00:00.700000Z"
            nonapproval_earliest[
                "now_utc"
            ] = "2030-01-01T00:00:00.600000Z"
            self.assertEqual(
                "NON_AUTHORIZING_BOUNDED_BEFORE_SUNSET",
                validity_profile_sunset_result(nonapproval_earliest),
            )
            nonapproval_earliest[
                "order_expiry_at"
            ] = "2030-01-01T00:00:00.700001Z"
            self.assertEqual(
                "DENY_ORDER_EXPIRY_AFTER_SUNSET_DEADLINE",
                validity_profile_sunset_result(nonapproval_earliest),
            )
        self.assertEqual(
            "DENY_MALFORMED_SUNSET_PROOF",
            validity_profile_sunset_result({**sunset, "order_id": ""}),
        )
        lower_values = {
            "operating_ttl_ms": 1000,
            "cancel_reconciliation_buffer_ms": 200,
            "dispatch_guard_ms": 100,
            "clock_skew_tolerance_ms": 20,
            "revocation_snapshot_max_age_ms": 100,
            "review_lead_time_ms": 300,
            "reconciliation_escalation_deadline_ms": 500,
        }
        cross_risk_scope = {
            field: self.profile["exact_key"][field]
            for field in CROSS_RISK_SCOPE_FIELDS
        }
        cross_risk_scope.update({
            "venue_capability_profile_id": "bitget-capability-v1",
            "venue_capability_profile_sha256": "1" * 64,
            "calibration_stratum_id": "bitget-normal-stratum-v1",
            "calibration_stratum_sha256": "2" * 64,
            "liquidity_regime": "NORMAL",
            "volatility_regime": "NORMAL",
            "degraded_state": "NORMAL",
        })
        scope_sha256 = hashlib.sha256(
            canonical_json_bytes(cross_risk_scope)
        ).hexdigest()
        lower = {
            "profile_id": "bitget-b1-owner-epoch-3",
            "profile_payload_sha256": "a" * 64,
            "owner_epoch": 3,
            "capital_stage": "PILOT_LIMITED_LIVE",
            "action_class": "PILOT_OPERATING_SCOPE",
            "action_family": "OPERATING",
            "risk_class": "B1_LIMITED_PILOT",
            "scope": cross_risk_scope,
            "values": lower_values,
            "authorized_actions": ["LIMIT_OPEN", "CANCEL"],
        }
        higher = {
            **lower,
            "profile_id": "bitget-b2-owner-epoch-3",
            "profile_payload_sha256": "b" * 64,
            "capital_stage": "PRODUCTION_LIVE",
            "action_class": "PRODUCTION_OPERATING_SCOPE",
            "risk_class": "B2_EXISTING_PRODUCTION",
            "values": {
                **lower_values,
                "operating_ttl_ms": 900,
                "cancel_reconciliation_buffer_ms": 250,
            },
            "authorized_actions": ["CANCEL"],
        }
        history = {
            "registry_id": "validity-profile-family-history-v1",
            "owner_epoch": 3,
            "base_sequence": 0,
            "latest_sequence": 2,
            "complete": True,
            "immutable": True,
            "as_of_utc": "2030-01-01T12:00:00Z",
            "entries": [
                {
                    "sequence": sequence,
                    "profile_id": profile["profile_id"],
                    "profile_payload_sha256": profile[
                        "profile_payload_sha256"
                    ],
                    "owner_epoch": 3,
                    "scope_sha256": scope_sha256,
                    "risk_class": profile["risk_class"],
                    "lifecycle_state": "ACTIVE",
                    "valid_from": "2030-01-01T00:00:00Z",
                    "expires_at": "2030-01-02T00:00:00Z",
                    "superseded_at": None,
                }
                for sequence, profile in enumerate(
                    (lower, higher),
                    start=1,
                )
            ],
        }
        self.assertEqual(
            "NON_AUTHORIZING_CROSS_RISK_ORDER_SHAPE_VALID",
            validity_profile_cross_risk_result(lower, higher, history),
        )
        weaker = copy.deepcopy(higher)
        weaker["values"]["operating_ttl_ms"] = 1100
        self.assertEqual(
            "DENY_HIGHER_RISK_DURATION_VECTOR_WEAKER",
            validity_profile_cross_risk_result(lower, weaker, history),
        )
        self.assertEqual(
            "DENY_INCOMPLETE_OR_UNTRUSTED_CROSS_RISK_HISTORY",
            validity_profile_cross_risk_result(lower, higher),
        )
        cross_venue = copy.deepcopy(higher)
        cross_venue["scope"]["venue_id"] = "MOEX"
        self.assertEqual(
            "DENY_CROSS_RISK_SCOPE_OR_FAMILY_MISMATCH",
            validity_profile_cross_risk_result(
                lower,
                cross_venue,
                history,
            ),
        )
        caller_family_lower = {**lower, "family_id": "caller-family"}
        caller_family_higher = {**higher, "family_id": "caller-family"}
        self.assertEqual(
            "DENY_INCOMPARABLE_CROSS_RISK_PROFILE",
            validity_profile_cross_risk_result(
                caller_family_lower,
                caller_family_higher,
                history,
            ),
        )
        inactive_history = copy.deepcopy(history)
        inactive_history["entries"][1][
            "lifecycle_state"
        ] = "SUSPENDED"
        self.assertEqual(
            "DENY_CROSS_RISK_PROFILES_NOT_SIMULTANEOUSLY_ACTIVE",
            validity_profile_cross_risk_result(
                lower,
                higher,
                inactive_history,
            ),
        )
        omitted_history_entry = copy.deepcopy(history)
        omitted_history_entry["entries"].pop()
        self.assertEqual(
            "DENY_INCOMPLETE_OR_UNTRUSTED_CROSS_RISK_HISTORY",
            validity_profile_cross_risk_result(
                lower,
                higher,
                omitted_history_entry,
            ),
        )
        for mechanics_field in (
            "venue_id",
            "venue_environment",
            "market_id",
            "api_or_protocol_version",
            "account_mode",
            "order_type",
            "time_in_force",
            "session_id",
        ):
            for unhashable in ([], {}, set()):
                malformed_scope = copy.deepcopy(cross_risk_scope)
                malformed_scope[mechanics_field] = unhashable
                self.assertTrue(
                    _venue_mechanics_result(
                        malformed_scope
                    ).startswith("DENY_")
                )
                malformed_lower = copy.deepcopy(lower)
                malformed_higher = copy.deepcopy(higher)
                malformed_lower["scope"] = copy.deepcopy(malformed_scope)
                malformed_higher["scope"] = copy.deepcopy(malformed_scope)
                self.assertTrue(
                    validity_profile_cross_risk_result(
                        malformed_lower,
                        malformed_higher,
                        history,
                    ).startswith("DENY_")
                )
        for profile_field in (
            "profile_id",
            "profile_payload_sha256",
            "risk_class",
        ):
            for malformed_identity in ([], {}, set()):
                malformed_lower = copy.deepcopy(lower)
                malformed_lower[profile_field] = malformed_identity
                self.assertTrue(
                    validity_profile_cross_risk_result(
                        malformed_lower,
                        higher,
                        history,
                    ).startswith("DENY_")
                )
        for scope_identity_field in (
            "venue_capability_profile_id",
            "venue_capability_profile_version",
            "venue_capability_profile_sha256",
            "risk_policy_id",
            "risk_policy_version",
            "risk_policy_sha256",
            "calibration_stratum_id",
            "calibration_stratum_sha256",
        ):
            for malformed_identity in ([], {}, set()):
                malformed_scope = copy.deepcopy(cross_risk_scope)
                malformed_scope[scope_identity_field] = malformed_identity
                malformed_lower = copy.deepcopy(lower)
                malformed_higher = copy.deepcopy(higher)
                malformed_lower["scope"] = copy.deepcopy(malformed_scope)
                malformed_higher["scope"] = copy.deepcopy(malformed_scope)
                self.assertTrue(
                    validity_profile_cross_risk_result(
                        malformed_lower,
                        malformed_higher,
                        history,
                    ).startswith("DENY_")
                )
        for history_field in (
            "profile_id",
            "profile_payload_sha256",
            "scope_sha256",
            "risk_class",
            "lifecycle_state",
        ):
            for malformed_identity in ([], {}, set()):
                malformed_history = copy.deepcopy(history)
                malformed_history["entries"][0][
                    history_field
                ] = malformed_identity
                self.assertTrue(
                    validity_profile_cross_risk_result(
                        lower,
                        higher,
                        malformed_history,
                    ).startswith("DENY_")
                )
        matched_scope_forgery_mutations = (
            ("venue_capability_profile_id", ""),
            ("venue_capability_profile_id", "x"),
            (
                "venue_capability_profile_id",
                "UNRESOLVED_NONAUTHORIZING_CAPABILITY",
            ),
            ("venue_capability_profile_id", "PENDING_CAPABILITY"),
            ("venue_capability_profile_id", "PENDINGCAPABILITY"),
            ("venue_capability_profile_id", "PENDING-CAPABILITY"),
            ("venue_capability_profile_id", "NOT_IMPLEMENTED_CAPABILITY"),
            ("venue_capability_profile_version", True),
            ("venue_capability_profile_version", 0),
            ("venue_capability_profile_version", "1"),
            ("venue_capability_profile_sha256", "A" * 64),
            ("venue_capability_profile_sha256", "0" * 63),
            ("venue_capability_profile_sha256", "0" * 64),
            ("calibration_stratum_id", ""),
            (
                "calibration_stratum_id",
                "UNRESOLVED_NONAUTHORIZING_STRATUM",
            ),
            ("calibration_stratum_id", "PENDING_STRATUM"),
            ("calibration_stratum_id", "NOT_IMPLEMENTED_STRATUM"),
            ("calibration_stratum_sha256", "A" * 64),
            ("calibration_stratum_sha256", "0" * 63),
            ("calibration_stratum_sha256", "0" * 64),
            ("risk_policy_version", True),
            ("risk_policy_sha256", "A" * 64),
            ("liquidity_regime", "UNKNOWN"),
            ("liquidity_regime", "UNRESOLVED_DENY"),
            ("volatility_regime", "UNKNOWN"),
            ("volatility_regime", "UNRESOLVED_DENY"),
            ("degraded_state", "UNKNOWN"),
            ("degraded_state", "UNRESOLVED_DENY"),
            ("api_or_protocol_version", "CALLER_API"),
            ("api_or_protocol_version", "PENDING_API"),
            ("account_mode", "CALLER_ACCOUNT"),
            ("account_mode", "NOT_IMPLEMENTED_ACCOUNT"),
            ("order_type", "CALLER_ORDER"),
            ("time_in_force", "CALLER_TIF"),
            ("session_id", "CALLER_SESSION"),
            ("session_id", "UNRESOLVED_DENY"),
        )
        for scope_field, malformed_value in matched_scope_forgery_mutations:
            forged_scope = copy.deepcopy(cross_risk_scope)
            forged_scope[scope_field] = malformed_value
            forged_lower = copy.deepcopy(lower)
            forged_higher = copy.deepcopy(higher)
            forged_lower["scope"] = copy.deepcopy(forged_scope)
            forged_higher["scope"] = copy.deepcopy(forged_scope)
            forged_history = copy.deepcopy(history)
            forged_scope_sha256 = hashlib.sha256(
                canonical_json_bytes(forged_scope)
            ).hexdigest()
            for entry in forged_history["entries"]:
                entry["scope_sha256"] = forged_scope_sha256
            self.assertEqual(
                "DENY_CROSS_RISK_SCOPE_OR_FAMILY_MISMATCH",
                validity_profile_cross_risk_result(
                    forged_lower,
                    forged_higher,
                    forged_history,
                ),
                (scope_field, malformed_value),
            )
        draft_scope = {
            field: self.profile["exact_key"][field]
            for field in CROSS_RISK_SCOPE_FIELDS
        }
        draft_lower = copy.deepcopy(lower)
        draft_higher = copy.deepcopy(higher)
        draft_lower["scope"] = copy.deepcopy(draft_scope)
        draft_higher["scope"] = copy.deepcopy(draft_scope)
        caller_active_draft_history = copy.deepcopy(history)
        draft_scope_sha256 = hashlib.sha256(
            canonical_json_bytes(draft_scope)
        ).hexdigest()
        for entry in caller_active_draft_history["entries"]:
            entry["scope_sha256"] = draft_scope_sha256
            entry["lifecycle_state"] = "ACTIVE"
        self.assertEqual(
            "DENY_CROSS_RISK_SCOPE_OR_FAMILY_MISMATCH",
            validity_profile_cross_risk_result(
                draft_lower,
                draft_higher,
                caller_active_draft_history,
            ),
        )
        for bypass_family in ("NON_CAPITAL", "SINGLE_USE", ""):
            bypass_lower = {
                **lower,
                "action_family": bypass_family,
                "values": {},
            }
            bypass_higher = {
                **higher,
                "action_family": bypass_family,
                "values": {},
            }
            self.assertEqual(
                "DENY_INCOMPARABLE_CROSS_RISK_PROFILE",
                validity_profile_cross_risk_result(
                    bypass_lower, bypass_higher, history
                ),
            )

    def test_calibration_recommendation_is_typed_and_inside_owner_bounds(self) -> None:
        profile = copy.deepcopy(self.profile)
        values = {
            "operating_ttl_ms": 1000,
            "cancel_reconciliation_buffer_ms": 200,
            "dispatch_guard_ms": 100,
            "clock_skew_tolerance_ms": 20,
            "revocation_snapshot_max_age_ms": 100,
            "review_lead_time_ms": 300,
            "reconciliation_escalation_deadline_ms": 500,
        }
        profile["owner_hard_bounds"] = {"status": "VERIFIED", "values": values}
        profile["owner_selected_effective_values"] = {
            "status": "VERIFIED",
            "values": copy.deepcopy(values),
        }
        profile["calibration_recommendation"] = {
            "status": "NON_AUTHORIZING_RECOMMENDATION",
            "values": copy.deepcopy(values),
        }
        self.assertEqual(
            "NON_AUTHORIZING_OWNER_BOUNDS_SHAPE_VALID",
            validity_profile_owner_bounds_result(profile),
        )
        outside = copy.deepcopy(profile)
        outside["calibration_recommendation"]["values"]["operating_ttl_ms"] = 1001
        self.assertEqual(
            "DENY_CALIBRATION_RECOMMENDATION_OUTSIDE_OWNER_BOUND",
            validity_profile_owner_bounds_result(outside),
        )
        boolean = copy.deepcopy(profile)
        boolean["calibration_recommendation"]["values"]["dispatch_guard_ms"] = True
        self.assertEqual(
            "DENY_MISSING_OR_INCOMPARABLE_OWNER_BOUND",
            validity_profile_owner_bounds_result(boolean),
        )


if __name__ == "__main__":
    unittest.main()
