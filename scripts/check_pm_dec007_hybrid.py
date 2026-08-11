#!/usr/bin/env python3
"""PM-DEC-007 v1 non-authorizing hybrid trust contract checks.

This module validates only the immutable architecture record and caller-supplied
factor *shape*.  It does not parse the opaque payload, verify cryptography,
classify replay/freshness, trust a checkpoint, or authorize an adapter call.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tomllib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]

PM_DEC007_RECORD_VALID = (
    "NON_AUTHORIZING_PM_DEC_007_ARCHITECTURE_SHAPE_VALID"
)
PM_DEC007_RECORD_INVALID = "DENY_PM_DEC_007_RECORD_INVALID"
PM_DEC007_BINDING_VALID = (
    "NON_AUTHORIZING_PM_DEC_007_HYBRID_BINDING_SHAPE_VALID"
)
PM_DEC007_FACTOR_SHAPE_INVALID = "DENY_PM_DEC_007_FACTOR_SHAPE_INVALID"
PM_DEC007_FACTORS_NOT_INDEPENDENT = (
    "DENY_PM_DEC_007_FACTORS_NOT_INDEPENDENT"
)
PM_DEC007_PAYLOAD_BINDING_MISMATCH = (
    "DENY_PM_DEC_007_PAYLOAD_BINDING_MISMATCH"
)
PM_DEC007_CALLER_AUTHORITY_CLAIM = (
    "DENY_PM_DEC_007_CALLER_AUTHORITY_CLAIM"
)
PM_DEC007_CHECKPOINT_UNAVAILABLE = (
    "DENY_PM_DEC_007_TRUSTED_CHECKPOINT_UNAVAILABLE"
)
PM_DEC007_RUNTIME_TRUST_INCOMPLETE = (
    "DENY_PM_DEC_007_RUNTIME_TRUST_INCOMPLETE"
)

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")
UTC_PATTERN = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z"
)

FACTOR_FIELDS = frozenset(
    {
        "factor_record_version",
        "role",
        "factor_class",
        "factor_id",
        "trust_set_id",
        "owner_identity_ref",
        "owner_trust_epoch",
        "global_sequence_namespace_id",
        "trust_root_id",
        "failure_domain_id",
        "key_material_id",
        "device_id",
        "session_id",
        "admin_domain_id",
        "recovery_path_id",
        "manifest_id",
        "manifest_version",
        "monotonic_sequence",
        "action_class",
        "payload_sha256",
        "scope_sha256",
        "limits_sha256",
        "artifact_set_sha256",
        "configuration_sha256",
        "effective_from",
        "review_due_at",
        "expires_at",
        "factor_evidence_ref",
    }
)

TOKEN_FIELDS = (
    "factor_id",
    "trust_set_id",
    "owner_identity_ref",
    "global_sequence_namespace_id",
    "trust_root_id",
    "failure_domain_id",
    "key_material_id",
    "device_id",
    "session_id",
    "admin_domain_id",
    "recovery_path_id",
    "manifest_id",
    "action_class",
    "factor_evidence_ref",
)

POSITIVE_INTEGER_FIELDS = (
    "owner_trust_epoch",
    "manifest_version",
    "monotonic_sequence",
)

DIGEST_FIELDS = (
    "payload_sha256",
    "scope_sha256",
    "limits_sha256",
    "artifact_set_sha256",
    "configuration_sha256",
)

TIMESTAMP_FIELDS = ("effective_from", "review_due_at", "expires_at")

DISTINCT_FIELDS = (
    "factor_id",
    "trust_root_id",
    "failure_domain_id",
    "key_material_id",
    "device_id",
    "session_id",
    "admin_domain_id",
    "recovery_path_id",
    "factor_evidence_ref",
)

EQUAL_BINDING_FIELDS = (
    "factor_record_version",
    "trust_set_id",
    "owner_identity_ref",
    "owner_trust_epoch",
    "global_sequence_namespace_id",
    "manifest_id",
    "manifest_version",
    "monotonic_sequence",
    "action_class",
    "payload_sha256",
    "scope_sha256",
    "limits_sha256",
    "artifact_set_sha256",
    "configuration_sha256",
    "effective_from",
    "review_due_at",
    "expires_at",
)

_AUTHORITY_STRING_CLAIMS = frozenset(
    {
        "VALID",
        "TRUSTED",
        "CURRENT",
        "APPROVED",
        "ACTIVE",
        "VERIFIED",
        "EVIDENCE_READY",
        "PILOT",
        "PRODUCTION",
    }
)

_AUTHORITY_KEY_FRAGMENTS = (
    "VALID",
    "TRUST",
    "CURRENT",
    "APPROV",
    "ACTIVE",
    "VERIF",
    "EVIDENCE",
    "PILOT",
    "PRODUCTION",
    "INDEPENDEN",
    "AUTHORITY",
    "STAGE",
    "STATUS",
)

REQUIRED_ARTIFACT_HASHES = (
    (
        "specs/pm-dec-007-hybrid-trust-v1/spec.md",
        "faf45536b935d58ddd71d22b14c9a29ecb93d2951d5e58001d42c15640aa0ef5",
    ),
    (
        "specs/pm-dec-007-hybrid-trust-v1/acceptance.toml",
        "04975d5c1c5fdfdbb2f11b087870bd1c6c27f1d433f510b88f213abfd01ff553",
    ),
    (
        "docs/FROZEN_CORE_V11.sha256",
        "46f20183230d84f6fdaba9ccc63e8e504afcd2be77c4447c66a14f5a9be5390f",
    ),
    (
        "governance/approval-policy.toml",
        "9be5ef3804dd8a35681526e9b154d50c0162ba610101dcbabd00ce29996a8708",
    ),
    (
        "governance/risk-policy.toml",
        "4f34d45ac058bec6d5ce1ecc05dc242572a917bd6e2f6769ff53b7115f4b72e8",
    ),
    (
        "specs/portfolio-mandate-v1/decisions/PM-DEC-002.toml",
        "eec0aa8d667b18be160e8b5ac98e1e6bcc3a7ec4037993a8bc57f1b36492af7b",
    ),
    (
        "specs/portfolio-mandate-v1/decisions/PM-DEC-003.toml",
        "618dd1da08fb6a8f7f0631fa6824bea1cc527d071e035b20b9250bcd374789ce",
    ),
)

EXPECTED_PM_DEC007_RECORD = {
    "decision_id": "PM-DEC-007",
    "decision_version": 1,
    "status": "PARTIALLY_RESOLVED_ARCHITECTURE_ONLY",
    "selected_option": 1,
    "selected_model": "HYBRID_PHYSICAL_KEY_PLUS_SEPARATE_DEVICE",
    "decision_type": "LEVEL_B_RUNTIME_TRUST_CONTOUR",
    "decided_by_ref": "OWNER",
    "decision_evidence_ref": "conversation:2026-07-24:PM-DEC-007:hybrid-selection",
    "recorded_at": "2026-07-24T10:07:27Z",
    "authorization_effect": "NONE",
    "implementation_status": "NOT_IMPLEMENTED",
    "eligible_for_real_capital_authorization": False,
    "artifact_ratification_eligible": False,
    "real_capital_authority": False,
    "pilot_status": "BLOCKED",
    "production_status": "BLOCKED",
    "live_trading_enabled": False,
    "moex_status": "FUTURE_BLOCKED",
    "changes_governance_policies": False,
    "numeric_validity_profile_status": "OWNER_INPUT_REQUIRED",
    "parent_frozen_manifest_ref": "docs/FROZEN_CORE_V11.sha256",
    "parent_frozen_manifest_sha256": (
        "46f20183230d84f6fdaba9ccc63e8e504afcd2be77c4447c66a14f5a9be5390f"
    ),
    "primary_factor": {
        "role": "PRIMARY_CRYPTOGRAPHIC_SIGNATURE",
        "factor_class": "PHYSICAL_HARDWARE_SIGNING_KEY",
        "pinned_trust_root_required": True,
        "concrete_trust_root_ref": "UNRESOLVED",
        "key_material_ref": "UNRESOLVED",
        "carrier_provider_profile": "UNRESOLVED",
        "algorithm_profile": "UNRESOLVED",
    },
    "independent_confirmation": {
        "role": "INDEPENDENT_SECOND_CONFIRMATION",
        "factor_class": "SEPARATE_DEVICE_CONFIRMATION",
        "pinned_trust_root_required": True,
        "independently_verifiable_evidence_required": True,
        "concrete_trust_root_ref": "UNRESOLVED",
        "key_material_ref": "UNRESOLVED",
        "carrier_provider_profile": "UNRESOLVED",
        "attestation_profile": "UNRESOLVED",
    },
    "factor_independence": {
        "required_distinct_bindings": [
            "TRUST_ROOT_ID",
            "FAILURE_DOMAIN_ID",
            "KEY_MATERIAL_ID",
            "DEVICE_ID",
            "SESSION_ID",
            "ADMIN_DOMAIN_ID",
            "RECOVERY_PATH_ID",
        ],
        "same_owner_identity_allowed": True,
        "shared_binding_counts_as_independent": False,
        "independence_must_be_derived_from_pinned_profile": True,
        "caller_declared_independence_authoritative": False,
    },
    "same_payload_binding": {
        "same_exact_payload_bytes_required": True,
        "same_payload_sha256_required": True,
        "required_equal_bindings": [
            "TRUST_SET_ID",
            "OWNER_IDENTITY_REF",
            "OWNER_TRUST_EPOCH",
            "GLOBAL_SEQUENCE_NAMESPACE_ID",
            "MANIFEST_ID",
            "MANIFEST_VERSION",
            "MONOTONIC_SEQUENCE",
            "ACTION_CLASS",
            "PAYLOAD_SHA256",
            "SCOPE_SHA256",
            "LIMITS_SHA256",
            "ARTIFACT_SET_SHA256",
            "CONFIGURATION_SHA256",
            "EFFECTIVE_FROM",
            "REVIEW_DUE_AT",
            "EXPIRES_AT",
        ],
        "level_b_canonicalization_profile": "UNRESOLVED",
        "caller_validity_booleans_authoritative": False,
    },
    "factor_lifecycle": {
        "loss_or_compromise_result": (
            "SUSPEND_OR_REVOKE_TRUST_SET_DENY_NEW_AUTHORITY"
        ),
        "one_factor_only_recovery_allowed": False,
        "shared_recovery_backend_allowed": False,
        "replacement_requires_new_root_and_factor_ids": True,
        "replacement_requires_new_owner_trust_epoch": True,
        "replacement_requires_greater_monotonic_sequence": True,
        "old_roots_terminally_revoked": True,
        "old_manifest_reactivation_allowed": False,
        "exact_recovery_ceremony": "UNRESOLVED_OWNER_INPUT_REQUIRED",
    },
    "current_checkpoint": {
        "registry_mode": "INDEPENDENTLY_TRUSTED_APPEND_ONLY",
        "current_checkpoint_required": True,
        "independent_checkpoint_trust_root_required": True,
        "exact_registry_scope_genesis_head_binding_required": True,
        "contiguous_sequence_and_supersedes_digest_required": True,
        "root_lifecycle_and_revocation_epoch_binding_required": True,
        "owner_trust_epoch_and_trust_set_binding_required": True,
        "commit_time_dispatch_claim_cas_outbox_binding_required": True,
        "zero_adapter_call_on_preclaim_change_or_unavailability": True,
        "postclaim_uncertainty_result": (
            "RECONCILIATION_REQUIRED_NO_BLIND_RETRY"
        ),
        "required_distinct_from_both_factors": [
            "TRUST_ROOT_ID",
            "FAILURE_DOMAIN_ID",
            "ADMIN_DOMAIN_ID",
            "RECOVERY_PATH_ID",
            "RUNTIME_HOST_DOMAIN_ID",
        ],
        "caller_supplied_or_self_declared_head_authoritative": False,
        "shape_proves_currentness_freshness_or_persistence": False,
        "runtime_implementation_status": "UNRESOLVED",
    },
    "unresolved_dependencies": {
        "items": [
            "CRYPTOGRAPHIC_ALGORITHM_PROFILE",
            "LEVEL_B_CANONICALIZATION_PROFILE",
            "CONCRETE_CARRIERS_PROVIDERS_AND_PINNED_ROOTS",
            "ENROLLMENT_AND_ATTESTATION_PROTOCOL",
            "ROTATION_REVOCATION_COMPROMISE_AND_RECOVERY_PROTOCOL",
            "TRUSTED_CLOCK",
            "OWNER_NUMERIC_TTL_AND_FRESHNESS_VALUES",
            "RUNTIME_CRYPTOGRAPHIC_AND_ATTESTATION_VERIFIER",
            "DURABLE_APPEND_ONLY_REGISTRY_AND_CURRENT_CHECKPOINT_VERIFIER",
        ]
    },
    "safety": {
        "shape_success_authorization_effect": "NONE",
        "incomplete_runtime_result": PM_DEC007_RUNTIME_TRUST_INCOMPLETE,
        "live_real_capital_result": "BLOCKED",
        "moex_result": "FUTURE_BLOCKED",
        "physical_or_separate_device_labels_prove_independence": False,
        "caller_booleans_prove_validity_or_currentness": False,
        "pure_validator_is_trust_root": False,
    },
    "artifact_hashes": [
        {"path": path, "sha256": digest}
        for path, digest in REQUIRED_ARTIFACT_HASHES
    ],
    "integrity": {
        "canonicalization": (
            "SORTED_KEYS_COMPACT_UTF8_JSON_V1_"
            "NON_AUTHORIZING_DECISION_RECORD_ONLY"
        ),
        "decision_payload_sha256": (
            "766edbe430a551a62cbfa20682aadcb50f137ec684c060a84f30989a0da0a447"
        ),
        "level_b_manifest_canonicalization_ratified": False,
    },
}

FROZEN_CORE_V11_PATHS = (
    "scripts/self_check.py",
    "tests/test_portfolio_mandate.py",
    "specs/portfolio-mandate-v1/spec.md",
    "specs/portfolio-mandate-v1/acceptance.toml",
    "specs/portfolio-mandate-v1/plan.md",
    "specs/portfolio-mandate-v1/tasks.md",
    "specs/portfolio-mandate-v1/decisions/PM-DEC-003-v2.toml",
    "specs/portfolio-mandate-v1/validity-profiles/validity-profile.schema.json",
    "specs/portfolio-mandate-v1/validity-profiles/bitget-pilot-draft-v1.toml",
    "portfolio-mandate-v0.6.zip",
)

FROZEN_CORE_V12_PATHS = FROZEN_CORE_V11_PATHS
FROZEN_PM_DEC007_PATHS = (
    "specs/pm-dec-007-hybrid-trust-v1/spec.md",
    "specs/pm-dec-007-hybrid-trust-v1/acceptance.toml",
    "specs/pm-dec-007-hybrid-trust-v1/plan.md",
    "specs/pm-dec-007-hybrid-trust-v1/tasks.md",
    "specs/pm-dec-007-hybrid-trust-v1/decisions/PM-DEC-007.toml",
    "specs/pm-dec-007-hybrid-trust-v1/review.md",
    "scripts/check_pm_dec007_hybrid.py",
    "tests/test_pm_dec007_hybrid.py",
    "pm-dec-007-hybrid-trust-v0.1.zip",
)
HISTORICAL_CORE_MANIFEST = "docs/FROZEN_CORE_V11.sha256"
HISTORICAL_CORE_MANIFEST_SHA256 = (
    "46f20183230d84f6fdaba9ccc63e8e504afcd2be77c4447c66a14f5a9be5390f"
)
ACTIVE_CORE_MANIFEST = "docs/FROZEN_CORE_V12.sha256"
ACTIVE_CORE_MANIFEST_SHA256 = (
    "c58ce36af3d0b993cb45650f8ba7ff7392cc5a23fe50e72c42733c40ef800233"
)
HISTORICAL_PM_MANIFEST = "docs/FROZEN_PM_DEC_007_HYBRID_V1.sha256"
HISTORICAL_PM_MANIFEST_SHA256 = (
    "f6b8e859365bc00335b7a5b5b1a577c7784ebc75661f4f573839c98abcafcd53"
)
ACTIVE_PM_MANIFEST = "docs/FROZEN_PM_DEC_007_HYBRID_V2.sha256"

TRACEABILITY = {
    "PM-AC-059": ("PM-REQ-094",),
    "PM-AC-060": ("PM-REQ-094", "PM-REQ-095"),
    "PM-AC-061": ("PM-REQ-096",),
}

COMPLETED_IMPLEMENTATION_TASKS = {
    "PM7-TASK-020": ("PM-AC-059",),
    "PM7-TASK-021": ("PM-AC-060",),
    "PM7-TASK-022": ("PM-AC-061",),
    "PM7-TASK-023": ("PM-AC-059", "PM-AC-060", "PM-AC-061"),
}

DEFERRED_TASKS = (
    "PM7-TASK-100",
    "PM7-TASK-101",
    "PM7-TASK-102",
    "PM7-TASK-103",
    "PM7-TASK-104",
)

TOML_READ_ERRORS = (
    OSError,
    UnicodeDecodeError,
    tomllib.TOMLDecodeError,
    ValueError,
    RecursionError,
)


def _all_dictionary_keys_are_exact_strings(value: object) -> bool:
    """Traverse dictionaries without key comparison, hashing, or lookup."""
    pending = [value]
    visited: set[int] = set()
    while pending:
        current = pending.pop()
        if type(current) not in {dict, list}:
            continue
        identity = id(current)
        if identity in visited:
            continue
        visited.add(identity)
        if type(current) is dict:
            for key in current:
                if type(key) is not str:
                    return False
            pending.extend(current.values())
        else:
            pending.extend(current)
    return True


def _strict_equal(left: object, right: object) -> bool:
    """Compare recursively without Python's bool/int equality coercion."""
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        left_dict = left
        right_dict = right
        if any(type(key) is not str for key in left_dict):
            return False
        if any(type(key) is not str for key in right_dict):
            return False
        if left_dict.keys() != right_dict.keys():
            return False
        return all(_strict_equal(left_dict[key], right_dict[key]) for key in left_dict)
    if type(left) is list:
        left_list = left
        right_list = right
        return len(left_list) == len(right_list) and all(
            _strict_equal(left_item, right_item)
            for left_item, right_item in zip(left_list, right_list, strict=True)
        )
    return left == right


def _canonical_json_bytes(value: object) -> bytes | None:
    def valid(item: object) -> bool:
        if item is None or type(item) is bool or type(item) is str:
            return True
        if type(item) is int:
            return True
        if type(item) is list:
            return all(valid(child) for child in item)
        if type(item) is dict:
            return all(
                type(key) is str and bool(key) and valid(child)
                for key, child in item.items()
            )
        return False

    try:
        if not valid(value):
            return None
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (RecursionError, TypeError, ValueError, OverflowError):
        return None


def pm_dec007_payload_digest(record: object) -> str:
    """Digest the decision record excluding the self-referential integrity table."""
    if (
        type(record) is not dict
        or not _all_dictionary_keys_are_exact_strings(record)
    ):
        return ""
    payload = {key: value for key, value in record.items() if key != "integrity"}
    canonical = _canonical_json_bytes(payload)
    return hashlib.sha256(canonical).hexdigest() if canonical is not None else ""


def validate_pm_dec007_record(
    record: object,
    root: Path = ROOT,
) -> list[str]:
    """Validate the closed immutable PM-DEC-007 v1 architecture record."""
    errors: list[str] = []
    if type(record) is not dict:
        return ["PM-DEC-007 record must be an exact dictionary"]
    if not _all_dictionary_keys_are_exact_strings(record):
        return ["PM-DEC-007 record dictionary keys must be exact strings"]

    if not _strict_equal(record, EXPECTED_PM_DEC007_RECORD):
        errors.append("PM-DEC-007 closed decision record differs from v1")

    integrity = record.get("integrity")
    if type(integrity) is not dict:
        errors.append("PM-DEC-007 integrity table is missing or malformed")
    elif (
        integrity.get("decision_payload_sha256")
        != pm_dec007_payload_digest(record)
    ):
        errors.append("PM-DEC-007 canonical decision payload hash mismatch")

    artifact_entries = record.get("artifact_hashes")
    if type(artifact_entries) is not list:
        errors.append("PM-DEC-007 artifact hash table is missing or malformed")
        return errors

    expected_entries = [
        {"path": path, "sha256": digest}
        for path, digest in REQUIRED_ARTIFACT_HASHES
    ]
    if not _strict_equal(artifact_entries, expected_entries):
        errors.append("PM-DEC-007 artifact hash set differs from the exact v1 set")
        return errors

    root_path = Path(root)
    for relative, expected_digest in REQUIRED_ARTIFACT_HASHES:
        try:
            actual_digest = hashlib.sha256(
                (root_path / relative).read_bytes()
            ).hexdigest()
        except OSError as exc:
            errors.append(f"PM-DEC-007 bound artifact unavailable: {relative}: {exc}")
            continue
        if actual_digest != expected_digest:
            errors.append(f"PM-DEC-007 bound artifact hash mismatch: {relative}")
    return errors


def pm_dec007_record_result(record: object, root: Path = ROOT) -> str:
    """Return a non-authorizing record-shape result."""
    return (
        PM_DEC007_RECORD_VALID
        if not validate_pm_dec007_record(record, root)
        else PM_DEC007_RECORD_INVALID
    )


def _parse_strict_utc(value: object) -> datetime | None:
    if type(value) is not str or UTC_PATTERN.fullmatch(value) is None:
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    if parsed.utcoffset() != timedelta(0):
        return None
    return parsed


def _has_caller_authority_claim(factor: object) -> bool:
    if type(factor) is not dict:
        return False
    for key, value in factor.items():
        if type(key) is not str:
            continue
        if key not in FACTOR_FIELDS:
            normalized_key = key.upper()
            if any(fragment in normalized_key for fragment in _AUTHORITY_KEY_FRAGMENTS):
                return True
            if type(value) is bool:
                return True
        if (
            key not in {"role", "factor_class"}
            and type(value) is str
            and value.upper() in _AUTHORITY_STRING_CLAIMS
        ):
            return True
    return False


def _factor_shape_valid(
    factor: object,
    *,
    expected_role: str,
    expected_class: str,
) -> bool:
    if (
        type(factor) is not dict
        or any(type(key) is not str for key in factor)
        or set(factor) != FACTOR_FIELDS
    ):
        return False
    if type(factor.get("factor_record_version")) is not int:
        return False
    if factor["factor_record_version"] != 1:
        return False
    if type(factor.get("role")) is not str or factor["role"] != expected_role:
        return False
    if (
        type(factor.get("factor_class")) is not str
        or factor["factor_class"] != expected_class
    ):
        return False
    if any(
        type(factor.get(field)) is not str
        or TOKEN_PATTERN.fullmatch(factor[field]) is None
        for field in TOKEN_FIELDS
    ):
        return False
    if any(
        type(factor.get(field)) is not int or factor[field] <= 0
        for field in POSITIVE_INTEGER_FIELDS
    ):
        return False
    if any(
        type(factor.get(field)) is not str
        or DIGEST_PATTERN.fullmatch(factor[field]) is None
        for field in DIGEST_FIELDS
    ):
        return False

    parsed_times = [_parse_strict_utc(factor.get(field)) for field in TIMESTAMP_FIELDS]
    if any(parsed is None for parsed in parsed_times):
        return False
    effective_from, review_due_at, expires_at = parsed_times
    if not effective_from < review_due_at < expires_at:
        return False
    return True


def pm_dec007_hybrid_binding_shape_result(
    primary: object,
    confirmation: object,
    primary_payload_bytes: object,
    confirmation_payload_bytes: object,
) -> str:
    """Validate only the §8.2 closed factor and exact opaque-byte binding shape."""
    if (
        type(primary) is not dict
        or type(confirmation) is not dict
        or not _all_dictionary_keys_are_exact_strings(primary)
        or not _all_dictionary_keys_are_exact_strings(confirmation)
    ):
        return PM_DEC007_FACTOR_SHAPE_INVALID

    if _has_caller_authority_claim(primary) or _has_caller_authority_claim(
        confirmation
    ):
        return PM_DEC007_CALLER_AUTHORITY_CLAIM

    if not _factor_shape_valid(
        primary,
        expected_role="PRIMARY_CRYPTOGRAPHIC_SIGNATURE",
        expected_class="PHYSICAL_HARDWARE_SIGNING_KEY",
    ) or not _factor_shape_valid(
        confirmation,
        expected_role="INDEPENDENT_SECOND_CONFIRMATION",
        expected_class="SEPARATE_DEVICE_CONFIRMATION",
    ):
        return PM_DEC007_FACTOR_SHAPE_INVALID

    if any(primary[field] == confirmation[field] for field in DISTINCT_FIELDS):
        return PM_DEC007_FACTORS_NOT_INDEPENDENT

    if any(
        not _strict_equal(primary[field], confirmation[field])
        for field in EQUAL_BINDING_FIELDS
    ):
        return PM_DEC007_PAYLOAD_BINDING_MISMATCH

    if (
        type(primary_payload_bytes) is not bytes
        or type(confirmation_payload_bytes) is not bytes
        or primary_payload_bytes != confirmation_payload_bytes
    ):
        return PM_DEC007_PAYLOAD_BINDING_MISMATCH

    primary_digest = hashlib.sha256(primary_payload_bytes).hexdigest()
    confirmation_digest = hashlib.sha256(confirmation_payload_bytes).hexdigest()
    if (
        primary["payload_sha256"] != primary_digest
        or confirmation["payload_sha256"] != confirmation_digest
    ):
        return PM_DEC007_PAYLOAD_BINDING_MISMATCH

    return PM_DEC007_BINDING_VALID


def pm_dec007_checkpoint_claim_result(claim: object = None) -> str:
    """Reject every caller-supplied checkpoint without inspecting it."""
    return PM_DEC007_CHECKPOINT_UNAVAILABLE


def pm_dec007_authority_readiness_result(
    *args: object,
    adapter_call: Callable[..., object] | object | None = None,
    **kwargs: object,
) -> str:
    """Remain unconditionally fail-closed; ``adapter_call`` is never invoked."""
    return PM_DEC007_RUNTIME_TRUST_INCOMPLETE


def _load_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _mentions_acceptance_id(text: str, criterion_id: str) -> bool:
    if criterion_id in text:
        return True
    target = int(criterion_id.rsplit("-", 1)[1])
    for start, end in re.findall(r"PM-AC-([0-9]{3})(?:…|\.\.\.)([0-9]{3})", text):
        if int(start) <= target <= int(end):
            return True
    return False


def _read_frozen_manifest(
    root: Path,
    relative: str,
    label: str,
) -> tuple[list[tuple[str, str]], list[str]]:
    errors: list[str] = []
    manifest = root / relative
    try:
        raw_lines = manifest.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return [], [f"{label} manifest unavailable or malformed"]

    entries: list[tuple[str, str]] = []
    for line in raw_lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        if match is None:
            errors.append(f"{label} manifest has a malformed entry")
            continue
        entries.append((match.group(2), match.group(1)))
    return entries, errors


def _check_manifest_identity(
    root: Path,
    relative: str,
    label: str,
    expected_sha256: str,
    expected_paths: tuple[str, ...],
) -> list[str]:
    entries, errors = _read_frozen_manifest(root, relative, label)
    if errors:
        return errors
    try:
        actual_manifest_sha256 = hashlib.sha256((root / relative).read_bytes()).hexdigest()
    except OSError:
        return [f"{label} manifest unavailable or malformed"]
    if actual_manifest_sha256 != expected_sha256:
        errors.append(f"{label} manifest bytes changed")
    paths = [path for path, _ in entries]
    if tuple(paths) != expected_paths or len(set(paths)) != len(expected_paths):
        errors.append(f"{label} manifest path set changed")
    return errors


def _check_active_manifest(
    root: Path,
    relative: str,
    label: str,
    expected_paths: tuple[str, ...],
    expected_sha256: str | None = None,
) -> list[str]:
    entries, errors = _read_frozen_manifest(root, relative, label)
    if errors:
        return errors
    paths = [path for path, _ in entries]
    if tuple(paths) != expected_paths or len(set(paths)) != len(expected_paths):
        errors.append(f"{label} manifest path set changed")
        return errors
    if expected_sha256 is not None:
        try:
            actual_manifest_sha256 = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        except OSError:
            return errors + [f"{label} manifest unavailable or malformed"]
        if actual_manifest_sha256 != expected_sha256:
            errors.append(f"{label} manifest bytes changed")
    for relative, expected_digest in entries:
        try:
            actual_digest = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        except OSError as exc:
            errors.append(f"{label} artifact unavailable: {relative}: {exc}")
            continue
        if actual_digest != expected_digest:
            errors.append(f"{label} artifact hash mismatch: {relative}")
    return errors


def _check_frozen_evidence_versions(root: Path) -> list[str]:
    errors = _check_manifest_identity(
        root,
        HISTORICAL_CORE_MANIFEST,
        "historical v11",
        HISTORICAL_CORE_MANIFEST_SHA256,
        FROZEN_CORE_V11_PATHS,
    )
    errors.extend(
        _check_active_manifest(
            root,
            ACTIVE_CORE_MANIFEST,
            "active v12",
            FROZEN_CORE_V12_PATHS,
            ACTIVE_CORE_MANIFEST_SHA256,
        )
    )
    errors.extend(
        _check_manifest_identity(
            root,
            HISTORICAL_PM_MANIFEST,
            "historical PM V1",
            HISTORICAL_PM_MANIFEST_SHA256,
            FROZEN_PM_DEC007_PATHS,
        )
    )
    errors.extend(
        _check_active_manifest(
            root,
            ACTIVE_PM_MANIFEST,
            "active PM V2",
            FROZEN_PM_DEC007_PATHS,
        )
    )
    return errors


def _check_traceability(root: Path) -> list[str]:
    errors: list[str] = []
    addendum = root / "specs/pm-dec-007-hybrid-trust-v1"
    try:
        spec_text = (addendum / "spec.md").read_text(encoding="utf-8")
        tasks_text = (addendum / "tasks.md").read_text(encoding="utf-8")
        acceptance = _load_toml(addendum / "acceptance.toml")
    except TOML_READ_ERRORS:
        return ["PM-DEC-007 traceability artifact unavailable or malformed"]

    for requirement in ("PM-REQ-094", "PM-REQ-095", "PM-REQ-096"):
        if requirement not in spec_text:
            errors.append(f"spec traceability is missing {requirement}")
    for criterion_id in TRACEABILITY:
        if not _mentions_acceptance_id(spec_text, criterion_id):
            errors.append(f"spec traceability is missing {criterion_id}")

    criteria = acceptance.get("criteria")
    if type(criteria) is not list:
        return errors + ["acceptance criteria must be an exact list"]
    ids = [
        criterion.get("id")
        for criterion in criteria
        if type(criterion) is dict
    ]
    if ids != list(TRACEABILITY) or len(ids) != len(criteria):
        errors.append("acceptance criteria must be exactly PM-AC-059 through PM-AC-061")
    else:
        for criterion in criteria:
            criterion_id = criterion["id"]
            if criterion.get("requirements") != list(TRACEABILITY[criterion_id]):
                errors.append(f"acceptance requirement mapping changed: {criterion_id}")
            if (
                criterion.get("implementation_status")
                != "PARTIAL_NON_AUTHORIZING_VALIDATORS"
            ):
                errors.append(
                    f"acceptance implementation status is incomplete: {criterion_id}"
                )

    task_matches = re.findall(
        r"^- \[([ x])\] `(PM7-TASK-[0-9]{3})` — (.+)$",
        tasks_text,
        flags=re.MULTILINE,
    )
    tasks = {task_id: (mark, text) for mark, task_id, text in task_matches}
    if len(tasks) != len(task_matches):
        errors.append("task IDs must be unique")
    for task_id, criteria_ids in COMPLETED_IMPLEMENTATION_TASKS.items():
        task = tasks.get(task_id)
        if task is None or task[0] != "x":
            errors.append(f"implementation task is not complete: {task_id}")
            continue
        if any(
            not _mentions_acceptance_id(task[1], criterion_id)
            for criterion_id in criteria_ids
        ):
            errors.append(f"implementation task traceability changed: {task_id}")
    for task_id in DEFERRED_TASKS:
        task = tasks.get(task_id)
        if task is None or task[0] != " ":
            errors.append(f"deferred authority task must remain incomplete: {task_id}")
    return errors


def run_checks(root: Path = ROOT) -> list[str]:
    """Run deterministic record, artifact, and traceability checks."""
    root_path = Path(root)
    errors: list[str] = []
    decision_path = (
        root_path
        / "specs/pm-dec-007-hybrid-trust-v1/decisions/PM-DEC-007.toml"
    )
    try:
        decision = _load_toml(decision_path)
    except TOML_READ_ERRORS:
        return ["PM-DEC-007 decision record unavailable or malformed"]
    errors.extend(validate_pm_dec007_record(decision, root_path))
    errors.extend(_check_traceability(root_path))
    errors.extend(_check_frozen_evidence_versions(root_path))
    return errors


def main(root: Path = ROOT) -> int:
    errors = run_checks(root)
    if errors:
        print("PM-DEC-007 HYBRID CHECK: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "PM-DEC-007 HYBRID CHECK: PASS "
        "(semantics unchanged, historical V11/PM V1, active V12/PM V2)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
