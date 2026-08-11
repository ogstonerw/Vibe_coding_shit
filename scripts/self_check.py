#!/usr/bin/env python3
"""Deterministic integrity checks for the agent factory."""

from __future__ import annotations

import json
import hashlib
import os
import re
import stat
import sys
import tomllib
import zipfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "AGENTS.md",
    "config/codex/config.toml",
    "factory/pipeline.toml",
    "governance/risk-policy.toml",
    "governance/approval-policy.toml",
    "contracts/handoff.schema.json",
    "contracts/release-report.schema.json",
    "evals/scenarios.toml",
    "specs/bitget-btc-telegram-v1/spec.md",
    "specs/bitget-btc-telegram-v1/plan.md",
    "specs/bitget-btc-telegram-v1/tasks.md",
    "specs/bitget-btc-telegram-v1/acceptance.toml",
    "specs/portfolio-mandate-v1/spec.md",
    "specs/portfolio-mandate-v1/plan.md",
    "specs/portfolio-mandate-v1/tasks.md",
    "specs/portfolio-mandate-v1/acceptance.toml",
    "specs/portfolio-mandate-v1/mandate.schema.json",
    "specs/portfolio-mandate-v1/owner-decision-manifest.schema.json",
    "specs/portfolio-mandate-v1/mandate.example.toml",
    "specs/portfolio-mandate-v1/decisions/PM-DEC-001.toml",
    "specs/portfolio-mandate-v1/decisions/PM-DEC-002.toml",
    "specs/portfolio-mandate-v1/decisions/PM-DEC-003.toml",
    "specs/portfolio-mandate-v1/decisions/PM-DEC-003-v2.toml",
    "specs/portfolio-mandate-v1/validity-profiles/validity-profile.schema.json",
    "specs/portfolio-mandate-v1/validity-profiles/bitget-pilot-draft-v1.toml",
    "specs/portfolio-mandate-v1/review.md",
    "portfolio-mandate-v0.4.zip",
    "portfolio-mandate-v0.5.zip",
    "portfolio-mandate-v0.6.zip",
]

REQUIRED_AGENTS = {
    "requirements_analyst",
    "quant_researcher",
    "system_architect",
    "game_ux_designer",
    "pro_trader_ux",
    "implementer",
    "test_engineer",
    "code_reviewer",
    "security_reviewer",
    "risk_reviewer",
    "release_verifier",
    "institutional_portfolio_reviewer",
    "quant_methodology_reviewer",
    "market_microstructure_reviewer",
}

UI_AGENT_EXPECTATIONS = {
    "game_ux_designer": {
        "model": "gpt-5.6",
        "model_reasoning_effort": "high",
        "sandbox_mode": "read-only",
    },
    "pro_trader_ux": {
        "model": "gpt-5.6",
        "model_reasoning_effort": "high",
        "sandbox_mode": "read-only",
    },
}

REQUIRED_SPEC_HEADINGS = {
    "## 1. Outcome",
    "## 2. In scope",
    "## 3. Out of scope",
    "## 6. Behavioral scenarios",
    "## 7. Risk and execution rules",
    "## 11. Acceptance criteria",
    "## 12. Open decisions",
}

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|api[_-]?secret|telegram[_-]?token)\s*[=:]\s*['\"]?(?!\$\{|<|changeme|example|your_)[A-Za-z0-9_\-/]{16,}"),
    re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b"),
]

PM_DEC002_REQUIRED_ARTIFACTS = (
    "specs/portfolio-mandate-v1/spec.md",
    "specs/portfolio-mandate-v1/acceptance.toml",
    "governance/approval-policy.toml",
    "governance/risk-policy.toml",
)

PM_DEC002_BOUND_FACTOR_FIELDS = (
    "manifest_id",
    "payload_sha256",
    "sequence",
    "scope_sha256",
    "limits_sha256",
    "expires_at",
)

PM_DEC002_REAL_CAPITAL_ACTIONS = (
    "REAL_ACCOUNT_OR_CREDENTIAL",
    "PILOT",
    "PRODUCTION",
    "REAL_SCOPE_EXPANSION",
    "HARD_LIMIT_INCREASE",
    "LEVERAGE_OR_MARGIN_CHANGE",
    "REAL_BOOK_TRANSFER",
    "DISTRIBUTION",
)

PM_DEC003_REQUIRED_ARTIFACTS = PM_DEC002_REQUIRED_ARTIFACTS

PM_NORMATIVE_CAPITAL_STAGES = (
    "DEVELOPMENT",
    "RESEARCH",
    "REPLAY",
    "DRY_RUN",
    "PAPER",
    "PILOT_LIMITED_LIVE",
    "PRODUCTION_LIVE",
)

PM_DEC003_LEVEL_A_LIFECYCLE = PM_NORMATIVE_CAPITAL_STAGES[:5]

PM_DEC003_LEVEL_B_MODES = (
    "TIME_BOXED_REAL_CAPITAL",
    "ONE_TIME_REAL_CAPITAL",
)

PM_DEC003_APPROVAL_TERMINAL_STATES = (
    "EXPIRED",
    "REVOKED",
    "SUPERSEDED",
    "INVALIDATED",
)

PM_DEC003_ACTION_TERMINAL_STATES = (
    "CONSUMED",
    "CANCELLED_NO_EFFECT",
)

PM_DEC003_INDEPENDENT_VALIDITY_OBJECTS = (
    "MANDATE",
    "OWNER_APPROVAL",
    "EVIDENCE",
    "VENUE_CAPABILITY",
    "RUNTIME_PROTECTION",
)

PM_DECISION_ARCHIVES = {
    "PM-DEC-002": "portfolio-mandate-v0.4.zip",
    "PM-DEC-003": "portfolio-mandate-v0.5.zip",
}

PM_DEC003_V1_SHA256 = "618dd1da08fb6a8f7f0631fa6824bea1cc527d071e035b20b9250bcd374789ce"
VALIDITY_DURATION_TECHNICAL_MAX_MS = 3_155_760_000_000
APPROVED_BITGET_RISK_POLICY_ID = "bitget-btc-v1"
APPROVED_BITGET_RISK_POLICY_VERSION = 1
APPROVED_BITGET_RISK_POLICY_SHA256 = (
    "4f34d45ac058bec6d5ce1ecc05dc242572a917bd6e2f6769ff53b7115f4b72e8"
)

LIQUIDITY_REGIMES = ("NORMAL", "THIN", "STRESSED", "UNRESOLVED_DENY")
VOLATILITY_REGIMES = ("NORMAL", "HIGH", "EXTREME", "UNRESOLVED_DENY")
DEGRADED_STATES = ("NORMAL", "DEGRADED_READ_ONLY", "UNRESOLVED_DENY")
HOLDOUT_ACCESS_PURPOSES = ("FINAL_FORWARD_CONFIRMATION",)
MANDATORY_SUNSET_CUTOFF_FIELDS = {
    "approval",
    "evidence",
    "capability",
    "risk_policy",
    "runtime_protection",
}

PM_DEC003_V2_EXACT_KEY_FIELDS = (
    "venue_id", "venue_environment", "market_id", "capital_stage", "approval_tier",
    "validity_mode", "action_class", "risk_class", "venue_capability_profile_id",
    "venue_capability_profile_version", "venue_capability_profile_sha256",
    "risk_policy_id", "risk_policy_version", "risk_policy_sha256",
    "calibration_stratum_id", "calibration_stratum_sha256",
    "api_or_protocol_version", "account_mode", "order_type", "time_in_force",
    "session_id", "liquidity_regime", "volatility_regime", "degraded_state",
)

CROSS_RISK_SCOPE_FIELDS = (
    "venue_id",
    "venue_environment",
    "market_id",
    "approval_tier",
    "validity_mode",
    "venue_capability_profile_id",
    "venue_capability_profile_version",
    "venue_capability_profile_sha256",
    "risk_policy_id",
    "risk_policy_version",
    "risk_policy_sha256",
    "calibration_stratum_id",
    "calibration_stratum_sha256",
    "api_or_protocol_version",
    "account_mode",
    "order_type",
    "time_in_force",
    "session_id",
    "liquidity_regime",
    "volatility_regime",
    "degraded_state",
)

OPERATING_NUMERIC_FIELDS = {
    "operating_ttl_ms", "cancel_reconciliation_buffer_ms", "dispatch_guard_ms",
    "clock_skew_tolerance_ms", "revocation_snapshot_max_age_ms", "review_lead_time_ms",
    "reconciliation_escalation_deadline_ms",
}
SINGLE_USE_NUMERIC_FIELDS = {
    "single_use_activation_window_ms", "dispatch_guard_ms", "clock_skew_tolerance_ms",
    "revocation_snapshot_max_age_ms", "reconciliation_escalation_deadline_ms",
}

NONCAPITAL_NUMERIC_FIELDS: set[str] = set()

ACTION_NUMERIC_FIELDS = {
    "OPERATING": OPERATING_NUMERIC_FIELDS,
    "SINGLE_USE": SINGLE_USE_NUMERIC_FIELDS,
    "NON_CAPITAL": NONCAPITAL_NUMERIC_FIELDS,
}

CROSS_RISK_COMPATIBILITY = {
    ("B1_LIMITED_PILOT", "B2_EXISTING_PRODUCTION"): "OPERATING",
}

ACTIVE_SCHEMA_UNAVAILABLE = "DENY_ACTIVE_SCHEMA_OR_RUNTIME_EVIDENCE_UNAVAILABLE"

VENUE_MECHANICS_MATRIX = {
    "BITGET": {
        "environments": {
            "PAPER_SIMULATOR",
            "BITGET_TESTNET",
            "BITGET_PRODUCTION",
        },
        "market_id": "BITGET_USDT_FUTURES",
        "api_or_protocol_version": "BITGET_API_V2",
        "account_modes": {"ONE_WAY_MODE"},
        "session_ids": {"BITGET_24X7"},
        "order_tif_pairs": {
            ("LIMIT", "GTC"),
            ("LIMIT", "IOC"),
            ("LIMIT", "FOK"),
            ("LIMIT", "POST_ONLY"),
        },
    },
    "MOEX": {
        "environments": {"MOEX_BROKER_TEST", "MOEX_PRODUCTION"},
        "market_id": "MOEX_UNRESOLVED_BLOCKED",
        "status": "FUTURE_BLOCKED",
    },
}


class _DuplicateJsonKey(ValueError):
    pass


def _strict_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKey(key)
        result[key] = value
    return result


def _parse_json_bytes_strict(raw: object) -> object | None:
    """Parse UTF-8 JSON while rejecting duplicate keys and non-JSON constants."""
    if not isinstance(raw, bytes):
        return None

    def reject_constant(value: str) -> object:
        raise ValueError(f"non-JSON constant: {value}")

    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_strict_json_object,
            parse_constant=reject_constant,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        _DuplicateJsonKey,
        RecursionError,
    ):
        return None


def canonical_json_bytes(value: object) -> bytes | None:
    """Return the project's strict canonical JSON or None for unsafe values."""
    def valid(item: object) -> bool:
        if item is None or isinstance(item, (str, bool)):
            return True
        if isinstance(item, int) and not isinstance(item, bool):
            return True
        if isinstance(item, float):
            return False
        if isinstance(item, list):
            return all(valid(child) for child in item)
        if isinstance(item, dict):
            return all(
                isinstance(key, str) and bool(key) and valid(child)
                for key, child in item.items()
            )
        return False

    try:
        is_valid = valid(value)
    except RecursionError:
        return None
    if not is_valid:
        return None
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError):
        return None


def canonical_json_digest(value: object) -> str | None:
    canonical = canonical_json_bytes(value)
    return hashlib.sha256(canonical).hexdigest() if canonical is not None else None


def canonical_json_bytes_result(raw: object) -> str:
    parsed = _parse_json_bytes_strict(raw)
    if parsed is None:
        return "DENY_DUPLICATE_KEY_OR_MALFORMED_JSON"
    canonical = canonical_json_bytes(parsed)
    if canonical is None:
        return "DENY_NON_CANONICAL_JSON_VALUE"
    if canonical != raw:
        return "DENY_NON_CANONICAL_JSON_BYTES"
    return "NON_AUTHORIZING_CANONICAL_JSON_SHAPE_VALID"


def _strict_positive_duration(value: object) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and 0 < value <= VALIDITY_DURATION_TECHNICAL_MAX_MS
    )


def load_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def validate_schema_subset(instance: object, schema: dict, *, root_schema: dict | None = None) -> list[str]:
    """Small dependency-free JSON-Schema subset for the non-authorizing draft.

    It deliberately implements only the vocabulary used by mandate.schema.json;
    an unsupported schema keyword is not treated as permission to accept input.
    """
    root_schema = schema if root_schema is None else root_schema

    def strict_json_equal(left: object, right: object) -> bool:
        if type(left) is not type(right):
            return False
        if isinstance(left, dict):
            return set(left) == set(right) and all(strict_json_equal(left[key], right[key]) for key in left)  # type: ignore[index]
        if isinstance(left, list):
            return len(left) == len(right) and all(strict_json_equal(a, b) for a, b in zip(left, right))  # type: ignore[arg-type]
        return left == right

    def resolve(node: dict) -> dict:
        reference = node.get("$ref")
        if not reference:
            return node
        if not isinstance(reference, str) or not reference.startswith("#/$defs/"):
            return {"not": {}}
        target: object = root_schema
        for part in reference.removeprefix("#/").split("/"):
            if not isinstance(target, dict) or part not in target:
                return {"not": {}}
            target = target[part]
        return target if isinstance(target, dict) else {"not": {}}

    def matches_type(value: object, expected: str) -> bool:
        if expected == "object":
            return isinstance(value, dict)
        if expected == "array":
            return isinstance(value, list)
        if expected == "string":
            return isinstance(value, str)
        if expected == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if expected == "boolean":
            return isinstance(value, bool)
        return False

    def walk(value: object, node: dict, path: str) -> list[str]:
        node = resolve(node)
        errors: list[str] = []
        if "const" in node and not strict_json_equal(value, node["const"]):
            errors.append(f"{path}: value must equal schema const")
        if "enum" in node and not any(strict_json_equal(value, candidate) for candidate in node["enum"]):
            errors.append(f"{path}: value is not in schema enum")
        expected_type = node.get("type")
        if isinstance(expected_type, str) and not matches_type(value, expected_type):
            return errors + [f"{path}: value has wrong schema type"]
        if isinstance(value, str):
            if len(value) < node.get("minLength", 0):
                errors.append(f"{path}: string is shorter than minLength")
            pattern = node.get("pattern")
            if isinstance(pattern, str) and re.fullmatch(pattern, value) is None:
                errors.append(f"{path}: string does not match schema pattern")
            if node.get("format") == "date-time" and _parse_strict_utc(value) is None:
                errors.append(f"{path}: date-time must be canonical RFC3339 UTC ending in Z")
        if isinstance(value, int) and not isinstance(value, bool):
            minimum = node.get("minimum")
            if isinstance(minimum, int) and value < minimum:
                errors.append(f"{path}: integer is below schema minimum")
            maximum = node.get("maximum")
            if isinstance(maximum, int) and value > maximum:
                errors.append(f"{path}: integer is above schema maximum")
        if isinstance(value, dict):
            properties = node.get("properties", {})
            required = node.get("required", [])
            if not isinstance(properties, dict) or not isinstance(required, list):
                return errors + [f"{path}: unsupported object schema"]
            for name in required:
                if name not in value:
                    errors.append(f"{path}: missing required property {name}")
            if node.get("additionalProperties") is False:
                for name in value:
                    if name not in properties:
                        errors.append(f"{path}: unknown property {name}")
            for name, child in properties.items():
                if name in value and isinstance(child, dict):
                    errors.extend(walk(value[name], child, f"{path}.{name}"))
        if isinstance(value, list):
            if len(value) < node.get("minItems", 0):
                errors.append(f"{path}: too few items")
            maximum = node.get("maxItems")
            if isinstance(maximum, int) and len(value) > maximum:
                errors.append(f"{path}: too many items")
            item_schema = node.get("items")
            if isinstance(item_schema, dict):
                for index, item in enumerate(value):
                    errors.extend(walk(item, item_schema, f"{path}[{index}]"))
            if node.get("uniqueItems") is True:
                encoded = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in value]
                if len(encoded) != len(set(encoded)):
                    errors.append(f"{path}: array items must be unique")
        return errors

    return walk(instance, schema, "$")


def read_archive_member(root: Path, archive_name: str, relative: str) -> bytes:
    with zipfile.ZipFile(root / archive_name) as archive:
        matches = [name for name in archive.namelist() if name == relative]
        if len(matches) != 1:
            raise ValueError(f"archive {archive_name} must contain exactly one {relative}")
        return archive.read(matches[0])


def _closed_release_source_members(
    root: Path,
    release_directory: Path,
) -> tuple[dict[str, bytes], list[str]]:
    """Read a closed regular-file tree without following source-side links."""
    expected: dict[str, bytes] = {}
    errors: list[str] = []
    try:
        root_lstat = root.lstat()
        resolved_root = root.resolve(strict=True)
        release_lstat = release_directory.lstat()
        resolved_release = release_directory.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        return expected, [f"release source tree unavailable or invalid: {exc}"]
    if (
        stat.S_ISLNK(root_lstat.st_mode)
        or not stat.S_ISDIR(root_lstat.st_mode)
        or stat.S_ISLNK(release_lstat.st_mode)
        or not stat.S_ISDIR(release_lstat.st_mode)
        or (
            resolved_release != resolved_root
            and resolved_root not in resolved_release.parents
        )
    ):
        return expected, ["release source directory is linked, non-directory, or escaping root"]

    try:
        relative_release = release_directory.relative_to(root)
    except ValueError:
        return expected, ["release source directory is outside lexical root"]
    ancestor = root
    for part in relative_release.parts:
        ancestor = ancestor / part
        try:
            ancestor_mode = ancestor.lstat().st_mode
        except OSError as exc:
            errors.append(f"release source ancestor unavailable: {ancestor}: {exc}")
            return expected, errors
        if stat.S_ISLNK(ancestor_mode):
            errors.append(f"release source has symlink ancestor: {ancestor}")
            return expected, errors

    pending = [release_directory]
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as iterator:
                entries = sorted(iterator, key=lambda entry: entry.name)
        except OSError as exc:
            errors.append(f"release source directory unreadable: {directory}: {exc}")
            continue
        for entry in entries:
            candidate = Path(entry.path)
            try:
                candidate_lstat = candidate.lstat()
            except OSError as exc:
                errors.append(f"release source member unavailable: {candidate}: {exc}")
                continue
            mode = candidate_lstat.st_mode
            if stat.S_ISLNK(mode):
                errors.append(f"release source contains symlink member: {candidate}")
                continue
            if stat.S_ISDIR(mode):
                pending.append(candidate)
                continue
            if not stat.S_ISREG(mode):
                errors.append(f"release source contains non-regular member: {candidate}")
                continue
            try:
                resolved_candidate = candidate.resolve(strict=True)
            except (OSError, RuntimeError) as exc:
                errors.append(f"release source member cannot be resolved: {candidate}: {exc}")
                continue
            if (
                resolved_candidate != resolved_release
                and resolved_release not in resolved_candidate.parents
            ):
                errors.append(f"release source member escapes release directory: {candidate}")
                continue
            try:
                relative = candidate.relative_to(root).as_posix()
                expected[relative] = candidate.read_bytes()
            except (OSError, ValueError) as exc:
                errors.append(f"release source member unreadable: {candidate}: {exc}")
    return expected, errors


def validate_release_snapshot_members(root: Path, archive_name: str, release_directory: Path) -> list[str]:
    """Byte-compare a non-authoritative snapshot against one closed directory tree."""
    expected, errors = _closed_release_source_members(root, release_directory)
    try:
        with zipfile.ZipFile(root / archive_name) as archive:
            all_infos = archive.infolist()
            infos = [info for info in all_infos if not info.is_dir()]
            names = [info.filename for info in infos]
            all_names = [info.filename for info in all_infos]
            if len(all_names) != len(set(all_names)):
                errors.append(f"{archive_name} contains duplicate file members")
            normalized_names: list[str] = []
            for info in all_infos:
                name = info.filename
                pure = PurePosixPath(name)
                parts = pure.parts
                normalized = pure.as_posix()
                normalized_names.append(normalized)
                canonical_member_name = (
                    normalized + "/" if info.is_dir() else normalized
                )
                windows_drive = re.match(r"^[A-Za-z]:", name) is not None
                if (
                    not name
                    or "\x00" in name
                    or name.startswith(("/", "\\"))
                    or windows_drive
                    or ".." in parts
                    or "." in parts
                    or "\\" in name
                    or canonical_member_name != name
                ):
                    errors.append(f"{archive_name} contains unsafe member path: {name}")
                unix_mode = (info.external_attr >> 16) & 0xFFFF
                file_type = stat.S_IFMT(unix_mode)
                allowed_types = (
                    {0, stat.S_IFDIR} if info.is_dir() else {0, stat.S_IFREG}
                )
                if file_type not in allowed_types:
                    errors.append(f"{archive_name} contains symlink or special member: {name}")
            if len(normalized_names) != len(set(normalized_names)):
                errors.append(f"{archive_name} contains duplicate normalized member paths")
            if set(names) != set(expected):
                errors.append(f"{archive_name} member manifest differs from closed release directory")
            for name in set(names) & set(expected):
                if archive.read(name) != expected[name]:
                    errors.append(f"{archive_name} member differs from working tree: {name}")
    except (OSError, zipfile.BadZipFile) as exc:
        errors.append(f"{archive_name} unavailable or invalid: {exc}")
    return errors


def load_snapshot_decision(root: Path, decision_id: str) -> dict:
    archive_name = PM_DECISION_ARCHIVES[decision_id]
    relative = f"specs/portfolio-mandate-v1/decisions/{decision_id}.toml"
    return tomllib.loads(read_archive_member(root, archive_name, relative).decode("utf-8"))


def validate_snapshot_consistency(
    record: dict,
    *,
    root: Path,
    decision_id: str,
    required_artifacts: tuple[str, ...],
) -> list[str]:
    """Check a non-authoritative release snapshot for internal consistency.

    ZIP snapshots are not a trust root and do not prove owner ratification.
    """
    errors: list[str] = []
    archive_name = PM_DECISION_ARCHIVES[decision_id]
    try:
        baseline = load_snapshot_decision(root, decision_id)
    except (OSError, ValueError, zipfile.BadZipFile, tomllib.TOMLDecodeError) as exc:
        return [f"{decision_id} consistency snapshot is unavailable: {exc}"]
    if record != baseline:
        errors.append(f"{decision_id} v1 differs from non-authoritative {archive_name} snapshot")

    entries = record.get("artifact_hashes", [])
    paths = [item.get("path") for item in entries]
    artifact_map = {item.get("path"): item.get("sha256") for item in entries}
    if (
        len(entries) != len(required_artifacts)
        or len(artifact_map) != len(entries)
        or set(paths) != set(required_artifacts)
    ):
        errors.append(f"{decision_id} artifact hash set must be exact and duplicate-free")
        return errors

    baseline_map = {
        item.get("path"): item.get("sha256")
        for item in baseline.get("artifact_hashes", [])
    }
    for relative in required_artifacts:
        if relative.startswith("specs/portfolio-mandate-v1/"):
            try:
                snapshot_bytes = read_archive_member(root, archive_name, relative)
            except (OSError, ValueError, zipfile.BadZipFile) as exc:
                errors.append(f"{decision_id} snapshot artifact is unavailable: {relative}: {exc}")
                continue
            expected_hash = hashlib.sha256(snapshot_bytes).hexdigest()
        else:
            expected_hash = baseline_map.get(relative)
        if artifact_map.get(relative) != expected_hash:
            errors.append(f"{decision_id} snapshot artifact hash mismatch: {relative}")
    return errors


def pm_dec002_payload_digest(record: dict) -> str:
    """Hash the complete decision record except its self-referential integrity table."""
    payload = {key: value for key, value in record.items() if key != "integrity"}
    return canonical_json_digest(payload) or ""


def pm_dec003_payload_digest(record: dict) -> str:
    """Hash the complete partial decision except its self-referential integrity table."""
    payload = {key: value for key, value in record.items() if key != "integrity"}
    return canonical_json_digest(payload) or ""


def validate_level_b_factor_binding(
    signature_factor: dict,
    second_factor: dict,
    *,
    now_utc: datetime,
    last_accepted_sequence: int,
    max_ttl_seconds: int,
    signature_valid: bool = True,
    second_factor_valid: bool = True,
    expired: bool = False,
    revoked: bool = False,
) -> list[str]:
    """Validate a factor-pair fixture; this never grants real-capital authority."""
    errors: list[str] = []
    if not signature_valid or not second_factor_valid or expired or revoked:
        errors.append("factor validity, expiry, or revocation state is not acceptable")
    if now_utc.tzinfo is None or now_utc.utcoffset() is None:
        errors.append("now_utc must be timezone-aware")
    if isinstance(last_accepted_sequence, bool) or not isinstance(last_accepted_sequence, int):
        errors.append("last accepted sequence must be an integer")
    if isinstance(max_ttl_seconds, bool) or not isinstance(max_ttl_seconds, int) or max_ttl_seconds <= 0:
        errors.append("maximum TTL must be a positive integer")

    for factor_name, factor in (
        ("signature", signature_factor),
        ("second", second_factor),
    ):
        for field in PM_DEC002_BOUND_FACTOR_FIELDS:
            if field not in factor or factor[field] in (None, ""):
                errors.append(f"{factor_name} factor is missing required field {field}")
        if not isinstance(factor.get("manifest_id"), str) or not factor.get("manifest_id", "").strip():
            errors.append(f"{factor_name} factor manifest_id must be a non-empty string")
        for field in ("payload_sha256", "scope_sha256", "limits_sha256"):
            value = factor.get(field)
            if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                errors.append(f"{factor_name} factor {field} must be lowercase SHA-256")
        sequence = factor.get("sequence")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence <= 0:
            errors.append(f"{factor_name} factor sequence must be a positive integer")
        for field in ("trust_root_id", "failure_domain_id"):
            if not isinstance(factor.get(field), str) or not factor.get(field, "").strip():
                errors.append(f"{factor_name} factor {field} must be a non-empty string")

    for field in PM_DEC002_BOUND_FACTOR_FIELDS:
        if signature_factor.get(field) != second_factor.get(field):
            errors.append(f"factor mismatch: {field}")

    sequence = signature_factor.get("sequence")
    if (
        isinstance(sequence, int)
        and not isinstance(sequence, bool)
        and isinstance(last_accepted_sequence, int)
        and not isinstance(last_accepted_sequence, bool)
        and sequence <= last_accepted_sequence
    ):
        errors.append("sequence is replayed or non-monotonic")

    expires_at = signature_factor.get("expires_at")
    expiry: datetime | None = None
    if isinstance(expires_at, str) and expires_at.endswith("Z"):
        try:
            expiry = datetime.fromisoformat(expires_at[:-1] + "+00:00")
        except ValueError:
            pass
    if expiry is None:
        errors.append("expires_at must be a parseable UTC timestamp ending in Z")
    elif now_utc.tzinfo is not None and now_utc.utcoffset() is not None:
        normalized_now = now_utc.astimezone(timezone.utc)
        if expiry <= normalized_now:
            errors.append("factor pair is expired")
        elif isinstance(max_ttl_seconds, int) and not isinstance(max_ttl_seconds, bool):
            if expiry > normalized_now + timedelta(seconds=max_ttl_seconds):
                errors.append("factor pair exceeds the policy TTL bound")

    if (
        signature_factor.get("trust_root_id") == second_factor.get("trust_root_id")
        or signature_factor.get("failure_domain_id") == second_factor.get("failure_domain_id")
    ):
        errors.append("factors do not have independent trust roots and failure domains")
    return errors


def level_b_factor_binding_result(*args: object, **kwargs: object) -> str:
    """PM-DEC-007 is unresolved, so even a well-formed pair remains DENY."""
    validate_level_b_factor_binding(*args, **kwargs)
    return "DENY"


def validate_pm_dec002_record(record: dict, root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    expected_lifecycle = ["DEVELOPMENT", "RESEARCH", "REPLAY", "DRY_RUN", "PAPER"]
    level_a = record.get("level_a_non_capital", {})
    level_b = record.get("level_b_real_capital", {})
    safety = record.get("safety", {})

    if (
        record.get("decision_id") != "PM-DEC-002"
        or record.get("selected_option") != 3
        or record.get("decision_type") != "TWO_TIER_OWNER_APPROVAL_MODEL"
        or level_a.get("applies_to") != expected_lifecycle
        or level_a.get("approval_record") != "VERSIONED_OWNER_DECISION_RECORD"
        or level_a.get("authorization_effect") != "DENY_REAL_ORDERS"
        or level_a.get("real_capital_authority") is not False
        or level_a.get("may_ratify_results_post_hoc") is not False
        or level_a.get("may_override_preregistration_holdout_or_drift") is not False
        or level_a.get("may_promote_stage_by_itself") is not False
        or level_b.get("required_factors")
        != ["CRYPTOGRAPHIC_SIGNATURE", "INDEPENDENT_SECOND_CONFIRMATION"]
        or level_b.get("applies_to") != list(PM_DEC002_REAL_CAPITAL_ACTIONS)
        or level_b.get("same_canonical_payload_required") is not True
        or level_b.get("payload_hash_binding_required") is not True
        or level_b.get("monotonic_sequence_required") is not True
        or level_b.get("expiry_and_revocation_required") is not True
        or level_b.get("independent_trust_root_required") is not True
        or level_b.get("independent_failure_domain_required") is not True
        or level_b.get("same_key_session_or_process_counts_as_independent") is not False
        or level_b.get("eligible_for_authorization") is not False
        or level_b.get("blocked_until_decision") != "PM-DEC-007"
        or safety.get("one_factor_only_result") != "DENY"
        or safety.get("mismatched_payload_result") != "DENY"
        or safety.get("expired_or_revoked_result") != "DENY"
        or safety.get("level_a_promotion_result") != "DENY"
        or safety.get("post_hoc_evidence_ratification_result") != "DENY"
        or safety.get("preregistration_holdout_or_drift_override_result") != "DENY"
        or safety.get("approval_only_stage_promotion_result") != "DENY"
        or safety.get("live_trading_enabled") is not False
        or safety.get("changes_governance_risk_policy") is not False
        or safety.get("ratified_real_capital_manifest") is not False
    ):
        errors.append("PM-DEC-002 must enforce all fail-closed two-tier approval invariants")

    # v0.4 is only a non-authoritative consistency snapshot. It prevents
    # accidental rebinding but cannot prove owner identity or ratification.
    errors.extend(
        validate_snapshot_consistency(
            record,
            root=root,
            decision_id="PM-DEC-002",
            required_artifacts=PM_DEC002_REQUIRED_ARTIFACTS,
        )
    )

    integrity = record.get("integrity", {})
    if integrity.get("canonicalization") != "SORTED_KEYS_COMPACT_UTF8_JSON_V1":
        errors.append("PM-DEC-002 canonicalization contract is missing or changed")
    if integrity.get("decision_payload_sha256") != pm_dec002_payload_digest(record):
        errors.append("PM-DEC-002 canonical decision payload hash mismatch")
    return errors


def _parse_strict_utc(value: object) -> datetime | None:
    if (
        not isinstance(value, str)
        or re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z",
            value,
        )
        is None
    ):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    if parsed.utcoffset() != timedelta(0):
        return None
    return parsed


def evaluate_pm_dec003_temporal_validity(
    approval: dict,
    *,
    evaluation_time: datetime,
    trusted_clock: bool = True,
    numeric_profile_ratified: bool = False,
) -> str:
    """Evaluate concept-state boundaries without granting real-capital authority."""
    if (
        not isinstance(approval, dict)
        or isinstance(trusted_clock, bool) is False
        or isinstance(numeric_profile_ratified, bool) is False
        or trusted_clock is not True
        or type(evaluation_time) is not datetime
        or evaluation_time.tzinfo is None
        or evaluation_time.utcoffset() != timedelta(0)
    ):
        return "DENY_UNTRUSTED_CLOCK"

    tier = approval.get("approval_tier")
    mode = approval.get("validity_mode")
    if tier == "LEVEL_A":
        if mode != "LONG_LIVED_NON_CAPITAL":
            return "DENY_INCOMPATIBLE_VALIDITY_MODE"
    elif tier == "LEVEL_B":
        if mode not in PM_DEC003_LEVEL_B_MODES:
            return "DENY_INCOMPATIBLE_VALIDITY_MODE"
    else:
        return "DENY_UNKNOWN_APPROVAL_TIER"

    state = approval.get("state")
    known_approval_states = {
        "DRAFT",
        "PENDING_EFFECTIVE",
        "ACTIVE",
        "REVIEW_REQUIRED",
        "SUSPENDED",
        *PM_DEC003_APPROVAL_TERMINAL_STATES,
    }
    if state not in known_approval_states:
        return "DENY_UNKNOWN_STATE"
    if state in PM_DEC003_APPROVAL_TERMINAL_STATES:
        return "DENY_TERMINAL_STATE"
    if state not in {"ACTIVE", "REVIEW_REQUIRED"}:
        return "DENY_INACTIVE_STATE"

    issued = _parse_strict_utc(approval.get("issued_at"))
    effective = _parse_strict_utc(approval.get("effective_from"))
    review_due = _parse_strict_utc(approval.get("review_due_at"))
    expires = _parse_strict_utc(approval.get("expires_at"))
    if (
        issued is None
        or effective is None
        or review_due is None
        or expires is None
        or not (issued <= effective <= review_due < expires)
    ):
        return "DENY_MALFORMED_TEMPORAL_ORDER"

    now = evaluation_time
    if now < effective:
        return "DENY_NOT_YET_EFFECTIVE"
    if now >= expires:
        return "DENY_EXPIRED"
    if now >= review_due or state == "REVIEW_REQUIRED":
        if tier == "LEVEL_A":
            return "NON_CAPITAL_REVIEW_REQUIRED"
        return "DENY_REVIEW_DUE"
    if tier == "LEVEL_B":
        if not numeric_profile_ratified:
            return "DENY_NUMERIC_PROFILE_UNRATIFIED"
        return "NON_AUTHORIZING_LEVEL_B_WINDOW_VALID"
    return "NON_CAPITAL_ACTIVE"


def pm_dec003_independent_validity_result(validity: dict[str, bool]) -> str:
    """Apply the most-restrictive intersection; success remains non-authorizing."""
    if not isinstance(validity, dict):
        return "DENY_MISSING_OR_UNKNOWN_VALIDITY_OBJECT"
    if set(validity) != set(PM_DEC003_INDEPENDENT_VALIDITY_OBJECTS):
        return "DENY_MISSING_OR_UNKNOWN_VALIDITY_OBJECT"
    if any(not isinstance(value, bool) for value in validity.values()):
        return "DENY_MALFORMED_VALIDITY_STATE"
    if not all(validity.values()):
        return "DENY_MOST_RESTRICTIVE_INTERSECTION"
    return "NON_AUTHORIZING_ALL_VALID"


PM_DEC003_EXPOSURE_BINDINGS = (
    "metric_id",
    "unit",
    "currency",
    "valuation_timestamp",
    "horizon",
    "netting_set",
    "convention",
)


def _parse_canonical_decimal(value: object) -> Decimal | None:
    """Parse a fixed-point decimal string; binary floats and booleans are invalid."""
    if not isinstance(value, str) or re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value) is None:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def pm_dec003_protective_exposure_result(pre: object, post: object) -> str:
    """Check proof shape only; success is explicitly non-authorizing."""
    if not isinstance(pre, dict) or not isinstance(post, dict):
        return "DENY_INCOMPARABLE_EXPOSURE_PROOF"
    for field in PM_DEC003_EXPOSURE_BINDINGS:
        if (
            not isinstance(pre.get(field), str)
            or not pre.get(field, "").strip()
            or pre.get(field) != post.get(field)
        ):
            return "DENY_INCOMPARABLE_EXPOSURE_PROOF"
    if _parse_strict_utc(pre.get("valuation_timestamp")) is None:
        return "DENY_INCOMPARABLE_EXPOSURE_PROOF"

    kind = pre.get("kind")
    if kind != post.get("kind"):
        return "DENY_INCOMPARABLE_EXPOSURE_PROOF"
    if kind == "SIGNED_NET":
        before = _parse_canonical_decimal(pre.get("value"))
        after = _parse_canonical_decimal(post.get("value"))
        if before is None or after is None:
            return "DENY_INCOMPARABLE_EXPOSURE_PROOF"
        if (before < 0 < after) or (before > 0 > after):
            return "DENY_SIGN_CROSSING"
        if abs(after) > abs(before):
            return "DENY_EXPOSURE_INCREASE"
        return "NON_AUTHORIZING_PROTECTIVE_SHAPE_VALID"

    if kind in {"ABSOLUTE", "GROSS", "CONTINGENT", "MARGIN"}:
        before = _parse_canonical_decimal(pre.get("value"))
        after = _parse_canonical_decimal(post.get("value"))
        if before is None or after is None or before < 0 or after < 0:
            return "DENY_INCOMPARABLE_EXPOSURE_PROOF"
        if after > before:
            return "DENY_EXPOSURE_INCREASE"
        return "NON_AUTHORIZING_PROTECTIVE_SHAPE_VALID"

    if kind == "STRESS_VECTOR":
        scenario_hash = pre.get("scenario_set_sha256")
        before_values = pre.get("scenario_values")
        after_values = post.get("scenario_values")
        if (
            not isinstance(scenario_hash, str)
            or re.fullmatch(r"[0-9a-f]{64}", scenario_hash) is None
            or post.get("scenario_set_sha256") != scenario_hash
            or not isinstance(before_values, dict)
            or not isinstance(after_values, dict)
            or not before_values
            or set(before_values) != set(after_values)
        ):
            return "DENY_MISSING_OR_INCOMPARABLE_SCENARIO"
        component_increase = False
        for scenario_id in before_values:
            if not isinstance(scenario_id, str) or not scenario_id.strip():
                return "DENY_MISSING_OR_INCOMPARABLE_SCENARIO"
            before = _parse_canonical_decimal(before_values[scenario_id])
            after = _parse_canonical_decimal(after_values[scenario_id])
            if before is None or after is None or before < 0 or after < 0:
                return "DENY_MISSING_OR_INCOMPARABLE_SCENARIO"
            component_increase = component_increase or after > before
        if not component_increase:
            return "NON_AUTHORIZING_PROTECTIVE_SHAPE_VALID"

        functional_id = pre.get("owner_approved_conservative_functional_id")
        before_functional = _parse_canonical_decimal(pre.get("functional_value"))
        after_functional = _parse_canonical_decimal(post.get("functional_value"))
        if (
            not isinstance(functional_id, str)
            or not functional_id.strip()
            or post.get("owner_approved_conservative_functional_id") != functional_id
            or before_functional is None
            or after_functional is None
            or before_functional < 0
            or after_functional < 0
            or after_functional > before_functional
        ):
            return "DENY_STRESS_EXPOSURE_INCREASE"
        return "NON_AUTHORIZING_PROTECTIVE_SHAPE_VALID"
    return "DENY_UNKNOWN_EXPOSURE_DIMENSION"


def pm_dec003_working_order_sunset_result(order: object) -> str:
    """Legacy bounded-order check; it cannot establish strict reconciliation."""
    if not isinstance(order, dict):
        return "DENY_MALFORMED_WORKING_ORDER_STATE"
    boolean_fields = (
        "venue_enforced_expiry",
        "expiry_not_after_cancel_deadline",
        "deadline_reached",
        "revoked",
        "venue_state_reconciled",
        "protective_path_verified",
    )
    if any(not isinstance(order.get(field), bool) for field in boolean_fields):
        return "DENY_MALFORMED_WORKING_ORDER_STATE"
    remaining = order.get("remaining_opening_or_conditional_orders")
    if isinstance(remaining, bool) or not isinstance(remaining, int) or remaining < 0:
        return "DENY_MALFORMED_WORKING_ORDER_STATE"
    if order.get("risk_effect") == "PROTECTIVE_REDUCE_ONLY":
        if order.get("protective_path_verified") is True:
            return "NON_AUTHORIZING_VERIFIED_PROTECTIVE_PATH"
        return "DENY_UNVERIFIED_PROTECTIVE_PATH"
    if order.get("risk_effect") != "NEW_OR_INCREASING_RISK":
        return "DENY_MALFORMED_WORKING_ORDER_STATE"
    if order.get("order_type") not in {"RESTING", "OPEN", "CONDITIONAL"}:
        return "DENY_MALFORMED_WORKING_ORDER_STATE"
    if (
        order.get("time_in_force") == "GTC"
        or order.get("venue_enforced_expiry") is not True
        or order.get("expiry_not_after_cancel_deadline") is not True
    ):
        return "DENY_UNBOUNDED_WORKING_ORDER"
    if order.get("deadline_reached") is True or order.get("revoked") is True:
        # This legacy shape has no terminal ledger, fill/trade watermark,
        # position/balance/child-order reconciliation, or reservation proof.
        return "RECONCILIATION_REQUIRED_NO_ZERO_EFFECT_PROMISE"
    return "NON_AUTHORIZING_BOUNDED_WORKING_ORDER_SHAPE_VALID"


def validate_pm_dec003_record(record: dict, root: Path = ROOT) -> list[str]:
    """Validate the owner-selected model while numerical authority remains unresolved."""
    errors: list[str] = []

    if not isinstance(record, dict):
        return ["PM-DEC-003 record must be a TOML object"]
    expected_top_level = {
        "decision_id",
        "decision_version",
        "status",
        "selected_option",
        "decided_by_ref",
        "decision_evidence_ref",
        "recorded_at",
        "decision_type",
        "numeric_validity_profile_status",
        "eligible_for_real_capital_authorization",
        "live_trading_enabled",
        "baseline_snapshot_archive",
        "baseline_snapshot_authoritative",
        "baseline_snapshot_trust_anchor_status",
        "artifact_ratification_eligible",
        "artifact_hashes",
        "level_a_non_capital",
        "level_b_real_capital",
        "temporal_contract",
        "trusted_clock",
        "approval_lifecycle",
        "action_lifecycle",
        "single_use",
        "configuration_mutation",
        "reconciliation",
        "working_order_sunset",
        "automatic_invalidation",
        "revocation",
        "supersession",
        "open_exposure",
        "independent_validity",
        "pending_owner_values",
        "safety",
        "integrity",
    }
    if set(record) != expected_top_level:
        errors.append("PM-DEC-003 top-level contract must be exact and closed")

    if (
        record.get("decision_id") != "PM-DEC-003"
        or record.get("decision_version") != 1
        or record.get("status") != "PARTIALLY_RESOLVED_NUMERIC_PROFILE_PENDING"
        or record.get("selected_option") != 3
        or record.get("decided_by_ref") != "OWNER"
        or record.get("decision_type") != "DIFFERENTIATED_VALIDITY_MODEL"
        or record.get("numeric_validity_profile_status") != "OWNER_INPUT_REQUIRED"
        or record.get("eligible_for_real_capital_authorization") is not False
        or record.get("live_trading_enabled") is not False
        or record.get("baseline_snapshot_archive") != "portfolio-mandate-v0.5.zip"
        or record.get("baseline_snapshot_authoritative") is not False
        or record.get("baseline_snapshot_trust_anchor_status") != "PENDING_PM-DEC-007"
        or record.get("artifact_ratification_eligible") is not False
        or not isinstance(record.get("decision_evidence_ref"), str)
        or not record.get("decision_evidence_ref", "").strip()
        or _parse_strict_utc(record.get("recorded_at")) is None
    ):
        errors.append("PM-DEC-003 identity and non-authorizing status must remain fail-closed")

    expected_level_a = {
        "validity_mode": "LONG_LIVED_NON_CAPITAL",
        "applies_to": list(PM_DEC003_LEVEL_A_LIFECYCLE),
        "exact_version_hash_scope_binding_required": True,
        "calendar_review_interval": "OWNER_INPUT_REQUIRED",
        "real_capital_authority": False,
        "automatic_renewal_allowed": False,
        "review_refreshes_evidence_or_holdout": False,
    }
    expected_level_b = {
        "allowed_validity_modes": list(PM_DEC003_LEVEL_B_MODES),
        "numeric_ttl_profile": "OWNER_INPUT_REQUIRED",
        "automatic_or_retroactive_renewal_allowed": False,
        "commit_time_recheck_required": True,
        "algorithmic_orders_inside_active_scope_require_new_owner_signature": False,
        "algorithmic_orders_still_require_all_runtime_gates": True,
        "eligible_for_authorization": False,
        "time_boxed_scope_types": ["PILOT_OPERATING_SCOPE", "PRODUCTION_OPERATING_SCOPE"],
        "cash_single_use_action_types": ["REAL_BOOK_TRANSFER", "DISTRIBUTION"],
        "configuration_single_use_action_types": [
            "REAL_ACCOUNT_OR_CREDENTIAL_CHANGE",
            "REAL_SCOPE_EXPANSION",
            "HARD_LIMIT_INCREASE",
            "LEVERAGE_OR_MARGIN_CHANGE",
        ],
    }
    if record.get("level_a_non_capital") != expected_level_a:
        errors.append("PM-DEC-003 Level-A validity contract changed or is incomplete")
    if record.get("level_b_real_capital") != expected_level_b:
        errors.append("PM-DEC-003 Level-B validity contract changed or is incomplete")

    expected_temporal = {
        "timezone": "UTC",
        "valid_interval": "effective_from <= evaluation_time < expires_at",
        "review_due_boundary_result_level_a": "REVIEW_REQUIRED_NO_NEW_BASELINE_OR_EVIDENCE_ADMISSION",
        "review_due_boundary_result_level_b": "DENY_NEW_OR_INCREASE_RISK",
        "expiry_boundary_result": "EXPIRED_DENY",
        "untrusted_or_unavailable_clock_result": "DENY",
        "timestamp_ordering_required": "issued_at <= effective_from <= review_due_at < expires_at",
    }
    expected_trusted_clock = {
        "required_sources": ["UTC_WALL_CLOCK", "MONOTONIC_ELAPSED_CLOCK", "PERSISTENT_LAST_SEEN_CHECKPOINT"],
        "wall_clock_rollback_result": "DENY",
        "boot_or_reboot_ambiguity_result": "DENY",
        "missing_or_conflicting_checkpoint_result": "DENY",
        "excessive_skew_result": "DENY",
        "skew_tolerance": "OWNER_INPUT_REQUIRED",
    }
    expected_approval_lifecycle = {
        "states": [
            "DRAFT",
            "PENDING_EFFECTIVE",
            "ACTIVE",
            "REVIEW_REQUIRED",
            "SUSPENDED",
            *PM_DEC003_APPROVAL_TERMINAL_STATES,
        ],
        "allowed_transitions": [
            "DRAFT->PENDING_EFFECTIVE", "DRAFT->SUSPENDED", "DRAFT->REVOKED", "DRAFT->INVALIDATED",
            "PENDING_EFFECTIVE->ACTIVE", "PENDING_EFFECTIVE->SUSPENDED", "PENDING_EFFECTIVE->EXPIRED", "PENDING_EFFECTIVE->REVOKED", "PENDING_EFFECTIVE->SUPERSEDED", "PENDING_EFFECTIVE->INVALIDATED",
            "ACTIVE->REVIEW_REQUIRED", "ACTIVE->SUSPENDED", "ACTIVE->EXPIRED", "ACTIVE->REVOKED", "ACTIVE->SUPERSEDED", "ACTIVE->INVALIDATED",
            "REVIEW_REQUIRED->SUSPENDED", "REVIEW_REQUIRED->EXPIRED", "REVIEW_REQUIRED->REVOKED", "REVIEW_REQUIRED->SUPERSEDED", "REVIEW_REQUIRED->INVALIDATED",
            "SUSPENDED->EXPIRED", "SUSPENDED->REVOKED", "SUSPENDED->SUPERSEDED", "SUSPENDED->INVALIDATED",
        ],
        "terminal_states": list(PM_DEC003_APPROVAL_TERMINAL_STATES),
        "unknown_or_conflicting_state_result": "DENY",
        "unlisted_transition_result": "DENY",
        "action_state_in_approval_lifecycle_result": "DENY",
        "terminal_reactivation_allowed": False,
    }
    expected_action_lifecycle = {
        "states": ["PENDING", "RESERVED", "DISPATCH_CLAIMED", "IN_FLIGHT", "RECONCILIATION_REQUIRED", "CONSUMED", "CANCELLED_NO_EFFECT", "BLOCKED_NO_NEW_RISK"],
        "allowed_transitions": ["PENDING->RESERVED", "PENDING->BLOCKED_NO_NEW_RISK", "RESERVED->DISPATCH_CLAIMED", "RESERVED->CANCELLED_NO_EFFECT", "RESERVED->BLOCKED_NO_NEW_RISK", "DISPATCH_CLAIMED->IN_FLIGHT", "DISPATCH_CLAIMED->RECONCILIATION_REQUIRED", "IN_FLIGHT->CONSUMED", "IN_FLIGHT->CANCELLED_NO_EFFECT", "IN_FLIGHT->RECONCILIATION_REQUIRED", "RECONCILIATION_REQUIRED->CONSUMED", "RECONCILIATION_REQUIRED->CANCELLED_NO_EFFECT"],
        "terminal_states": list(PM_DEC003_ACTION_TERMINAL_STATES),
        "unknown_or_conflicting_state_result": "DENY",
        "unlisted_transition_result": "DENY",
        "approval_state_in_action_lifecycle_result": "DENY",
        "reconciliation_may_remain_without_transition": True,
    }
    if record.get("temporal_contract") != expected_temporal:
        errors.append("PM-DEC-003 temporal contract changed or is incomplete")
    if record.get("trusted_clock") != expected_trusted_clock:
        errors.append("PM-DEC-003 trusted-clock contract changed or is incomplete")
    if record.get("approval_lifecycle") != expected_approval_lifecycle:
        errors.append("PM-DEC-003 approval lifecycle changed or is incomplete")
    if record.get("action_lifecycle") != expected_action_lifecycle:
        errors.append("PM-DEC-003 action lifecycle changed or is incomplete")

    expected_single_use = {
        "required_bindings": [
            "action_id",
            "canonical_action_payload_sha256",
            "idempotency_key_ref",
            "account_ref",
            "capital_book",
            "typed_amount_or_limits",
            "expires_at",
            "approval_version_sequence",
            "revocation_version_epoch",
            "reservation_generation",
            "fencing_token",
        ],
        "durable_atomic_reservation_required": True,
        "reservation_generation_strictly_monotonic": True,
        "dispatch_linearization_state": "DISPATCH_CLAIMED",
        "claim_transaction_bindings": ["REVOCATION_VERSION_EPOCH", "APPROVAL_VERSION_SEQUENCE", "RESERVATION_GENERATION", "FENCING_TOKEN", "TRANSACTIONAL_OUTBOX_DISPATCH_CLAIM"],
        "durable_transaction_or_cas_required": True,
        "stale_fencing_token_result": "DENY",
        "revocation_before_claim_result": "NO_ADAPTER_CALL_BLOCKED_NO_NEW_RISK",
        "unknown_after_claim_state": "RECONCILIATION_REQUIRED",
        "zero_external_side_effect_promised_after_claim": False,
        "safe_release_requires_durable_no_dispatch_proof": True,
        "successful_commit_state": "CONSUMED",
        "duplicate_success_result": "RETURN_STORED_OUTCOME_NO_NEW_SIDE_EFFECT",
        "unknown_or_lost_ack_state": "RECONCILIATION_REQUIRED",
        "allowed_reconciliation_outcomes": [
            "CONSUMED",
            "CANCELLED_NO_EFFECT",
            "RECONCILIATION_REQUIRED",
        ],
        "blind_retry_allowed": False,
    }
    if record.get("single_use") != expected_single_use:
        errors.append("PM-DEC-003 single-use contract changed or is incomplete")

    expected_configuration_mutation = {
        "consumed_action_types": ["REAL_ACCOUNT_OR_CREDENTIAL_CHANGE", "REAL_SCOPE_EXPANSION", "HARD_LIMIT_INCREASE", "LEVERAGE_OR_MARGIN_CHANGE"],
        "resulting_configuration_states": ["PENDING_OPERATING_AUTHORIZATION", "BLOCKED_NO_NEW_RISK"],
        "new_configuration_hash_and_version_required": True,
        "inherits_old_operating_approval": False,
        "separate_time_boxed_operating_manifest_required": True,
        "new_manifest_bound_to_new_configuration_hash_required": True,
        "orders_before_new_manifest_result": "DENY",
    }
    expected_reconciliation = {
        "default_allowed_operations": ["READ", "CANCEL_ATTEMPT", "LEDGER_AUDIT_REPAIR"],
        "trading_side_effect_default": "DENY",
        "protective_trade_requirements": [
            "PREAPPROVED_PROTECTIVE_POLICY",
            "TYPED_PRE_AND_POST_EXPOSURE_PROOF",
            "DIMENSION_SPECIFIC_NON_INCREASE_COMPARISON",
            "NO_SIGN_FLIP",
            "VENUE_CAPABILITY_CONFIRMED",
        ],
        "owner_approved_exposure_dimensions": [
            "ABSOLUTE_EXPOSURE",
            "NET_EXPOSURE",
            "GROSS_EXPOSURE",
            "CONTINGENT_EXPOSURE",
            "MARGIN_EXPOSURE",
            "STRESS_EXPOSURE",
        ],
        "pre_and_post_values_required_for_every_applicable_dimension": True,
        "required_metric_bindings": [
            "METRIC_ID",
            "UNIT",
            "CURRENCY",
            "VALUATION_TIMESTAMP",
            "HORIZON",
            "NETTING_SET",
            "CONVENTION",
        ],
        "scalar_risk_magnitudes_nonnegative": True,
        "signed_net_comparison": "ABS_POST_LE_ABS_PRE",
        "signed_net_sign_crossing_result": "DENY_EXCEPT_EXACT_ZERO",
        "nonnegative_scalar_dimensions": [
            "ABSOLUTE_EXPOSURE",
            "GROSS_EXPOSURE",
            "CONTINGENT_EXPOSURE",
            "MARGIN_EXPOSURE",
        ],
        "nonnegative_scalar_comparison": "POST_LE_PRE",
        "stress_scenario_set_and_hash_exact_match_required": True,
        "stress_comparison": "COMPONENTWISE_POST_LE_PRE_OR_OWNER_APPROVED_CONSERVATIVE_SCALAR_FUNCTIONAL",
        "missing_scenario_or_dimension_result": "DENY",
        "unknown_ambiguous_or_incomparable_exposure_result": "DENY",
        "sign_flip_result": "DENY",
        "missing_venue_capability_result": "DENY",
    }
    if record.get("configuration_mutation") != expected_configuration_mutation:
        errors.append("PM-DEC-003 configuration-mutation contract changed or is incomplete")
    if record.get("reconciliation") != expected_reconciliation:
        errors.append("PM-DEC-003 reconciliation contract changed or is incomplete")
    expected_working_order_sunset = {
        "applies_to": [
            "RISK_INCREASING_RESTING_ORDER",
            "RISK_INCREASING_OPEN_ORDER",
            "RISK_INCREASING_CONDITIONAL_ORDER",
        ],
        "venue_enforced_tif_or_expiry_required": True,
        "latest_expiry": "APPROVAL_EXPIRES_AT_MINUS_OWNER_APPROVED_CANCEL_RECONCILIATION_BUFFER",
        "gtc_without_bounded_venue_expiry_result": "DENY",
        "deadline_state": "NO_NEW_RISK",
        "deadline_actions": [
            "CANCEL_ALL_OPENING_AND_CONDITIONAL_ORDERS",
            "RECONCILE_VENUE_STATE",
        ],
        "revocation_action": "IMMEDIATE_CANCEL_ALL_OPENING_AND_CONDITIONAL_ORDERS",
        "cancel_pending_unknown_lost_ack_halt_or_restart_state": "RECONCILIATION_REQUIRED",
        "contingent_exposure_and_reservation_retained_until_verified_terminal_outcome": True,
        "zero_external_side_effect_promised_after_cancel_request": False,
        "verified_protective_reduce_only_path_may_continue": True,
        "new_or_increasing_risk_during_sunset_result": "DENY",
        "completion_requires_zero_remaining_opening_or_conditional_orders": True,
    }
    if record.get("working_order_sunset") != expected_working_order_sunset:
        errors.append("PM-DEC-003 working-order sunset contract changed or is incomplete")

    expected_invalidation = {
        "triggers": [
            "ACCOUNT_OR_CREDENTIAL_IDENTITY_REF_CHANGE",
            "STAGE_OR_CAPITAL_BOOK_CHANGE",
            "VENUE_MARKET_OR_INSTRUMENT_CHANGE",
            "STRATEGY_OR_BOT_CHANGE",
            "LIMIT_OR_PAYLOAD_CHANGE",
            "OWNER_TRUST_OR_SECOND_FACTOR_BINDING_CHANGE",
            "POLICY_SPEC_ACCEPTANCE_MANDATE_BUILD_OR_DATASET_HASH_CHANGE",
            "PARAMETER_BENCHMARK_DATA_COST_OR_FILL_MODEL_CHANGE",
            "CAPACITY_VENUE_API_MECHANICS_CHANGE",
            "EVIDENCE_DRIFT_THRESHOLD_BREACH",
        ],
        "result": "INVALIDATED_DENY",
        "new_approval_refreshes_evidence_or_viewed_holdout": False,
    }
    expected_revocation = {
        "append_only": True,
        "terminal": True,
        "unavailable_stale_or_conflicting_lookup_result": "DENY",
        "restoration_requires_new_version_and_higher_sequence": True,
        "freshness_limit": "OWNER_INPUT_REQUIRED",
    }
    expected_supersession = {
        "new_immutable_version_required": True,
        "higher_monotonic_sequence_required": True,
        "supersedes_ref_required": True,
        "old_version_terminal": True,
        "rollback_reactivates_old_version": False,
        "expansion_requires_full_activation": True,
        "emergency_restriction_applies_immediately": True,
    }
    if record.get("automatic_invalidation") != expected_invalidation:
        errors.append("PM-DEC-003 automatic invalidation contract changed or is incomplete")
    if record.get("revocation") != expected_revocation:
        errors.append("PM-DEC-003 revocation contract changed or is incomplete")
    if record.get("supersession") != expected_supersession:
        errors.append("PM-DEC-003 supersession contract changed or is incomplete")

    expected_open_exposure = {
        "expiry_revocation_suspension_or_invalidation_result": "NO_NEW_OR_INCREASE_RISK",
        "uncontrolled_market_exit_authorized": False,
        "verified_reduce_only_protection_and_reconciliation_may_continue": True,
        "protective_trade_requires_dimension_specific_typed_pre_post_proof_and_venue_capability": True,
        "unknown_ambiguous_missing_or_incomparable_exposure_proof_result": "DENY",
        "restoring_new_risk_requires_new_version_and_full_gate": True,
    }
    expected_independent = {
        "objects": list(PM_DEC003_INDEPENDENT_VALIDITY_OBJECTS),
        "one_object_renews_another": False,
        "effective_result": "MOST_RESTRICTIVE_INTERSECTION",
    }
    if record.get("open_exposure") != expected_open_exposure:
        errors.append("PM-DEC-003 open-exposure safety contract changed or is incomplete")
    if record.get("independent_validity") != expected_independent:
        errors.append("PM-DEC-003 independent-validity contract changed or is incomplete")

    expected_pending = {
        "level_a_review_interval": "UNRESOLVED",
        "pilot_operating_ttl": "UNRESOLVED",
        "production_operating_ttl": "UNRESOLVED",
        "real_account_or_credential_change_window": "UNRESOLVED",
        "hard_limit_leverage_or_margin_change_window": "UNRESOLVED",
        "transfer_or_distribution_window": "UNRESOLVED",
        "single_use_activation_window": "UNRESOLVED",
        "clock_skew_tolerance": "UNRESOLVED",
        "revocation_snapshot_max_age": "UNRESOLVED",
        "review_lead_time": "UNRESOLVED",
        "reconciliation_timeout": "UNRESOLVED",
        "working_order_cancel_reconciliation_buffer": "UNRESOLVED",
    }
    expected_safety = {
        "missing_numeric_profile_result": "DENY_REAL_CAPITAL",
        "expired_result": "DENY_NEW_OR_INCREASE_RISK",
        "revoked_result": "DENY_NEW_OR_INCREASE_RISK",
        "superseded_result": "DENY_NEW_OR_INCREASE_RISK",
        "consumed_replay_result": "DENY_NEW_SIDE_EFFECT",
        "unknown_state_result": "DENY",
        "preclaim_revocation_adapter_call_result": "DENY_NO_ADAPTER_CALL",
        "postclaim_unknown_result": "RECONCILIATION_REQUIRED_NO_ZERO_EFFECT_CLAIM",
        "configuration_consumed_operating_authority_result": "DENY_PENDING_SEPARATE_TIME_BOXED_MANIFEST",
        "changes_governance_risk_policy": False,
        "ratified_real_capital_manifest": False,
    }
    if record.get("pending_owner_values") != expected_pending:
        errors.append("PM-DEC-003 must not infer or import any numerical validity value")
    if record.get("safety") != expected_safety:
        errors.append("PM-DEC-003 fail-closed safety defaults changed or are incomplete")

    errors.extend(
        validate_snapshot_consistency(
            record,
            root=root,
            decision_id="PM-DEC-003",
            required_artifacts=PM_DEC003_REQUIRED_ARTIFACTS,
        )
    )

    integrity = record.get("integrity", {})
    if integrity.get("canonicalization") != "SORTED_KEYS_COMPACT_UTF8_JSON_V1":
        errors.append("PM-DEC-003 canonicalization contract is missing or changed")
    if integrity.get("decision_payload_sha256") != pm_dec003_payload_digest(record):
        errors.append("PM-DEC-003 canonical decision payload hash mismatch")
    return errors


def validity_profile_payload_digest(profile: dict) -> str:
    payload = {key: value for key, value in profile.items() if key not in {"profile_payload_sha256", "owner_authority"}}
    return canonical_json_digest(payload) or ""


def _venue_mechanics_result(scope: object) -> str:
    """Apply one closed per-venue mechanics matrix with reject-all default."""
    if not isinstance(scope, dict):
        return "DENY_UNKNOWN_OR_UNSUPPORTED_VENUE_MECHANICS"
    scalar_fields = (
        "venue_id",
        "venue_environment",
        "market_id",
        "api_or_protocol_version",
        "account_mode",
        "order_type",
        "time_in_force",
        "session_id",
    )
    if any(
        not isinstance(scope.get(field), str)
        or not scope[field].strip()
        for field in scalar_fields
    ):
        return "DENY_UNKNOWN_OR_UNSUPPORTED_VENUE_MECHANICS"
    venue = scope.get("venue_id")
    matrix = VENUE_MECHANICS_MATRIX.get(venue)
    if matrix is None:
        return "DENY_UNKNOWN_OR_UNSUPPORTED_VENUE_MECHANICS"
    if (
        scope.get("venue_environment") not in matrix["environments"]
        or scope.get("market_id") != matrix["market_id"]
    ):
        return "DENY_INCOHERENT_VENUE_ENVIRONMENT_MARKET"
    if venue == "MOEX":
        return "DENY_MOEX_FUTURE_BLOCKED"
    if (
        scope.get("api_or_protocol_version")
        != matrix["api_or_protocol_version"]
        or scope.get("account_mode") not in matrix["account_modes"]
        or scope.get("session_id") not in matrix["session_ids"]
    ):
        return "DENY_INCOHERENT_VENUE_API_ACCOUNT_OR_SESSION"
    if scope.get("order_type") == "MARKET":
        return "DENY_MARKET_ORDER_WHILE_LIMIT_ONLY"
    if (
        scope.get("order_type"),
        scope.get("time_in_force"),
    ) not in matrix["order_tif_pairs"]:
        return "DENY_UNSUPPORTED_ORDER_TYPE_OR_TIF"
    return "NON_AUTHORIZING_CLOSED_VENUE_MECHANICS_SHAPE_VALID"


def validity_profile_tuple_result(profile: object, *, require_numeric_values: bool) -> str:
    if not isinstance(profile, dict) or not isinstance(profile.get("exact_key"), dict):
        return "DENY_MALFORMED_PROFILE_TUPLE"
    key = profile["exact_key"]
    if set(key) != set(PM_DEC003_V2_EXACT_KEY_FIELDS):
        return "DENY_INEXACT_KEY"
    string_fields = set(PM_DEC003_V2_EXACT_KEY_FIELDS) - {
        "venue_capability_profile_version",
        "risk_policy_version",
    }
    if any(
        not isinstance(key.get(field), str)
        or not key[field].strip()
        or key[field] == "*"
        for field in string_fields
    ):
        return "DENY_EMPTY_OR_WILDCARD_IDENTITY"
    if any(
        isinstance(key.get(field), bool)
        or not isinstance(key.get(field), int)
        or key[field] < 1
        for field in ("venue_capability_profile_version", "risk_policy_version")
    ):
        return "DENY_TYPE_CONFUSION"
    if any(
        re.fullmatch(r"[0-9a-f]{64}", key[field]) is None
        for field in (
            "venue_capability_profile_sha256",
            "risk_policy_sha256",
            "calibration_stratum_sha256",
        )
    ):
        return "DENY_MALFORMED_EXACT_KEY_HASH"
    if (
        key.get("capital_stage") not in PM_NORMATIVE_CAPITAL_STAGES
        or key.get("liquidity_regime") not in LIQUIDITY_REGIMES
        or key.get("volatility_regime") not in VOLATILITY_REGIMES
        or key.get("degraded_state") not in DEGRADED_STATES
    ):
        return "DENY_UNKNOWN_CLOSED_TAXONOMY_VALUE"
    mechanics_result = _venue_mechanics_result(key)
    if mechanics_result != "NON_AUTHORIZING_CLOSED_VENUE_MECHANICS_SHAPE_VALID":
        return mechanics_result
    venue = key.get("venue_id")
    environment = key.get("venue_environment")
    tuple_fields = (key.get("capital_stage"), key.get("approval_tier"), key.get("validity_mode"), key.get("action_class"), key.get("risk_class"))
    noncapital = tuple_fields in {
        (stage, "LEVEL_A", "LONG_LIVED_NON_CAPITAL", "NON_CAPITAL", "A0_NON_CAPITAL")
        for stage in PM_DEC003_LEVEL_A_LIFECYCLE
    }
    pilot = tuple_fields == ("PILOT_LIMITED_LIVE", "LEVEL_B", "TIME_BOXED_REAL_CAPITAL", "PILOT_OPERATING_SCOPE", "B1_LIMITED_PILOT")
    production = tuple_fields == ("PRODUCTION_LIVE", "LEVEL_B", "TIME_BOXED_REAL_CAPITAL", "PRODUCTION_OPERATING_SCOPE", "B2_EXISTING_PRODUCTION")
    cash = tuple_fields in {
        (stage, "LEVEL_B", "ONE_TIME_REAL_CAPITAL", action, "B3_CASH_ACTION")
        for stage in ("PILOT_LIMITED_LIVE", "PRODUCTION_LIVE")
        for action in ("REAL_BOOK_TRANSFER", "DISTRIBUTION")
    }
    mutation = tuple_fields in {
        (stage, "LEVEL_B", "ONE_TIME_REAL_CAPITAL", action, "B4_AUTHORITY_MUTATION")
        for stage in ("PILOT_LIMITED_LIVE", "PRODUCTION_LIVE")
        for action in (
            "REAL_ACCOUNT_OR_CREDENTIAL_CHANGE",
            "REAL_SCOPE_EXPANSION",
            "HARD_LIMIT_INCREASE",
            "LEVERAGE_OR_MARGIN_CHANGE",
            "VALIDITY_PROFILE_AUTHORITY_CHANGE",
        )
    }
    if not any((noncapital, pilot, production, cash, mutation)):
        return "DENY_INCOHERENT_STAGE_TIER_VALIDITY_ACTION_RISK"
    if noncapital and environment in {"BITGET_PRODUCTION", "MOEX_PRODUCTION"}:
        return "DENY_NONCAPITAL_PROFILE_ON_PRODUCTION_ENVIRONMENT"
    if (pilot or production or cash or mutation) and environment not in {"BITGET_PRODUCTION", "MOEX_PRODUCTION"}:
        return "DENY_REAL_CAPITAL_PROFILE_ON_NONPRODUCTION_ENVIRONMENT"
    if venue == "BITGET" and (
        key.get("risk_policy_id") != APPROVED_BITGET_RISK_POLICY_ID
        or key.get("risk_policy_version") != APPROVED_BITGET_RISK_POLICY_VERSION
        or key.get("risk_policy_sha256") != APPROVED_BITGET_RISK_POLICY_SHA256
    ):
        return "DENY_RISK_POLICY_IDENTITY_SUBSTITUTION"
    required = set() if noncapital else (OPERATING_NUMERIC_FIELDS if pilot or production else SINGLE_USE_NUMERIC_FIELDS)
    for layer_name in ("owner_hard_bounds", "calibration_recommendation", "owner_selected_effective_values"):
        layer = profile.get(layer_name)
        if not isinstance(layer, dict) or not isinstance(layer.get("values"), dict):
            return "DENY_MALFORMED_NUMERIC_LAYER"
        values = layer["values"]
        if not values and layer.get("status") == "UNRESOLVED" and not require_numeric_values:
            continue
        if set(values) != required:
            return "DENY_MISSING_EXTRA_OR_INAPPLICABLE_NUMERIC_FIELD"
        if any(not _strict_positive_duration(value) for value in values.values()):
            return "DENY_TYPE_CONFUSION_OR_DURATION_BOUND"
    return "NON_AUTHORIZING_COHERENT_PROFILE_TUPLE"


def validity_profile_owner_authority_result(profile: object, owner_manifest: object, *, last_accepted_sequence: int) -> str:
    if not isinstance(profile, dict) or not isinstance(owner_manifest, dict) or isinstance(last_accepted_sequence, bool) or not isinstance(last_accepted_sequence, int):
        return "DENY_MALFORMED_OWNER_AUTHORITY"
    binding = profile.get("owner_authority")
    if not isinstance(binding, dict) or binding.get("status") != "VERIFIED":
        return "DENY_OWNER_AUTHORITY_ABSENT"
    required_manifest = {"manifest_ref", "manifest_sha256", "manifest_version", "manifest_sequence", "canonical_owner_payload_sha256"}
    if set(owner_manifest) != required_manifest:
        return "DENY_MALFORMED_OWNER_AUTHORITY"
    if any(binding.get(field) != owner_manifest.get(field) for field in required_manifest):
        return "DENY_OWNER_AUTHORITY_MISMATCH"
    sequence = owner_manifest.get("manifest_sequence")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence <= last_accepted_sequence:
        return "DENY_OWNER_AUTHORITY_REPLAY"
    canonical_owner_payload = {
        "profile_id": profile.get("profile_id"),
        "profile_version": profile.get("profile_version"),
        "profile_payload_sha256": profile.get("profile_payload_sha256"),
        "owner_hard_bounds": profile.get("owner_hard_bounds"),
        "owner_selected_effective_values": profile.get("owner_selected_effective_values"),
    }
    digest = canonical_json_digest(canonical_owner_payload)
    if owner_manifest.get("canonical_owner_payload_sha256") != digest:
        return "DENY_OWNER_CANONICAL_PAYLOAD_MISMATCH"
    return "NON_AUTHORIZING_OWNER_BINDING_SHAPE_VALID"


def validity_profile_owner_bounds_result(profile: object) -> str:
    if not isinstance(profile, dict):
        return "DENY_MALFORMED_OWNER_NUMERIC_LAYERS"
    hard = profile.get("owner_hard_bounds")
    effective = profile.get("owner_selected_effective_values")
    calibration = profile.get("calibration_recommendation")
    if not all(isinstance(layer, dict) for layer in (hard, effective, calibration)):
        return "DENY_MALFORMED_OWNER_NUMERIC_LAYERS"
    if hard.get("status") != "VERIFIED" or effective.get("status") != "VERIFIED":
        return "DENY_SIGNED_BUT_OWNER_VALUES_UNRESOLVED"
    if calibration.get("status") != "NON_AUTHORIZING_RECOMMENDATION":
        return "DENY_CALIBRATION_STATUS_OR_AUTHORITY_CONFUSION"
    hard_values = hard.get("values")
    effective_values = effective.get("values")
    calibration_values = calibration.get("values")
    if not all(isinstance(values, dict) for values in (hard_values, effective_values, calibration_values)):
        return "DENY_MALFORMED_OWNER_NUMERIC_LAYERS"
    if set(hard_values) != set(effective_values) or set(hard_values) != set(calibration_values):
        return "DENY_MISSING_OR_INCOMPARABLE_OWNER_BOUND"
    for field in hard_values:
        if field not in VALIDITY_NUMERIC_SAFETY_DIRECTIONS:
            return "DENY_UNKNOWN_OWNER_BOUND_DIRECTION"
        bound, selected, recommended = (
            hard_values[field],
            effective_values[field],
            calibration_values[field],
        )
        if any(
            not _strict_positive_duration(value)
            for value in (bound, selected, recommended)
        ):
            return "DENY_MISSING_OR_INCOMPARABLE_OWNER_BOUND"
        direction = VALIDITY_NUMERIC_SAFETY_DIRECTIONS[field]
        if direction == "DECREASE" and selected > bound:
            return "DENY_EFFECTIVE_VALUE_OUTSIDE_OWNER_BOUND"
        if direction == "INCREASE" and selected < bound:
            return "DENY_EFFECTIVE_VALUE_OUTSIDE_OWNER_BOUND"
        if direction == "DECREASE" and recommended > bound:
            return "DENY_CALIBRATION_RECOMMENDATION_OUTSIDE_OWNER_BOUND"
        if direction == "INCREASE" and recommended < bound:
            return "DENY_CALIBRATION_RECOMMENDATION_OUTSIDE_OWNER_BOUND"
        if direction not in {"DECREASE", "INCREASE"} and selected != bound:
            return "DENY_NON_MONOTONE_OWNER_VALUE_MISMATCH"
        if direction not in {"DECREASE", "INCREASE"} and recommended != bound:
            return "DENY_CALIBRATION_RECOMMENDATION_OUTSIDE_OWNER_BOUND"
    return "NON_AUTHORIZING_OWNER_BOUNDS_SHAPE_VALID"


def validity_profile_lookup_result(
    profiles: object,
    exact_key: object,
    *,
    schema_bytes: object,
    registry_context: object,
) -> str:
    """Strict non-authorizing registry lookup with no implicit fallback."""
    if not isinstance(profiles, list) or not isinstance(exact_key, dict) or not isinstance(schema_bytes, bytes) or not isinstance(registry_context, dict):
        return "DENY_MALFORMED_LOOKUP"
    schema_bytes_sha256 = hashlib.sha256(schema_bytes).hexdigest()
    schema = _parse_json_bytes_strict(schema_bytes)
    if not isinstance(schema, dict):
        return "DENY_SCHEMA_BYTES_INVALID"
    draft_schema_id = "https://tradebot.local/schemas/non-authorizing-validity-profile-draft-v1.json"
    active_claim = any(
        isinstance(profile, dict)
        and (
            profile.get("profile_status") == "ACTIVE"
            or (
                isinstance(profile.get("lifecycle"), dict)
                and profile["lifecycle"].get("state") == "ACTIVE"
            )
            or profile.get("capability_evidence_status") == "VERIFIED"
        )
        for profile in profiles
    )
    if schema.get("$id") != draft_schema_id or active_claim:
        return ACTIVE_SCHEMA_UNAVAILABLE
    if set(exact_key) != set(PM_DEC003_V2_EXACT_KEY_FIELDS):
        return "DENY_INEXACT_KEY"
    if any(
        value is None
        or (isinstance(value, str) and (not value.strip() or value == "*"))
        for value in exact_key.values()
    ):
        return "DENY_WILDCARD_OR_EMPTY_KEY"
    key_schema = schema.get("properties", {}).get("exact_key")
    if not isinstance(key_schema, dict) or validate_schema_subset(exact_key, key_schema, root_schema=schema):
        return "DENY_EXACT_KEY_SCHEMA_INVALID"
    required_context = {
        "decision_sha256", "risk_policy_hashes", "capability_hashes", "schema_hashes",
        "profile_hashes", "evidence_hashes", "family_status", "now_utc", "owner_manifest",
        "last_owner_sequence", "last_profile_sequence",
    }
    if (
        set(registry_context) != required_context
        or _parse_strict_utc(registry_context.get("now_utc")) is None
        or not isinstance(registry_context.get("decision_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", registry_context["decision_sha256"]) is None
        or any(not isinstance(registry_context.get(field), dict) for field in ("risk_policy_hashes", "capability_hashes", "schema_hashes", "profile_hashes", "evidence_hashes", "family_status"))
        or isinstance(registry_context.get("last_profile_sequence"), bool)
        or not isinstance(registry_context.get("last_profile_sequence"), int)
    ):
        return "DENY_INVALID_REGISTRY_CONTEXT"
    if exact_key.get("venue_id") == "MOEX":
        return "DENY_MOEX_FUTURE_BLOCKED"
    if registry_context["family_status"].get(exact_key.get("venue_id")) != "ENABLED_NONAUTHORIZING_VALIDATION":
        return "DENY_VENUE_FAMILY_BLOCKED_OR_UNKNOWN"
    candidates: list[dict] = []
    for profile in profiles:
        if not isinstance(profile, dict) or validate_schema_subset(profile, schema):
            return "DENY_PROFILE_SCHEMA_INVALID"
        if profile.get("exact_key") != exact_key:
            continue
        if profile.get("profile_payload_sha256") != validity_profile_payload_digest(profile):
            return "DENY_PROFILE_PAYLOAD_HASH_MISMATCH"
        schema_binding = f"{profile.get('schema_id')}:{profile.get('schema_version')}"
        if (
            schema.get("$id") != profile.get("schema_id")
            or schema.get("x-schema-version") != profile.get("schema_version")
            or profile.get("schema_sha256") != schema_bytes_sha256
            or registry_context["schema_hashes"].get(schema_binding) != schema_bytes_sha256
        ):
            return "DENY_SCHEMA_ID_VERSION_HASH_MISMATCH"
        profile_sequence = profile.get("profile_sequence")
        supersedes_sequence = profile.get("supersedes_sequence")
        if (
            isinstance(profile_sequence, bool) or not isinstance(profile_sequence, int)
            or isinstance(supersedes_sequence, bool) or not isinstance(supersedes_sequence, int)
            or profile_sequence <= registry_context["last_profile_sequence"]
            or supersedes_sequence != registry_context["last_profile_sequence"]
            or profile_sequence <= supersedes_sequence
        ):
            return "DENY_PROFILE_SEQUENCE_REPLAY_OR_GAP"
        if registry_context["profile_hashes"].get(profile.get("supersedes_ref")) != profile.get("supersedes_sha256"):
            return "DENY_SUPERSEDES_REF_HASH_MISMATCH"
        if profile.get("decision_sha256") != registry_context["decision_sha256"]:
            return "DENY_DECISION_HASH_MISMATCH"
        risk_binding = f"{exact_key['risk_policy_id']}:{exact_key['risk_policy_version']}"
        if registry_context["risk_policy_hashes"].get(risk_binding) != exact_key["risk_policy_sha256"]:
            return "DENY_RISK_POLICY_HASH_MISMATCH"
        capability_binding = f"{exact_key['venue_capability_profile_id']}:{exact_key['venue_capability_profile_version']}"
        if profile.get("capability_evidence_status") != "VERIFIED" or registry_context["capability_hashes"].get(capability_binding) != exact_key["venue_capability_profile_sha256"]:
            return "DENY_CAPABILITY_EVIDENCE_MISSING_OR_MISMATCH"
        evidence = profile.get("evidence", {})
        evidence_as_of = _parse_strict_utc(evidence.get("as_of"))
        if (
            evidence.get("status") != "VERIFIED"
            or evidence.get("freshness_status") != "VERIFIED_CURRENT"
            or not isinstance(evidence_as_of, datetime)
            or evidence_as_of > _parse_strict_utc(registry_context["now_utc"])
            or registry_context["evidence_hashes"].get(evidence.get("manifest_ref")) != evidence.get("manifest_sha256")
            or not isinstance(evidence.get("issuer_ref"), str)
            or evidence.get("issuer_ref", "").startswith("UNRESOLVED")
        ):
            return "DENY_EVIDENCE_BINDING_OR_FRESHNESS"
        tuple_result = validity_profile_tuple_result(profile, require_numeric_values=True)
        if tuple_result != "NON_AUTHORIZING_COHERENT_PROFILE_TUPLE":
            return tuple_result
        bound_result = validity_profile_owner_bounds_result(profile)
        if bound_result != "NON_AUTHORIZING_OWNER_BOUNDS_SHAPE_VALID":
            return bound_result
        now = _parse_strict_utc(registry_context["now_utc"])
        valid_from = _parse_strict_utc(profile.get("valid_from"))
        review_due = _parse_strict_utc(profile.get("review_due_at"))
        expires = _parse_strict_utc(profile.get("expires_at"))
        if None in (now, valid_from, review_due, expires) or not (valid_from <= now < review_due < expires):
            return "DENY_PROFILE_STALE_OR_INVALID_TIME"
        owner_result = validity_profile_owner_authority_result(profile, registry_context.get("owner_manifest"), last_accepted_sequence=registry_context.get("last_owner_sequence"))
        if owner_result != "NON_AUTHORIZING_OWNER_BINDING_SHAPE_VALID":
            return owner_result
        if profile.get("profile_status") != "ACTIVE" or profile.get("lifecycle", {}).get("state") != "ACTIVE":
            continue
        if profile.get("eligible_for_authorization") is not False or profile.get("authorization_result") != "DENY" or profile.get("live_trading_enabled") is not False:
            return "DENY_PROFILE_AUTHORITY_MISMATCH"
        candidates.append(profile)
    if len(candidates) != 1:
        return "DENY_ZERO_OR_MULTIPLE_ACTIVE_MATCHES"
    return "NON_AUTHORIZING_EXACT_PROFILE_SHAPE_MATCH"


VALIDITY_NUMERIC_SAFETY_DIRECTIONS = {
        "operating_ttl_ms": "DECREASE",
        "single_use_activation_window_ms": "DECREASE",
        "cancel_reconciliation_buffer_ms": "INCREASE",
        "dispatch_guard_ms": "INCREASE",
        "clock_skew_tolerance_ms": "DECREASE",
        "revocation_snapshot_max_age_ms": "DECREASE",
        "review_lead_time_ms": "INCREASE",
        "reconciliation_escalation_deadline_ms": "DECREASE",
}


def validity_profile_monotone_result(
    previous: object,
    proposed: object,
    *,
    previous_authorized_actions: object,
    proposed_authorized_actions: object,
    history: object,
    action_class: object = None,
    overlay_id: object = None,
    owner_epoch: object = None,
) -> str:
    """Validate one restrictive overlay against complete immutable epoch history.

    A successful result is deliberately non-authorizing: this pure helper is not a
    signed persistent registry or a runtime trust root.
    """
    if (
        not isinstance(previous, dict)
        or not isinstance(proposed, dict)
        or not isinstance(history, dict)
        or not isinstance(action_class, str)
        or action_class not in ACTION_NUMERIC_FIELDS
        or not isinstance(overlay_id, str)
        or not overlay_id.strip()
        or isinstance(owner_epoch, bool)
        or not isinstance(owner_epoch, int)
        or owner_epoch < 1
    ):
        return "DENY_INCOMPARABLE_CHANGE"
    expected_fields = ACTION_NUMERIC_FIELDS[action_class]
    if set(previous) != expected_fields or set(proposed) != expected_fields:
        return "DENY_INCOMPLETE_NUMERIC_VECTOR"
    if not isinstance(previous_authorized_actions, (list, set, tuple)) or not isinstance(proposed_authorized_actions, (list, set, tuple)):
        return "DENY_INCOMPARABLE_ACTION_SET"
    if any(not isinstance(item, str) or not item for item in [*previous_authorized_actions, *proposed_authorized_actions]):
        return "DENY_INCOMPARABLE_ACTION_SET"
    if not set(proposed_authorized_actions).issubset(set(previous_authorized_actions)):
        return "DENY_AUTHORIZED_ACTION_EXPANSION"
    if set(history) != {"owner_epoch", "complete", "immutable", "entries"}:
        return "DENY_INCOMPLETE_OR_UNTRUSTED_HISTORY"
    if (
        history.get("owner_epoch") != owner_epoch
        or history.get("complete") is not True
        or history.get("immutable") is not True
        or not isinstance(history.get("entries"), list)
    ):
        return "DENY_INCOMPLETE_OR_UNTRUSTED_HISTORY"
    seen_overlay_ids: set[str] = set()
    history_vectors: list[dict] = []
    for entry in history["entries"]:
        if not isinstance(entry, dict) or set(entry) != {
            "overlay_id", "owner_epoch", "action_class", "values", "authorized_actions",
        }:
            return "DENY_INCOMPARABLE_HISTORY"
        entry_id = entry.get("overlay_id")
        entry_values = entry.get("values")
        entry_actions = entry.get("authorized_actions")
        if (
            not isinstance(entry_id, str)
            or not entry_id.strip()
            or entry_id in seen_overlay_ids
            or entry_id == overlay_id
            or entry.get("owner_epoch") != owner_epoch
            or entry.get("action_class") != action_class
            or not isinstance(entry_values, dict)
            or set(entry_values) != expected_fields
            or not isinstance(entry_actions, list)
            or any(not isinstance(item, str) or not item for item in entry_actions)
        ):
            return "DENY_INCOMPARABLE_HISTORY"
        if not set(proposed_authorized_actions).issubset(set(entry_actions)):
            return "DENY_REBOUND_OR_AUTOMATIC_RELAXATION"
        seen_overlay_ids.add(entry_id)
        history_vectors.append(entry_values)
    comparisons = [previous, *history_vectors]
    if any(not isinstance(item, dict) or set(item) != expected_fields for item in comparisons):
        return "DENY_INCOMPARABLE_HISTORY"
    for baseline in comparisons:
      for field in expected_fields:
        direction = VALIDITY_NUMERIC_SAFETY_DIRECTIONS[field]
        before, after = baseline[field], proposed[field]
        if any(not _strict_positive_duration(value) for value in (before, after)):
            if any(
                isinstance(value, int)
                and not isinstance(value, bool)
                and value > VALIDITY_DURATION_TECHNICAL_MAX_MS
                for value in (before, after)
            ):
                return "DENY_DURATION_TECHNICAL_MAX_EXCEEDED"
            return "DENY_TYPE_CONFUSION"
        if direction == "DECREASE" and after > before:
            return "DENY_REBOUND_OR_AUTOMATIC_RELAXATION" if baseline is not previous else "DENY_AUTOMATIC_RELAXATION"
        if direction == "INCREASE" and after < before:
            return "DENY_REBOUND_OR_AUTOMATIC_RELAXATION" if baseline is not previous else "DENY_AUTOMATIC_RELAXATION"
    return "NON_AUTHORIZING_MONOTONE_SAFER_OVERLAY_SHAPE"


def _mandatory_sunset_deadline(
    mandatory_cutoffs: object,
    cancel_reconciliation_buffer_ms: object,
) -> tuple[datetime | None, str | None]:
    """Derive one deadline shared by feasibility and strict sunset checks."""
    if (
        not isinstance(mandatory_cutoffs, dict)
        or set(mandatory_cutoffs) != MANDATORY_SUNSET_CUTOFF_FIELDS
        or not _strict_positive_duration(cancel_reconciliation_buffer_ms)
    ):
        return None, "DENY_MALFORMED_MANDATORY_CUTOFF_BINDING"
    parsed = [_parse_strict_utc(value) for value in mandatory_cutoffs.values()]
    if any(value is None for value in parsed):
        return None, "DENY_INVALID_UTC_TIMESTAMP"
    try:
        return min(parsed) - timedelta(
            milliseconds=cancel_reconciliation_buffer_ms
        ), None
    except (OverflowError, TypeError):
        return None, "DENY_DURATION_ARITHMETIC_OVERFLOW"


def validity_profile_feasibility_result(values: object) -> str:
    if not isinstance(values, dict):
        return "DENY_MISSING_OWNER_VALUES"
    required = {
        "operating_ttl_ms", "cancel_reconciliation_buffer_ms", "dispatch_guard_ms", "reconciliation_escalation_deadline_ms", "duration_unit",
        "mandatory_cutoffs", "order_id", "order_expiry_at", "late_fill_state", "reconciliation_state",
        "escalation_deadline_reached", "exposure_or_reservation_released", "no_new_risk_cleared",
    }
    if set(values) != required:
        return "DENY_MISSING_OWNER_VALUES"
    if values.get("duration_unit") != "ms":
        return "DENY_INCOMPATIBLE_UNIT"
    numeric_fields = ("operating_ttl_ms", "cancel_reconciliation_buffer_ms", "dispatch_guard_ms", "reconciliation_escalation_deadline_ms")
    if any(isinstance(values[field], bool) or not isinstance(values[field], int) or values[field] < 1 for field in numeric_fields):
        return "DENY_TYPE_CONFUSION"
    if any(values[field] > VALIDITY_DURATION_TECHNICAL_MAX_MS for field in numeric_fields):
        return "DENY_DURATION_TECHNICAL_MAX_EXCEEDED"
    boolean_fields = ("escalation_deadline_reached", "exposure_or_reservation_released", "no_new_risk_cleared")
    if any(not isinstance(values[field], bool) for field in boolean_fields):
        return "DENY_TYPE_CONFUSION"
    if values["operating_ttl_ms"] <= values["cancel_reconciliation_buffer_ms"] + values["dispatch_guard_ms"]:
        return "DENY_INFEASIBLE_TTL_BUFFER_GUARD"
    if (
        not isinstance(values.get("order_id"), str)
        or not values["order_id"].strip()
    ):
        return "DENY_MALFORMED_WORKING_ORDER_IDENTITY"
    order_expiry = _parse_strict_utc(values.get("order_expiry_at"))
    if order_expiry is None:
        return "DENY_INVALID_UTC_TIMESTAMP"
    sunset_deadline, cutoff_error = _mandatory_sunset_deadline(
        values.get("mandatory_cutoffs"),
        values["cancel_reconciliation_buffer_ms"],
    )
    if cutoff_error is not None or sunset_deadline is None:
        return cutoff_error or "DENY_MALFORMED_MANDATORY_CUTOFF_BINDING"
    if order_expiry > sunset_deadline:
        return "DENY_ORDER_EXPIRY_AFTER_SUNSET_DEADLINE"
    if values.get("escalation_deadline_reached") is True and (values.get("exposure_or_reservation_released") is True or values.get("no_new_risk_cleared") is True):
        return "DENY_ESCALATION_DEADLINE_USED_AS_TERMINAL_PROOF"
    if values.get("late_fill_state") != "VERIFIED_NO_LATE_FILL" or values.get("reconciliation_state") != "VERIFIED_TERMINAL":
        return "RECONCILIATION_REQUIRED_LATE_FILL_UNKNOWN"
    return "NON_AUTHORIZING_FEASIBLE_SHAPE"


def validity_profile_timestamp_binding_result(
    action_class: object,
    values: object,
    timestamps: object,
) -> str:
    """Bind absolute UTC timestamps to one exact action-specific duration vector."""
    action_family = (
        "OPERATING"
        if action_class in {"PILOT_OPERATING_SCOPE", "PRODUCTION_OPERATING_SCOPE"}
        else "SINGLE_USE"
        if action_class in {
            "REAL_BOOK_TRANSFER",
            "DISTRIBUTION",
            "REAL_ACCOUNT_OR_CREDENTIAL_CHANGE",
            "REAL_SCOPE_EXPANSION",
            "HARD_LIMIT_INCREASE",
            "LEVERAGE_OR_MARGIN_CHANGE",
            "VALIDITY_PROFILE_AUTHORITY_CHANGE",
        }
        else None
    )
    required_timestamps = {
        "effective_from",
        "review_due_at",
        "expires_at",
        "commit_at",
        "evaluated_at",
        "revocation_snapshot_at",
        "first_durable_unknown_at",
        "escalation_due_at",
        "escalation_dispatched_at",
        "escalation_ack_at",
    }
    if (
        action_family is None
        or not isinstance(values, dict)
        or set(values) != ACTION_NUMERIC_FIELDS[action_family]
        or not isinstance(timestamps, dict)
        or set(timestamps) != required_timestamps
        or any(not _strict_positive_duration(item) for item in values.values())
    ):
        return "DENY_MISSING_EXTRA_OR_INAPPLICABLE_TEMPORAL_FIELD"
    parsed: dict[str, datetime | None] = {}
    for field, raw in timestamps.items():
        if raw is None and field in {
            "review_due_at",
            "first_durable_unknown_at",
            "escalation_due_at",
            "escalation_dispatched_at",
            "escalation_ack_at",
        }:
            parsed[field] = None
            continue
        parsed[field] = _parse_strict_utc(raw)
        if parsed[field] is None:
            return "DENY_INVALID_UTC_TIMESTAMP"
    effective = parsed["effective_from"]
    expires = parsed["expires_at"]
    commit = parsed["commit_at"]
    evaluated = parsed["evaluated_at"]
    revocation_snapshot = parsed["revocation_snapshot_at"]
    if not all(
        isinstance(item, datetime)
        for item in (effective, expires, commit, evaluated, revocation_snapshot)
    ):
        return "DENY_INVALID_UTC_TIMESTAMP"
    try:
        expected_expiry = effective + timedelta(
            milliseconds=values[
                "operating_ttl_ms"
                if action_family == "OPERATING"
                else "single_use_activation_window_ms"
            ]
        )
        latest_commit = expires - timedelta(milliseconds=values["dispatch_guard_ms"])
        revocation_age_at_commit = commit - revocation_snapshot
    except (OverflowError, TypeError):
        return "DENY_DURATION_ARITHMETIC_OVERFLOW"
    if action_family == "OPERATING" and expires <= effective:
        return "DENY_NONPOSITIVE_OPERATING_INTERVAL"
    if expires != expected_expiry:
        return "DENY_DURATION_TIMESTAMP_MISMATCH"
    if commit < effective:
        return "DENY_COMMIT_BEFORE_EFFECTIVE_FROM"
    if evaluated < effective or evaluated > commit or evaluated >= expires:
        return "DENY_EVALUATION_OUTSIDE_EFFECTIVE_INTERVAL"
    if commit > latest_commit:
        return "DENY_INSUFFICIENT_DISPATCH_GUARD"
    if revocation_snapshot > evaluated or revocation_age_at_commit < timedelta(
        0
    ) or revocation_age_at_commit > timedelta(
        milliseconds=values["revocation_snapshot_max_age_ms"]
    ):
        return "DENY_STALE_OR_CAUSALLY_INVALID_REVOCATION_SNAPSHOT"
    review_due = parsed["review_due_at"]
    if action_family == "OPERATING":
        try:
            expected_review_due = expires - timedelta(
                milliseconds=values["review_lead_time_ms"]
            )
        except (OverflowError, TypeError):
            return "DENY_DURATION_ARITHMETIC_OVERFLOW"
        if (
            review_due != expected_review_due
            or not isinstance(review_due, datetime)
        ):
            return "DENY_REVIEW_LEAD_TIMESTAMP_MISMATCH"
        if (
            not effective < review_due
            or evaluated >= review_due
            or commit >= review_due
        ):
            return "DENY_REVIEW_CUTOFF_REACHED_OR_INVALID"
    elif review_due is not None:
        return "DENY_MISSING_EXTRA_OR_INAPPLICABLE_TEMPORAL_FIELD"
    first_unknown = parsed["first_durable_unknown_at"]
    escalation_due = parsed["escalation_due_at"]
    dispatched = parsed["escalation_dispatched_at"]
    ack = parsed["escalation_ack_at"]
    if first_unknown is None:
        if any(item is not None for item in (escalation_due, dispatched, ack)):
            return "DENY_CAUSALLY_INVALID_ESCALATION_ORDER"
    else:
        try:
            expected_due = first_unknown + timedelta(
                milliseconds=values["reconciliation_escalation_deadline_ms"]
            )
        except (OverflowError, TypeError):
            return "DENY_DURATION_ARITHMETIC_OVERFLOW"
        if escalation_due != expected_due:
            return "DENY_ESCALATION_DEADLINE_TIMESTAMP_MISMATCH"
        if first_unknown > evaluated:
            return "DENY_CAUSALLY_INVALID_ESCALATION_ORDER"
        if dispatched is not None and (
            dispatched < first_unknown or dispatched > evaluated
        ):
            return "DENY_CAUSALLY_INVALID_ESCALATION_ORDER"
        if ack is not None and (
            dispatched is None or ack < dispatched or ack > evaluated
        ):
            return "DENY_CAUSALLY_INVALID_ESCALATION_ORDER"
    return "NON_AUTHORIZING_TIMESTAMP_BINDING_SHAPE_VALID"


RUNTIME_SEMANTIC_SCOPE_FIELDS = (
    "venue_id",
    "venue_environment",
    "market_id",
    "capital_stage",
    "risk_class",
    "api_or_protocol_version",
    "account_mode",
    "order_type",
    "time_in_force",
    "session_id",
    "liquidity_regime",
    "volatility_regime",
    "degraded_state",
    "calibration_stratum_id",
    "calibration_stratum_sha256",
    "risk_policy_id",
    "risk_policy_version",
    "risk_policy_sha256",
)


def validity_artifact_scope_result(
    request: object,
    artifact_bytes: object,
    *,
    expected_kind: object,
    expected_sha256: object,
    now_utc: object,
) -> str:
    """Check exact bytes and closed semantic scope without claiming trust."""
    if (
        not isinstance(request, dict)
        or set(request) != set(RUNTIME_SEMANTIC_SCOPE_FIELDS)
        or any(
            not isinstance(request.get(field), str) or not request[field].strip()
            for field in set(RUNTIME_SEMANTIC_SCOPE_FIELDS)
            - {"risk_policy_version"}
        )
        or isinstance(request.get("risk_policy_version"), bool)
        or not isinstance(request.get("risk_policy_version"), int)
        or request["risk_policy_version"] < 1
        or expected_kind not in {"VENUE_CAPABILITY", "RISK_POLICY"}
        or not isinstance(expected_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None
        or not isinstance(artifact_bytes, bytes)
    ):
        return "DENY_MALFORMED_ARTIFACT_BINDING"
    if expected_kind == "RISK_POLICY":
        mechanics_result = _venue_mechanics_result(request)
        if (
            mechanics_result
            != "NON_AUTHORIZING_CLOSED_VENUE_MECHANICS_SHAPE_VALID"
        ):
            return mechanics_result
        try:
            actual_policy_bytes = (
                ROOT / "governance/risk-policy.toml"
            ).read_bytes()
        except OSError:
            return "DENY_GOVERNANCE_RISK_POLICY_EXACT_BYTES_MISMATCH"
        if (
            expected_sha256 != APPROVED_BITGET_RISK_POLICY_SHA256
            or hashlib.sha256(artifact_bytes).hexdigest()
            != APPROVED_BITGET_RISK_POLICY_SHA256
            or artifact_bytes != actual_policy_bytes
        ):
            return "DENY_GOVERNANCE_RISK_POLICY_EXACT_BYTES_MISMATCH"
        try:
            policy = tomllib.loads(artifact_bytes.decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError):
            return "DENY_MALFORMED_GOVERNANCE_RISK_POLICY"
        required_policy_sections = {
            "policy_id",
            "version",
            "status",
            "change_control",
            "scope",
            "allocation",
            "position_risk",
            "entry",
            "stop_interpretation",
            "management",
            "safety",
            "live_trading",
        }
        scope = policy.get("scope")
        entry = policy.get("entry")
        live = policy.get("live_trading")
        if (
            set(policy) != required_policy_sections
            or policy.get("policy_id") != APPROVED_BITGET_RISK_POLICY_ID
            or policy.get("version") != APPROVED_BITGET_RISK_POLICY_VERSION
            or not isinstance(scope, dict)
            or scope.get("exchange") != "Bitget"
            or scope.get("market") != "USDT-margined futures"
            or scope.get("allowed_symbols") != ["BTCUSDT"]
            or not isinstance(entry, dict)
            or entry.get("order_type") != "limit_only"
            or not isinstance(live, dict)
            or live.get("enabled") is not False
            or request.get("risk_policy_id")
            != APPROVED_BITGET_RISK_POLICY_ID
            or request.get("risk_policy_version")
            != APPROVED_BITGET_RISK_POLICY_VERSION
            or request.get("risk_policy_sha256")
            != APPROVED_BITGET_RISK_POLICY_SHA256
        ):
            return "DENY_GOVERNANCE_RISK_POLICY_SEMANTIC_BINDING_MISMATCH"
        return "NON_AUTHORIZING_EXACT_GOVERNANCE_POLICY_SCOPE_SHAPE_VALID"
    if hashlib.sha256(artifact_bytes).hexdigest() != expected_sha256:
        return "DENY_ARTIFACT_EXACT_BYTES_HASH_MISMATCH"
    artifact = _parse_json_bytes_strict(artifact_bytes)
    required = {
        "artifact_kind",
        "artifact_id",
        "artifact_version",
        "lifecycle",
        "effective_from",
        "review_due_at",
        "expires_at",
        "semantic_scope",
        "limit_only",
        "provenance",
    }
    if not isinstance(artifact, dict) or set(artifact) != required:
        return "DENY_MALFORMED_ARTIFACT_BINDING"
    if (
        artifact.get("artifact_kind") != expected_kind
        or not isinstance(artifact.get("artifact_id"), str)
        or not artifact["artifact_id"].strip()
        or isinstance(artifact.get("artifact_version"), bool)
        or not isinstance(artifact.get("artifact_version"), int)
        or artifact["artifact_version"] < 1
        or artifact.get("lifecycle") != "ACTIVE_VERIFIED_CURRENT"
        or not isinstance(artifact.get("semantic_scope"), dict)
        or artifact["semantic_scope"] != request
        or not isinstance(artifact.get("limit_only"), bool)
        or not isinstance(artifact.get("provenance"), list)
        or not artifact["provenance"]
        or any(not isinstance(item, str) or not item.strip() for item in artifact["provenance"])
    ):
        return "DENY_ARTIFACT_LIFECYCLE_OR_SEMANTIC_SCOPE_MISMATCH"
    mechanics_result = _venue_mechanics_result(request)
    if (
        mechanics_result
        != "NON_AUTHORIZING_CLOSED_VENUE_MECHANICS_SHAPE_VALID"
    ):
        return mechanics_result
    now = _parse_strict_utc(now_utc)
    effective = _parse_strict_utc(artifact.get("effective_from"))
    review = _parse_strict_utc(artifact.get("review_due_at"))
    expires = _parse_strict_utc(artifact.get("expires_at"))
    if (
        None in (now, effective, review, expires)
        or not (effective <= now < review < expires)
    ):
        return "DENY_ARTIFACT_STALE_OR_INVALID_TIME"
    if request["venue_id"] == "BITGET" and request["order_type"] == "MARKET":
        return "DENY_MARKET_ORDER_WHILE_LIMIT_ONLY"
    return "NON_AUTHORIZING_EXACT_BYTE_SEMANTIC_SCOPE_SHAPE_VALID"


def validity_evidence_manifest_result(
    request: object,
    manifest_bytes: object,
    *,
    expected_sha256: object,
    now_utc: object,
    owner_bound_thresholds_bytes: object = None,
    owner_bound_thresholds_sha256: object = None,
) -> str:
    """Validate declared canonical shape and causality, never statistical truth."""
    if (
        not isinstance(request, dict)
        or set(request) != set(RUNTIME_SEMANTIC_SCOPE_FIELDS)
        or not isinstance(manifest_bytes, bytes)
        or not isinstance(expected_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None
    ):
        return "DENY_MALFORMED_EVIDENCE_MANIFEST"
    if (
        request.get("liquidity_regime") not in LIQUIDITY_REGIMES
        or request.get("volatility_regime") not in VOLATILITY_REGIMES
        or request.get("degraded_state") not in DEGRADED_STATES
    ):
        return "DENY_EVIDENCE_SCOPE_TAXONOMY_UNKNOWN"
    if "UNRESOLVED_DENY" in {
        request["liquidity_regime"],
        request["volatility_regime"],
        request["degraded_state"],
    }:
        return "DENY_EVIDENCE_SCOPE_UNRESOLVED"
    if hashlib.sha256(manifest_bytes).hexdigest() != expected_sha256:
        return "DENY_EVIDENCE_EXACT_BYTES_HASH_MISMATCH"
    if (
        not isinstance(owner_bound_thresholds_bytes, bytes)
        or not isinstance(owner_bound_thresholds_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", owner_bound_thresholds_sha256) is None
        or hashlib.sha256(owner_bound_thresholds_bytes).hexdigest()
        != owner_bound_thresholds_sha256
        or canonical_json_bytes_result(owner_bound_thresholds_bytes)
        != "NON_AUTHORIZING_CANONICAL_JSON_SHAPE_VALID"
    ):
        return "DENY_OWNER_BOUND_EVIDENCE_THRESHOLDS_MISSING_OR_MISMATCH"
    thresholds = _parse_json_bytes_strict(owner_bound_thresholds_bytes)
    threshold_required = {
        "binding_id",
        "binding_version",
        "status",
        "semantic_scope",
        "minimum_raw_sample_size",
        "minimum_cluster_sample_size",
        "minimum_effective_sample_size",
        "minimum_window_observations",
        "required_provenance_refs",
    }
    if (
        not isinstance(thresholds, dict)
        or set(thresholds) != threshold_required
        or not isinstance(thresholds.get("binding_id"), str)
        or not thresholds["binding_id"].strip()
        or isinstance(thresholds.get("binding_version"), bool)
        or not isinstance(thresholds.get("binding_version"), int)
        or thresholds["binding_version"] < 1
        or thresholds.get("status") != "OWNER_APPROVED_BOUND_REFERENCE"
        or thresholds.get("semantic_scope") != request
    ):
        return "DENY_OWNER_BOUND_EVIDENCE_THRESHOLDS_MISSING_OR_MISMATCH"
    threshold_integer_fields = (
        "minimum_raw_sample_size",
        "minimum_cluster_sample_size",
        "minimum_effective_sample_size",
    )
    minimum_windows = thresholds.get("minimum_window_observations")
    required_provenance = thresholds.get("required_provenance_refs")
    if (
        any(
            isinstance(thresholds.get(field), bool)
            or not isinstance(thresholds.get(field), int)
            or thresholds[field] < 1
            for field in threshold_integer_fields
        )
        or not isinstance(minimum_windows, dict)
        or set(minimum_windows)
        != {"ROLLING_RECENT", "STRESS_ARCHIVE", "FORWARD_CONFIRMATION"}
        or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 1
            for value in minimum_windows.values()
        )
        or not isinstance(required_provenance, list)
        or not required_provenance
        or any(
            not isinstance(item, str)
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{2,255}", item)
            is None
            for item in required_provenance
        )
        or len(required_provenance) != len(set(required_provenance))
        or not (
            thresholds["minimum_effective_sample_size"]
            <= thresholds["minimum_cluster_sample_size"]
            <= thresholds["minimum_raw_sample_size"]
        )
    ):
        return "DENY_OWNER_BOUND_EVIDENCE_THRESHOLDS_MISSING_OR_MISMATCH"
    manifest = _parse_json_bytes_strict(manifest_bytes)
    required = {
        "manifest_id",
        "manifest_version",
        "status",
        "issuer_ref",
        "as_of",
        "expires_at",
        "semantic_scope",
        "censored_outcomes_retained",
        "unknown_outcomes_retained",
        "competing_risks",
        "tail_quantile_ppm",
        "one_sided_confidence_level_ppm",
        "estimator_id",
        "clustering_rule_id",
        "raw_sample_size",
        "cluster_sample_size",
        "effective_sample_size",
        "sealed_windows",
        "holdout_access_history",
        "holdout_tuning_allowed",
        "provenance_refs",
        "drift_status",
        "owner_bound_thresholds_id",
        "owner_bound_thresholds_version",
        "owner_bound_thresholds_sha256",
    }
    if not isinstance(manifest, dict) or set(manifest) != required:
        return "DENY_INCOMPLETE_VERIFIED_EVIDENCE"
    identity_strings = ("manifest_id", "issuer_ref", "estimator_id", "clustering_rule_id")
    if any(
        not isinstance(manifest.get(field), str) or not manifest[field].strip()
        for field in identity_strings
    ):
        return "DENY_INCOMPLETE_VERIFIED_EVIDENCE"
    if (
        isinstance(manifest.get("manifest_version"), bool)
        or not isinstance(manifest.get("manifest_version"), int)
        or manifest["manifest_version"] < 1
        or manifest.get("status") != "VERIFIED_CURRENT"
        or manifest.get("semantic_scope") != request
        or manifest.get("censored_outcomes_retained") is not True
        or manifest.get("unknown_outcomes_retained") is not True
        or manifest.get("competing_risks") != ["CANCELLED", "FILLED", "LATE_FILL"]
        or manifest.get("holdout_tuning_allowed") is not False
        or manifest.get("drift_status") != "PASS"
        or not isinstance(manifest.get("owner_bound_thresholds_id"), str)
        or manifest.get("owner_bound_thresholds_id") != thresholds["binding_id"]
        or isinstance(manifest.get("owner_bound_thresholds_version"), bool)
        or not isinstance(manifest.get("owner_bound_thresholds_version"), int)
        or manifest.get("owner_bound_thresholds_version")
        != thresholds["binding_version"]
        or not isinstance(manifest.get("owner_bound_thresholds_sha256"), str)
        or manifest.get("owner_bound_thresholds_sha256")
        != owner_bound_thresholds_sha256
    ):
        return "DENY_INCOMPLETE_VERIFIED_EVIDENCE"
    integer_fields = (
        "tail_quantile_ppm",
        "one_sided_confidence_level_ppm",
        "raw_sample_size",
        "cluster_sample_size",
        "effective_sample_size",
    )
    if any(
        isinstance(manifest.get(field), bool)
        or not isinstance(manifest.get(field), int)
        or manifest[field] < 1
        for field in integer_fields
    ):
        return "DENY_EVIDENCE_TYPE_OR_SAMPLE_INVALID"
    if (
        manifest["tail_quantile_ppm"] > 1_000_000
        or manifest["one_sided_confidence_level_ppm"] > 1_000_000
        or not (
            manifest["effective_sample_size"]
            <= manifest["cluster_sample_size"]
            <= manifest["raw_sample_size"]
        )
    ):
        return "DENY_EVIDENCE_TYPE_OR_SAMPLE_INVALID"
    if any(
        manifest[actual] < thresholds[minimum]
        for actual, minimum in (
            ("raw_sample_size", "minimum_raw_sample_size"),
            ("cluster_sample_size", "minimum_cluster_sample_size"),
            ("effective_sample_size", "minimum_effective_sample_size"),
        )
    ):
        return "DENY_EVIDENCE_BELOW_OWNER_BOUND_MINIMUM"
    now = _parse_strict_utc(now_utc)
    as_of = _parse_strict_utc(manifest.get("as_of"))
    expires = _parse_strict_utc(manifest.get("expires_at"))
    if None in (now, as_of, expires) or not (as_of <= now < expires):
        return "DENY_EVIDENCE_STALE_OR_CAUSALLY_INVALID"
    windows = manifest.get("sealed_windows")
    if (
        not isinstance(windows, dict)
        or set(windows) != {"ROLLING_RECENT", "STRESS_ARCHIVE", "FORWARD_CONFIRMATION"}
    ):
        return "DENY_UNSEALED_OR_MISSING_EVIDENCE_WINDOW"
    for window_name, window in windows.items():
        sealed_at = (
            _parse_strict_utc(window.get("sealed_at"))
            if isinstance(window, dict)
            else None
        )
        if (
            not isinstance(window, dict)
            or set(window) != {"dataset_sha256", "sealed_at", "observations", "sealed"}
            or not isinstance(window.get("dataset_sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", window["dataset_sha256"]) is None
            or sealed_at is None
            or isinstance(window.get("observations"), bool)
            or not isinstance(window.get("observations"), int)
            or window["observations"] < 1
            or window.get("sealed") is not True
        ):
            return "DENY_UNSEALED_OR_MISSING_EVIDENCE_WINDOW"
        if sealed_at > now or sealed_at > as_of or sealed_at > expires:
            return "DENY_EVIDENCE_WINDOW_CAUSALLY_INVALID"
        if window["observations"] < minimum_windows[window_name]:
            return "DENY_EVIDENCE_BELOW_OWNER_BOUND_MINIMUM"
    history = manifest.get("holdout_access_history")
    provenance = manifest.get("provenance_refs")
    if (
        not isinstance(history, list)
        or not history
        or any(
            not isinstance(item, dict)
            or set(item) != {"accessed_at", "actor_ref", "purpose"}
            or _parse_strict_utc(item.get("accessed_at")) is None
            or not isinstance(item.get("actor_ref"), str)
            or not item["actor_ref"].strip()
            or not isinstance(item.get("purpose"), str)
            or item["purpose"] not in HOLDOUT_ACCESS_PURPOSES
            for item in history
        )
        or not isinstance(provenance, list)
        or provenance != required_provenance
    ):
        return "DENY_HOLDOUT_HISTORY_OR_PROVENANCE_MISSING"
    for item in history:
        accessed_at = _parse_strict_utc(item["accessed_at"])
        if accessed_at is None or accessed_at > as_of or accessed_at > now:
            return "DENY_HOLDOUT_ACCESS_CAUSALLY_INVALID"
    return "NON_AUTHORIZING_DECLARED_EVIDENCE_SHAPE_CAUSALITY_VALID"


def validity_active_runtime_contract_result(
    request: object,
    *,
    schema_bytes: object,
    capability_bytes: object,
    capability_sha256: object,
    policy_bytes: object,
    policy_sha256: object,
    evidence_bytes: object,
    evidence_sha256: object,
    owner_bound_thresholds_bytes: object,
    owner_bound_thresholds_sha256: object,
    now_utc: object,
) -> str:
    """Exercise future bindings, then fail because no runtime trust root exists."""
    schema = _parse_json_bytes_strict(schema_bytes)
    if (
        not isinstance(schema_bytes, bytes)
        or not isinstance(schema, dict)
        or schema.get("$id")
        == "https://tradebot.local/schemas/non-authorizing-validity-profile-draft-v1.json"
    ):
        return ACTIVE_SCHEMA_UNAVAILABLE
    for result in (
        validity_artifact_scope_result(
            request,
            capability_bytes,
            expected_kind="VENUE_CAPABILITY",
            expected_sha256=capability_sha256,
            now_utc=now_utc,
        ),
        validity_artifact_scope_result(
            request,
            policy_bytes,
            expected_kind="RISK_POLICY",
            expected_sha256=policy_sha256,
            now_utc=now_utc,
        ),
        validity_evidence_manifest_result(
            request,
            evidence_bytes,
            expected_sha256=evidence_sha256,
            now_utc=now_utc,
            owner_bound_thresholds_bytes=owner_bound_thresholds_bytes,
            owner_bound_thresholds_sha256=owner_bound_thresholds_sha256,
        ),
    ):
        if not result.startswith("NON_AUTHORIZING_"):
            return result
    return ACTIVE_SCHEMA_UNAVAILABLE


B4_CANONICAL_PAYLOAD_FIELDS = (
    "action_id",
    "action_class",
    "risk_class",
    "approval_tier",
    "owner_epoch",
    "profile_id",
    "previous_profile_sha256",
    "new_profile_sha256",
    "previous_configuration_sha256",
    "new_configuration_sha256",
    "previous_operating_manifest_sha256",
    "effective_from",
    "expires_at",
    "commit_at",
    "owner_selected_activation_window_ms",
    "level_b_signature_id",
    "second_factor_id",
)

B4_DURABLE_RECORD_FIELDS = {
    "action_id",
    "owner_epoch",
    "parent_profile_sha256",
    "parent_operating_manifest_sha256",
    "child_profile_sha256",
    "child_configuration_sha256",
    "canonical_action_payload_sha256",
    "previous_sequence",
    "sequence",
    "cas_token_sha256",
    "consumed_at",
    "state",
    "atomic_parent_consumption",
    "parent_profile_invalidated",
    "parent_operating_manifest_invalidated",
}

B4_GLOBAL_REGISTRY_ID = "validity-profile-authority-global-v1"
B4_GLOBAL_REGISTRY_SCOPE = "GLOBAL_ACROSS_OWNER_EPOCHS"
B4_GLOBAL_REGISTRY_GENESIS_OWNER_EPOCH = 0
B4_GLOBAL_REGISTRY_GENESIS_SHA256 = (
    "00d45207979fc16245c40b9c850d7cad99b664e4678a2f100350ebae15705c34"
)


def _b4_registry_shape_details(
    durable_registry: object,
) -> tuple[str, list[dict]]:
    """Validate caller-supplied registry structure without trusting its state."""
    registry_required = {
        "registry_id",
        "registry_scope",
        "genesis_owner_epoch",
        "genesis_sha256",
        "latest_owner_epoch",
        "durable",
        "append_only",
        "history_complete",
        "base_sequence",
        "latest_sequence",
        "records",
    }
    if (
        not isinstance(durable_registry, dict)
        or set(durable_registry) != registry_required
        or durable_registry.get("registry_id") != B4_GLOBAL_REGISTRY_ID
        or durable_registry.get("registry_scope")
        != B4_GLOBAL_REGISTRY_SCOPE
        or durable_registry.get("genesis_owner_epoch")
        != B4_GLOBAL_REGISTRY_GENESIS_OWNER_EPOCH
        or durable_registry.get("genesis_sha256")
        != B4_GLOBAL_REGISTRY_GENESIS_SHA256
        or isinstance(durable_registry.get("genesis_owner_epoch"), bool)
        or not isinstance(durable_registry.get("genesis_owner_epoch"), int)
        or isinstance(durable_registry.get("latest_owner_epoch"), bool)
        or not isinstance(durable_registry.get("latest_owner_epoch"), int)
        or durable_registry["latest_owner_epoch"] < 0
        or durable_registry.get("durable") is not True
        or durable_registry.get("append_only") is not True
        or durable_registry.get("history_complete") is not True
        or isinstance(durable_registry.get("base_sequence"), bool)
        or not isinstance(durable_registry.get("base_sequence"), int)
        or durable_registry["base_sequence"] != 0
        or isinstance(durable_registry.get("latest_sequence"), bool)
        or not isinstance(durable_registry.get("latest_sequence"), int)
        or durable_registry["latest_sequence"] < durable_registry["base_sequence"]
        or not isinstance(durable_registry.get("records"), list)
    ):
        return "DENY_B4_DURABLE_REGISTRY_PROOF_INVALID", []
    records = durable_registry["records"]
    if not records and durable_registry["latest_owner_epoch"] != 0:
        return "DENY_B4_DURABLE_REGISTRY_PROOF_INVALID", []
    expected_sequence = 1
    seen_actions: set[str] = set()
    seen_parents: set[tuple[str, str]] = set()
    seen_parent_profiles: set[str] = set()
    seen_parent_manifests: set[str] = set()
    seen_cas_tokens: set[str] = set()
    previous_record_owner_epoch = B4_GLOBAL_REGISTRY_GENESIS_OWNER_EPOCH
    for record in records:
        if not isinstance(record, dict) or set(record) != B4_DURABLE_RECORD_FIELDS:
            return "DENY_B4_DURABLE_REGISTRY_PROOF_INVALID", []
        record_hash_fields = (
            "parent_profile_sha256",
            "parent_operating_manifest_sha256",
            "child_profile_sha256",
            "child_configuration_sha256",
            "canonical_action_payload_sha256",
            "cas_token_sha256",
        )
        if (
            not isinstance(record.get("action_id"), str)
            or not record["action_id"].strip()
            or isinstance(record.get("owner_epoch"), bool)
            or not isinstance(record.get("owner_epoch"), int)
            or record["owner_epoch"] < 1
            or record["owner_epoch"] < previous_record_owner_epoch
            or record["owner_epoch"] > durable_registry["latest_owner_epoch"]
            or any(
                not isinstance(record.get(field), str)
                or re.fullmatch(r"[0-9a-f]{64}", record[field]) is None
                for field in record_hash_fields
            )
            or isinstance(record.get("previous_sequence"), bool)
            or not isinstance(record.get("previous_sequence"), int)
            or isinstance(record.get("sequence"), bool)
            or not isinstance(record.get("sequence"), int)
            or record["previous_sequence"] != expected_sequence - 1
            or record["sequence"] != expected_sequence
            or record.get("state") != "CONSUMED_AND_PARENTS_INVALIDATED"
            or record.get("atomic_parent_consumption") is not True
            or record.get("parent_profile_invalidated") is not True
            or record.get("parent_operating_manifest_invalidated") is not True
            or _parse_strict_utc(record.get("consumed_at")) is None
        ):
            return "DENY_B4_DURABLE_REGISTRY_PROOF_INVALID", []
        parent_key = (
            record["parent_profile_sha256"],
            record["parent_operating_manifest_sha256"],
        )
        if (
            record["action_id"] in seen_actions
            or parent_key in seen_parents
            or record["parent_profile_sha256"] in seen_parent_profiles
            or record["parent_operating_manifest_sha256"]
            in seen_parent_manifests
            or record["cas_token_sha256"] in seen_cas_tokens
        ):
            return "DENY_B4_DURABLE_REGISTRY_PROOF_INVALID", []
        seen_actions.add(record["action_id"])
        seen_parents.add(parent_key)
        seen_parent_profiles.add(record["parent_profile_sha256"])
        seen_parent_manifests.add(
            record["parent_operating_manifest_sha256"]
        )
        seen_cas_tokens.add(record["cas_token_sha256"])
        previous_record_owner_epoch = record["owner_epoch"]
        expected_sequence += 1
    if (
        durable_registry["latest_sequence"] != expected_sequence - 1
        or (
            records
            and durable_registry["latest_owner_epoch"]
            != records[-1]["owner_epoch"]
        )
    ):
        return "DENY_B4_DURABLE_REGISTRY_PROOF_INVALID", []
    return "NON_AUTHORIZING_B4_REGISTRY_SHAPE_VALID", records


def validity_profile_b4_registry_shape_result(
    durable_registry: object,
) -> str:
    """Return registry shape only; never readiness, freshness, or persistence."""
    result, _ = _b4_registry_shape_details(durable_registry)
    return result


def validity_profile_authority_change_result(
    change: object,
    durable_registry: object,
    *,
    prior_operating_manifest_bytes: object = None,
    prior_operating_manifest_record: object = None,
) -> str:
    """Fail closed without an independently trusted current registry checkpoint."""
    required = set(B4_CANONICAL_PAYLOAD_FIELDS) | {
        "level_b_signature_verified",
        "second_factor_verified",
        "canonical_action_payload_sha256",
        "consumption_state",
        "durable_consumed_at",
        "invalidated_profile_sha256",
        "invalidated_operating_manifest_sha256",
        "new_operating_manifest_ref",
    }
    if (
        not isinstance(change, dict)
        or set(change) != required
    ):
        return "DENY_MALFORMED_B4_AUTHORITY_CHANGE"
    if (
        change.get("action_class") != "VALIDITY_PROFILE_AUTHORITY_CHANGE"
        or change.get("risk_class") != "B4_AUTHORITY_MUTATION"
        or change.get("approval_tier") != "LEVEL_B"
        or change.get("level_b_signature_verified") is not True
        or change.get("second_factor_verified") is not True
        or not isinstance(change.get("level_b_signature_id"), str)
        or not change["level_b_signature_id"].strip()
        or not isinstance(change.get("second_factor_id"), str)
        or not change["second_factor_id"].strip()
        or change["level_b_signature_id"] == change["second_factor_id"]
    ):
        return "DENY_B4_LEVEL_B_OR_INDEPENDENT_FACTOR_INVALID"
    identity_fields = ("action_id", "profile_id")
    if any(
        not isinstance(change.get(field), str) or not change[field].strip()
        for field in identity_fields
    ):
        return "DENY_MALFORMED_B4_AUTHORITY_CHANGE"
    hashes = (
        "previous_profile_sha256",
        "new_profile_sha256",
        "previous_configuration_sha256",
        "new_configuration_sha256",
        "previous_operating_manifest_sha256",
        "invalidated_profile_sha256",
        "invalidated_operating_manifest_sha256",
        "canonical_action_payload_sha256",
    )
    if any(
        not isinstance(change.get(field), str)
        or re.fullmatch(r"[0-9a-f]{64}", change[field]) is None
        for field in hashes
    ):
        return "DENY_MALFORMED_B4_AUTHORITY_CHANGE"
    if (
        change["new_profile_sha256"] == change["previous_profile_sha256"]
        or change["new_configuration_sha256"]
        == change["previous_configuration_sha256"]
        or change["invalidated_profile_sha256"] != change["previous_profile_sha256"]
        or change["invalidated_operating_manifest_sha256"]
        != change["previous_operating_manifest_sha256"]
        or change.get("new_operating_manifest_ref")
        != "PENDING_SEPARATE_OPERATING_MANIFEST"
    ):
        return "DENY_B4_HASH_ROTATION_OR_INVALIDATION_PROOF_MISMATCH"
    if (
        _previous_configuration_binding_result(
            change,
            prior_operating_manifest_bytes,
            prior_operating_manifest_record,
        )
        != "NON_AUTHORIZING_PREVIOUS_CONFIGURATION_BINDING_SHAPE_VALID"
    ):
        return "DENY_B4_PREVIOUS_CONFIGURATION_BINDING_INVALID"
    if (
        isinstance(change.get("owner_epoch"), bool)
        or not isinstance(change.get("owner_epoch"), int)
        or change["owner_epoch"] < 1
    ):
        return "DENY_MALFORMED_B4_AUTHORITY_CHANGE"
    window = change.get("owner_selected_activation_window_ms")
    effective = _parse_strict_utc(change.get("effective_from"))
    expires = _parse_strict_utc(change.get("expires_at"))
    commit = _parse_strict_utc(change.get("commit_at"))
    if not _strict_positive_duration(window) or None in (effective, expires, commit):
        return "DENY_B4_WINDOW_OR_TIMESTAMP_INVALID"
    try:
        expected_expiry = effective + timedelta(milliseconds=window)
    except (OverflowError, TypeError):
        return "DENY_DURATION_ARITHMETIC_OVERFLOW"
    if expires != expected_expiry or not (effective <= commit < expires):
        return (
            "DENY_COMMIT_BEFORE_EFFECTIVE_FROM"
            if commit < effective
            else "DENY_B4_WINDOW_OR_TIMESTAMP_INVALID"
        )
    payload = {field: change[field] for field in B4_CANONICAL_PAYLOAD_FIELDS}
    if canonical_json_digest(payload) != change["canonical_action_payload_sha256"]:
        return "DENY_B4_CANONICAL_PAYLOAD_MISMATCH"
    registry_shape_result, records = _b4_registry_shape_details(durable_registry)
    if registry_shape_result != "NON_AUTHORIZING_B4_REGISTRY_SHAPE_VALID":
        return registry_shape_result
    action_records = [
        record for record in records if record["action_id"] == change["action_id"]
    ]
    parent_key = (
        change["previous_profile_sha256"],
        change["previous_operating_manifest_sha256"],
    )
    parent_records = [
        record
        for record in records
        if (
            record["parent_profile_sha256"],
            record["parent_operating_manifest_sha256"],
        )
        == parent_key
    ]
    parent_component_records = [
        record
        for record in records
        if (
            record["parent_profile_sha256"]
            == change["previous_profile_sha256"]
            or record["parent_operating_manifest_sha256"]
            == change["previous_operating_manifest_sha256"]
        )
    ]
    if change.get("consumption_state") == "PROPOSED":
        if change["owner_epoch"] < durable_registry["latest_owner_epoch"]:
            return "DENY_B4_DURABLE_REGISTRY_PROOF_INVALID"
        if action_records:
            return "DENY_B4_SINGLE_USE_REPLAY"
        if parent_component_records:
            return "DENY_B4_PARENT_ALREADY_CONSUMED"
        if change.get("durable_consumed_at") is not None:
            return "DENY_B4_DURABLE_REGISTRY_PROOF_INVALID"
        return "DENY_B4_CURRENT_REGISTRY_CHECKPOINT_OR_RUNTIME_TRUST_UNAVAILABLE"
    if change.get("consumption_state") != "CONSUMED":
        return "DENY_B4_DURABLE_REGISTRY_PROOF_INVALID"
    consumed_at = _parse_strict_utc(change.get("durable_consumed_at"))
    if (
        consumed_at is None
        or consumed_at < commit
        or consumed_at >= expires
        or len(action_records) != 1
        or action_records != parent_records
        or action_records != parent_component_records
        or action_records[0]["owner_epoch"] != change["owner_epoch"]
        or action_records[0]["child_profile_sha256"]
        != change["new_profile_sha256"]
        or action_records[0]["child_configuration_sha256"]
        != change["new_configuration_sha256"]
        or action_records[0]["canonical_action_payload_sha256"]
        != change["canonical_action_payload_sha256"]
        or _parse_strict_utc(action_records[0]["consumed_at"]) != consumed_at
    ):
        return "DENY_B4_DURABLE_REGISTRY_PROOF_INVALID"
    return "DENY_B4_CURRENT_REGISTRY_CHECKPOINT_OR_RUNTIME_TRUST_UNAVAILABLE"


OPERATING_MANIFEST_FIELDS = {
    "manifest_ref",
    "manifest_version",
    "manifest_sequence",
    "supersedes_ref",
    "supersedes_version",
    "supersedes_sequence",
    "supersedes_sha256",
    "change_action_id",
    "change_payload_sha256",
    "profile_sha256",
    "configuration_sha256",
    "effective_from",
    "expires_at",
    "status",
}

LEGACY_OPERATING_MANIFEST_FIELDS = (
    OPERATING_MANIFEST_FIELDS
    - {
        "supersedes_ref",
        "supersedes_version",
        "supersedes_sequence",
        "supersedes_sha256",
    }
)

OPERATING_MANIFEST_REGISTRY_RECORD_FIELDS = {
    "manifest_ref",
    "manifest_version",
    "manifest_sequence",
    "manifest_sha256",
    "manifest_bytes",
}


def _canonical_versioned_manifest_ref(
    reference: object,
    version: object,
) -> bool:
    if (
        not isinstance(reference, str)
        or not reference
        or isinstance(version, bool)
        or not isinstance(version, int)
        or version < 1
    ):
        return False
    pure = PurePosixPath(reference)
    return (
        not pure.is_absolute()
        and reference == pure.as_posix()
        and "." not in pure.parts
        and ".." not in pure.parts
        and re.fullmatch(
            r"[a-z0-9][a-z0-9._/-]*-v[1-9][0-9]*\.json",
            reference,
        )
        is not None
        and reference.endswith(f"-v{version}.json")
    )


def _operating_manifest_payload_shape_valid(
    manifest: object,
    *,
    allow_legacy: bool,
) -> bool:
    if not isinstance(manifest, dict):
        return False
    fields = set(manifest)
    if fields != OPERATING_MANIFEST_FIELDS and (
        not allow_legacy or fields != LEGACY_OPERATING_MANIFEST_FIELDS
    ):
        return False
    if (
        not _canonical_versioned_manifest_ref(
            manifest.get("manifest_ref"),
            manifest.get("manifest_version"),
        )
        or isinstance(manifest.get("manifest_sequence"), bool)
        or not isinstance(manifest.get("manifest_sequence"), int)
        or manifest["manifest_sequence"] < 1
        or not isinstance(manifest.get("change_action_id"), str)
        or not manifest["change_action_id"]
        or any(
            not isinstance(manifest.get(field), str)
            or re.fullmatch(r"[0-9a-f]{64}", manifest[field]) is None
            for field in (
                "change_payload_sha256",
                "profile_sha256",
                "configuration_sha256",
            )
        )
        or manifest.get("status")
        != "SEPARATELY_APPROVED_NON_AUTHORIZING_SHAPE"
    ):
        return False
    effective = _parse_strict_utc(manifest.get("effective_from"))
    expires = _parse_strict_utc(manifest.get("expires_at"))
    if effective is None or expires is None or not effective < expires:
        return False
    if fields == OPERATING_MANIFEST_FIELDS and (
        not _canonical_versioned_manifest_ref(
            manifest.get("supersedes_ref"),
            manifest.get("supersedes_version"),
        )
        or isinstance(manifest.get("supersedes_sequence"), bool)
        or not isinstance(manifest.get("supersedes_sequence"), int)
        or manifest["supersedes_sequence"] < 1
        or not isinstance(manifest.get("supersedes_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", manifest["supersedes_sha256"])
        is None
    ):
        return False
    return True


def _previous_configuration_binding_result(
    change: object,
    prior_manifest_bytes: object,
    prior_manifest_record: object,
) -> str:
    """Derive the previous configuration from exact prior-manifest bytes."""
    if (
        not isinstance(change, dict)
        or not isinstance(prior_manifest_bytes, bytes)
        or not isinstance(prior_manifest_record, dict)
        or set(prior_manifest_record)
        != OPERATING_MANIFEST_REGISTRY_RECORD_FIELDS
        or prior_manifest_record.get("manifest_bytes") != prior_manifest_bytes
        or prior_manifest_record.get("manifest_sha256")
        != change.get("previous_operating_manifest_sha256")
        or hashlib.sha256(prior_manifest_bytes).hexdigest()
        != change.get("previous_operating_manifest_sha256")
        or canonical_json_bytes_result(prior_manifest_bytes)
        != "NON_AUTHORIZING_CANONICAL_JSON_SHAPE_VALID"
    ):
        return "DENY_B4_PREVIOUS_CONFIGURATION_BINDING_INVALID"
    prior_manifest = _parse_json_bytes_strict(prior_manifest_bytes)
    if (
        not _operating_manifest_payload_shape_valid(
            prior_manifest,
            allow_legacy=True,
        )
        or prior_manifest_record.get("manifest_ref")
        != prior_manifest.get("manifest_ref")
        or prior_manifest_record.get("manifest_version")
        != prior_manifest.get("manifest_version")
        or prior_manifest_record.get("manifest_sequence")
        != prior_manifest.get("manifest_sequence")
        or prior_manifest.get("configuration_sha256")
        != change.get("previous_configuration_sha256")
    ):
        return "DENY_B4_PREVIOUS_CONFIGURATION_BINDING_INVALID"
    return "NON_AUTHORIZING_PREVIOUS_CONFIGURATION_BINDING_SHAPE_VALID"


def validity_profile_operating_manifest_result(
    change: object,
    operating_manifest_bytes: object,
    *,
    manifest_sha256: object,
    prior_manifest_bytes: object,
    prior_manifest_sha256: object,
    manifest_registry: object,
) -> str:
    if (
        not isinstance(change, dict)
        or not isinstance(operating_manifest_bytes, bytes)
        or not isinstance(manifest_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", manifest_sha256) is None
        or hashlib.sha256(operating_manifest_bytes).hexdigest() != manifest_sha256
        or canonical_json_bytes_result(operating_manifest_bytes)
        != "NON_AUTHORIZING_CANONICAL_JSON_SHAPE_VALID"
    ):
        return "DENY_MALFORMED_OPERATING_MANIFEST"
    if manifest_sha256 == change.get("previous_operating_manifest_sha256"):
        return "DENY_OLD_OPERATING_MANIFEST_REUSE"
    operating_manifest = _parse_json_bytes_strict(operating_manifest_bytes)
    if (
        not isinstance(operating_manifest, dict)
        or set(operating_manifest) != OPERATING_MANIFEST_FIELDS
    ):
        return "DENY_MALFORMED_OPERATING_MANIFEST"
    reference = operating_manifest.get("manifest_ref")
    version = operating_manifest.get("manifest_version")
    sequence = operating_manifest.get("manifest_sequence")
    if (
        not _canonical_versioned_manifest_ref(reference, version)
        or isinstance(sequence, bool)
        or not isinstance(sequence, int)
        or sequence < 1
        or not _canonical_versioned_manifest_ref(
            operating_manifest.get("supersedes_ref"),
            operating_manifest.get("supersedes_version"),
        )
        or isinstance(operating_manifest.get("supersedes_sequence"), bool)
        or not isinstance(operating_manifest.get("supersedes_sequence"), int)
        or operating_manifest["supersedes_sequence"] < 1
    ):
        return "DENY_MALFORMED_OPERATING_MANIFEST"
    hash_fields = (
        "supersedes_sha256",
        "change_payload_sha256",
        "profile_sha256",
        "configuration_sha256",
    )
    if any(
        not isinstance(operating_manifest.get(field), str)
        or re.fullmatch(r"[0-9a-f]{64}", operating_manifest[field]) is None
        for field in hash_fields
    ):
        return "DENY_MALFORMED_OPERATING_MANIFEST"
    if (
        operating_manifest.get("profile_sha256")
        == change.get("previous_profile_sha256")
    ):
        return "DENY_OLD_OPERATING_MANIFEST_REUSE"
    registry_required = {
        "trusted",
        "complete",
        "append_only",
        "latest_sequence",
        "records",
    }
    if (
        not isinstance(prior_manifest_bytes, bytes)
        or not isinstance(prior_manifest_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", prior_manifest_sha256) is None
        or hashlib.sha256(prior_manifest_bytes).hexdigest()
        != prior_manifest_sha256
        or canonical_json_bytes_result(prior_manifest_bytes)
        != "NON_AUTHORIZING_CANONICAL_JSON_SHAPE_VALID"
        or prior_manifest_sha256
        != change.get("previous_operating_manifest_sha256")
        or not isinstance(manifest_registry, dict)
        or set(manifest_registry) != registry_required
        or manifest_registry.get("trusted") is not True
        or manifest_registry.get("complete") is not True
        or manifest_registry.get("append_only") is not True
        or isinstance(manifest_registry.get("latest_sequence"), bool)
        or not isinstance(manifest_registry.get("latest_sequence"), int)
        or manifest_registry["latest_sequence"] < 1
        or not isinstance(manifest_registry.get("records"), list)
    ):
        return "DENY_OPERATING_MANIFEST_REGISTRY_OR_PRIOR_INVALID"
    prior_manifest = _parse_json_bytes_strict(prior_manifest_bytes)
    if (
        not _operating_manifest_payload_shape_valid(
            prior_manifest,
            allow_legacy=True,
        )
    ):
        return "DENY_OPERATING_MANIFEST_REGISTRY_OR_PRIOR_INVALID"
    identity_digests: dict[tuple[str, int, int], str] = {}
    expected_sequence = 1
    prior_records: list[dict] = []
    previous_record_manifest: dict | None = None
    for record in manifest_registry["records"]:
        if (
            not isinstance(record, dict)
            or set(record) != OPERATING_MANIFEST_REGISTRY_RECORD_FIELDS
            or not _canonical_versioned_manifest_ref(
                record.get("manifest_ref"),
                record.get("manifest_version"),
            )
            or isinstance(record.get("manifest_sequence"), bool)
            or not isinstance(record.get("manifest_sequence"), int)
            or record["manifest_sequence"] < 1
            or not isinstance(record.get("manifest_sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", record["manifest_sha256"])
            is None
            or not isinstance(record.get("manifest_bytes"), bytes)
            or hashlib.sha256(record["manifest_bytes"]).hexdigest()
            != record["manifest_sha256"]
            or canonical_json_bytes_result(record["manifest_bytes"])
            != "NON_AUTHORIZING_CANONICAL_JSON_SHAPE_VALID"
        ):
            return "DENY_OPERATING_MANIFEST_REGISTRY_OR_PRIOR_INVALID"
        record_manifest = _parse_json_bytes_strict(record["manifest_bytes"])
        if (
            not _operating_manifest_payload_shape_valid(
                record_manifest,
                allow_legacy=True,
            )
            or record_manifest.get("manifest_ref")
            != record["manifest_ref"]
            or record_manifest.get("manifest_version")
            != record["manifest_version"]
            or record_manifest.get("manifest_sequence")
            != record["manifest_sequence"]
        ):
            return "DENY_OPERATING_MANIFEST_REGISTRY_OR_PRIOR_INVALID"
        identity = (
            record["manifest_ref"],
            record["manifest_version"],
            record["manifest_sequence"],
        )
        if identity in identity_digests:
            if identity_digests[identity] != record["manifest_sha256"]:
                return "DENY_OPERATING_MANIFEST_IDENTITY_DIGEST_CONFLICT"
            return "DENY_OPERATING_MANIFEST_SEQUENCE_REPLAY"
        identity_digests[identity] = record["manifest_sha256"]
        if record["manifest_sequence"] != expected_sequence:
            return "DENY_OPERATING_MANIFEST_REGISTRY_OR_PRIOR_INVALID"
        if record["manifest_sequence"] == 1:
            if (
                set(record_manifest) != LEGACY_OPERATING_MANIFEST_FIELDS
                or record["manifest_version"] != 1
            ):
                return "DENY_OPERATING_MANIFEST_REGISTRY_OR_PRIOR_INVALID"
        elif (
            previous_record_manifest is None
            or set(record_manifest) != OPERATING_MANIFEST_FIELDS
            or record["manifest_version"]
            != previous_record_manifest["manifest_version"] + 1
            or record_manifest.get("supersedes_ref")
            != previous_record_manifest["manifest_ref"]
            or record_manifest.get("supersedes_version")
            != previous_record_manifest["manifest_version"]
            or record_manifest.get("supersedes_sequence")
            != previous_record_manifest["manifest_sequence"]
            or record_manifest.get("supersedes_sha256")
            != identity_digests[
                (
                    previous_record_manifest["manifest_ref"],
                    previous_record_manifest["manifest_version"],
                    previous_record_manifest["manifest_sequence"],
                )
            ]
        ):
            return "DENY_OPERATING_MANIFEST_REGISTRY_OR_PRIOR_INVALID"
        previous_record_manifest = record_manifest
        expected_sequence += 1
        if (
            record["manifest_sha256"] == prior_manifest_sha256
            and record["manifest_bytes"] == prior_manifest_bytes
        ):
            prior_records.append(record)
    if (
        manifest_registry["latest_sequence"] != expected_sequence - 1
        or len(manifest_registry["records"])
        != manifest_registry["latest_sequence"]
        or len(prior_records) != 1
    ):
        return "DENY_OPERATING_MANIFEST_REGISTRY_OR_PRIOR_INVALID"
    prior_identity = (
        prior_manifest["manifest_ref"],
        prior_manifest["manifest_version"],
        prior_manifest["manifest_sequence"],
    )
    prior_record = prior_records[0]
    if (
        prior_identity
        != (
            prior_record["manifest_ref"],
            prior_record["manifest_version"],
            prior_record["manifest_sequence"],
        )
        or prior_manifest["manifest_sequence"]
        != manifest_registry["latest_sequence"]
    ):
        return "DENY_OPERATING_MANIFEST_REGISTRY_OR_PRIOR_INVALID"
    if (
        _previous_configuration_binding_result(
            change,
            prior_manifest_bytes,
            prior_record,
        )
        != "NON_AUTHORIZING_PREVIOUS_CONFIGURATION_BINDING_SHAPE_VALID"
    ):
        return "DENY_B4_PREVIOUS_CONFIGURATION_BINDING_INVALID"
    if (
        change.get("new_configuration_sha256")
        == change.get("previous_configuration_sha256")
        or operating_manifest.get("configuration_sha256")
        == prior_manifest.get("configuration_sha256")
    ):
        return "DENY_OLD_CONFIGURATION_REUSE"
    candidate_identity = (reference, version, sequence)
    if candidate_identity in identity_digests:
        if identity_digests[candidate_identity] != manifest_sha256:
            return "DENY_OPERATING_MANIFEST_IDENTITY_DIGEST_CONFLICT"
        return "DENY_OPERATING_MANIFEST_SEQUENCE_REPLAY"
    if (
        sequence != manifest_registry["latest_sequence"] + 1
        or version != prior_manifest["manifest_version"] + 1
        or operating_manifest.get("supersedes_ref")
        != prior_manifest["manifest_ref"]
        or operating_manifest.get("supersedes_version")
        != prior_manifest["manifest_version"]
        or operating_manifest.get("supersedes_sequence")
        != prior_manifest["manifest_sequence"]
        or operating_manifest.get("supersedes_sha256")
        != prior_manifest_sha256
    ):
        return "DENY_OPERATING_MANIFEST_SUPERSESSION_OR_SEQUENCE_INVALID"
    effective = _parse_strict_utc(operating_manifest.get("effective_from"))
    expires = _parse_strict_utc(operating_manifest.get("expires_at"))
    consumed_at = _parse_strict_utc(change.get("durable_consumed_at"))
    if (
        change.get("consumption_state") != "CONSUMED"
        or consumed_at is None
        or effective is None
        or expires is None
        or not (consumed_at <= effective < expires)
        or not isinstance(operating_manifest.get("change_action_id"), str)
        or not operating_manifest["change_action_id"]
        or operating_manifest["change_action_id"] != change.get("action_id")
        or operating_manifest.get("change_payload_sha256")
        != change.get("canonical_action_payload_sha256")
        or operating_manifest.get("profile_sha256") != change.get("new_profile_sha256")
        or operating_manifest.get("configuration_sha256")
        != change.get("new_configuration_sha256")
        or operating_manifest.get("status")
        != "SEPARATELY_APPROVED_NON_AUTHORIZING_SHAPE"
    ):
        return "DENY_NEW_OPERATING_MANIFEST_BINDING_MISMATCH"
    return "NON_AUTHORIZING_NEW_OPERATING_MANIFEST_BINDING_SHAPE_VALID"


def validity_reconciliation_escalation_result(
    state: object,
    *,
    reconciliation_escalation_deadline_ms: object,
) -> str:
    required = {
        "first_durable_unknown_at",
        "escalation_due_at",
        "now_utc",
        "dispatch_at",
        "ack_at",
        "profile_state",
        "exposure_retained",
        "reservation_retained",
        "reconciliation_required",
        "authority_restored",
        "terminal_outcome_verified",
    }
    if (
        not isinstance(state, dict)
        or set(state) != required
        or not _strict_positive_duration(reconciliation_escalation_deadline_ms)
    ):
        return "DENY_MALFORMED_RECONCILIATION_ESCALATION"
    boolean_fields = (
        "exposure_retained",
        "reservation_retained",
        "reconciliation_required",
        "authority_restored",
        "terminal_outcome_verified",
    )
    if any(not isinstance(state.get(field), bool) for field in boolean_fields):
        return "DENY_MALFORMED_RECONCILIATION_ESCALATION"
    first = _parse_strict_utc(state.get("first_durable_unknown_at"))
    due = _parse_strict_utc(state.get("escalation_due_at"))
    now = _parse_strict_utc(state.get("now_utc"))
    dispatch = (
        None
        if state.get("dispatch_at") is None
        else _parse_strict_utc(state.get("dispatch_at"))
    )
    ack = None if state.get("ack_at") is None else _parse_strict_utc(state.get("ack_at"))
    if None in (first, due, now):
        return "DENY_MALFORMED_RECONCILIATION_ESCALATION"
    try:
        expected_due = first + timedelta(
            milliseconds=reconciliation_escalation_deadline_ms
        )
    except (OverflowError, TypeError):
        return "DENY_DURATION_ARITHMETIC_OVERFLOW"
    if due != expected_due:
        return "DENY_ESCALATION_DEADLINE_TIMESTAMP_MISMATCH"
    if (
        (state.get("dispatch_at") is not None and dispatch is None)
        or (state.get("ack_at") is not None and ack is None)
        or first > now
        or (dispatch is not None and dispatch < first)
        or (dispatch is not None and dispatch > now)
        or (ack is not None and (dispatch is None or ack < dispatch))
        or (ack is not None and ack > now)
    ):
        return "DENY_CAUSALLY_INVALID_ESCALATION_ORDER"
    if state["authority_restored"] is True:
        return "DENY_LATE_ACK_AUTHORITY_REBOUND"
    if state["terminal_outcome_verified"] is False and (
        state["exposure_retained"] is not True
        or state["reservation_retained"] is not True
        or state["reconciliation_required"] is not True
    ):
        return "DENY_ESCALATION_RELEASED_BLOCK_OR_RESERVATION"
    if now >= due and (dispatch is None or ack is None or ack > due):
        if state["profile_state"] not in {"SUSPENDED", "INVALIDATED"}:
            return "DENY_OVERDUE_ESCALATION_NOT_SUSPENDED_OR_INVALIDATED"
        return "NON_AUTHORIZING_SUSPEND_OR_INVALIDATE_RETAIN_BLOCK"
    if state["terminal_outcome_verified"] is True:
        return "NON_AUTHORIZING_VERIFIED_TERMINAL_RECONCILIATION_SHAPE"
    return "NON_AUTHORIZING_ESCALATION_ACK_RETAINS_BLOCK"


def validity_profile_sunset_result(state: object) -> str:
    required = {
        "mandatory_cutoffs",
        "cancel_reconciliation_buffer_ms",
        "computed_sunset_deadline",
        "order_id",
        "order_expiry_at",
        "now_utc",
        "revoked",
        "remaining_opening_or_conditional_orders",
        "unknown_or_possible_fills",
        "completion_proof",
    }
    proof_fields = {
        "terminal_order_outcomes_complete",
        "fill_trade_watermark_complete",
        "positions_reconciled",
        "balances_reconciled",
        "child_orders_reconciled",
        "reservation_proof_status",
    }
    if (
        not isinstance(state, dict)
        or set(state) != required
        or not isinstance(state.get("mandatory_cutoffs"), dict)
        or set(state["mandatory_cutoffs"])
        != MANDATORY_SUNSET_CUTOFF_FIELDS
        or not _strict_positive_duration(state.get("cancel_reconciliation_buffer_ms"))
        or not isinstance(state.get("order_id"), str)
        or not state["order_id"].strip()
        or not isinstance(state.get("revoked"), bool)
        or not isinstance(state.get("unknown_or_possible_fills"), bool)
        or isinstance(state.get("remaining_opening_or_conditional_orders"), bool)
        or not isinstance(state.get("remaining_opening_or_conditional_orders"), int)
        or state["remaining_opening_or_conditional_orders"] < 0
        or not isinstance(state.get("completion_proof"), dict)
        or set(state["completion_proof"]) != proof_fields
    ):
        return "DENY_MALFORMED_SUNSET_PROOF"
    now = _parse_strict_utc(state.get("now_utc"))
    claimed_deadline = _parse_strict_utc(state.get("computed_sunset_deadline"))
    order_expiry = _parse_strict_utc(state.get("order_expiry_at"))
    if None in (now, claimed_deadline, order_expiry):
        return "DENY_MALFORMED_SUNSET_PROOF"
    expected_deadline, cutoff_error = _mandatory_sunset_deadline(
        state["mandatory_cutoffs"],
        state["cancel_reconciliation_buffer_ms"],
    )
    if cutoff_error is not None or expected_deadline is None:
        return cutoff_error or "DENY_MALFORMED_MANDATORY_CUTOFF_BINDING"
    if claimed_deadline != expected_deadline:
        return "DENY_SUNSET_NOT_EARLIEST_CUTOFF"
    if order_expiry > expected_deadline:
        return "DENY_ORDER_EXPIRY_AFTER_SUNSET_DEADLINE"
    if now < claimed_deadline and state["revoked"] is False:
        return "NON_AUTHORIZING_BOUNDED_BEFORE_SUNSET"
    proof = state["completion_proof"]
    proof_booleans = (
        "terminal_order_outcomes_complete",
        "fill_trade_watermark_complete",
        "positions_reconciled",
        "balances_reconciled",
        "child_orders_reconciled",
    )
    if any(not isinstance(proof.get(field), bool) for field in proof_booleans):
        return "DENY_MALFORMED_SUNSET_PROOF"
    complete = (
        state["remaining_opening_or_conditional_orders"] == 0
        and state["unknown_or_possible_fills"] is False
        and all(proof[field] is True for field in proof_booleans)
        and proof.get("reservation_proof_status")
        == "DURABLE_TERMINAL_RELEASE_OR_TRANSFER"
    )
    if not complete:
        return "RECONCILIATION_REQUIRED_UNKNOWN_FILLS_OR_INCOMPLETE_PROOF"
    return "NON_AUTHORIZING_SUNSET_DURABLY_RECONCILED"


def _is_unresolved_or_deny_sentinel(value: str) -> bool:
    normalized = value.upper()
    return (
        "UNRESOLVED" in normalized
        or normalized.startswith("PENDING")
        or "NOT_IMPLEMENTED" in normalized
        or normalized == "DENY"
        or normalized.endswith("_DENY")
    )


def _cross_risk_scope_identity_result(scope: object) -> str:
    """Validate one canonical comparable-family scope before comparison."""
    if (
        not isinstance(scope, dict)
        or set(scope) != set(CROSS_RISK_SCOPE_FIELDS)
    ):
        return "DENY_CROSS_RISK_SCOPE_OR_FAMILY_MISMATCH"
    identity_fields = (
        "venue_capability_profile_id",
        "risk_policy_id",
        "calibration_stratum_id",
    )
    scalar_fields = (
        "venue_id",
        "venue_environment",
        "market_id",
        "approval_tier",
        "validity_mode",
        "api_or_protocol_version",
        "account_mode",
        "order_type",
        "time_in_force",
        "session_id",
        "liquidity_regime",
        "volatility_regime",
        "degraded_state",
    )
    if (
        any(
            not isinstance(scope.get(field), str)
            or not scope[field].strip()
            for field in scalar_fields
        )
        or any(
            not isinstance(scope.get(field), str)
            or re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._:-]{2,127}",
                scope[field],
            )
            is None
            for field in identity_fields
        )
        or any(
            isinstance(scope.get(field), bool)
            or not isinstance(scope.get(field), int)
            or scope[field] < 1
            for field in (
                "venue_capability_profile_version",
                "risk_policy_version",
            )
        )
        or any(
            not isinstance(scope.get(field), str)
            or re.fullmatch(r"[0-9a-f]{64}", scope[field]) is None
            for field in (
                "venue_capability_profile_sha256",
                "risk_policy_sha256",
                "calibration_stratum_sha256",
            )
        )
        or any(
            _is_unresolved_or_deny_sentinel(value)
            for value in scope.values()
            if isinstance(value, str)
        )
        or scope.get("venue_capability_profile_sha256") == "0" * 64
        or scope.get("calibration_stratum_sha256") == "0" * 64
        or scope.get("liquidity_regime") not in LIQUIDITY_REGIMES
        or scope.get("volatility_regime") not in VOLATILITY_REGIMES
        or scope.get("degraded_state") not in DEGRADED_STATES
        or scope.get("approval_tier") != "LEVEL_B"
        or scope.get("validity_mode") != "TIME_BOXED_REAL_CAPITAL"
        or scope.get("risk_policy_id")
        != APPROVED_BITGET_RISK_POLICY_ID
        or scope.get("risk_policy_version")
        != APPROVED_BITGET_RISK_POLICY_VERSION
        or scope.get("risk_policy_sha256")
        != APPROVED_BITGET_RISK_POLICY_SHA256
    ):
        return "DENY_CROSS_RISK_SCOPE_OR_FAMILY_MISMATCH"
    if (
        _venue_mechanics_result(scope)
        != "NON_AUTHORIZING_CLOSED_VENUE_MECHANICS_SHAPE_VALID"
    ):
        return "DENY_CROSS_RISK_SCOPE_OR_FAMILY_MISMATCH"
    return "NON_AUTHORIZING_CANONICAL_CROSS_RISK_SCOPE_IDENTITY_VALID"


def validity_profile_cross_risk_result(
    lower: object,
    higher: object,
    history: object = None,
) -> str:
    """Compare declared ACTIVE profiles only after exact scope/history binding.

    Success is a non-authorizing shape result. Caller-supplied history cannot
    establish runtime ACTIVE status or replace the unavailable ACTIVE evaluator.
    """
    profile_fields = {
        "profile_id",
        "profile_payload_sha256",
        "owner_epoch",
        "capital_stage",
        "action_class",
        "action_family",
        "risk_class",
        "scope",
        "values",
        "authorized_actions",
    }
    if (
        not isinstance(lower, dict)
        or not isinstance(higher, dict)
        or set(lower) != profile_fields
        or set(higher) != profile_fields
    ):
        return "DENY_INCOMPARABLE_CROSS_RISK_PROFILE"
    if (
        any(
            not isinstance(profile.get(field), str)
            or not profile[field].strip()
            for profile in (lower, higher)
            for field in (
                "profile_id",
                "capital_stage",
                "action_class",
                "action_family",
                "risk_class",
            )
        )
        or lower.get("owner_epoch") != higher.get("owner_epoch")
        or isinstance(lower.get("owner_epoch"), bool)
        or not isinstance(lower.get("owner_epoch"), int)
        or lower["owner_epoch"] < 1
        or isinstance(higher.get("owner_epoch"), bool)
        or not isinstance(higher.get("owner_epoch"), int)
        or higher["owner_epoch"] < 1
        or any(
            not isinstance(profile.get("profile_payload_sha256"), str)
            or re.fullmatch(
                r"[0-9a-f]{64}",
                profile["profile_payload_sha256"],
            )
            is None
            for profile in (lower, higher)
        )
        or lower["profile_id"] == higher["profile_id"]
    ):
        return "DENY_INCOMPARABLE_CROSS_RISK_PROFILE"
    risk_pair = (lower["risk_class"], higher["risk_class"])
    if (
        risk_pair not in CROSS_RISK_COMPATIBILITY
        or lower.get("action_family") != higher.get("action_family")
        or lower.get("action_family") != CROSS_RISK_COMPATIBILITY[risk_pair]
        or (
            lower.get("capital_stage"),
            lower.get("action_class"),
            higher.get("capital_stage"),
            higher.get("action_class"),
        )
        != (
            "PILOT_LIMITED_LIVE",
            "PILOT_OPERATING_SCOPE",
            "PRODUCTION_LIVE",
            "PRODUCTION_OPERATING_SCOPE",
        )
    ):
        return "DENY_INCOMPARABLE_CROSS_RISK_PROFILE"
    lower_scope = lower.get("scope")
    higher_scope = higher.get("scope")
    if (
        _cross_risk_scope_identity_result(lower_scope)
        != "NON_AUTHORIZING_CANONICAL_CROSS_RISK_SCOPE_IDENTITY_VALID"
        or _cross_risk_scope_identity_result(higher_scope)
        != "NON_AUTHORIZING_CANONICAL_CROSS_RISK_SCOPE_IDENTITY_VALID"
        or lower_scope != higher_scope
    ):
        return "DENY_CROSS_RISK_SCOPE_OR_FAMILY_MISMATCH"
    expected_fields = ACTION_NUMERIC_FIELDS[lower["action_family"]]
    if (
        not isinstance(lower.get("values"), dict)
        or not isinstance(higher.get("values"), dict)
        or set(lower["values"]) != expected_fields
        or set(higher["values"]) != expected_fields
        or not isinstance(lower.get("authorized_actions"), list)
        or not isinstance(higher.get("authorized_actions"), list)
        or any(
            not isinstance(item, str) or not item
            for item in [
                *lower["authorized_actions"],
                *higher["authorized_actions"],
            ]
        )
    ):
        return "DENY_INCOMPARABLE_CROSS_RISK_PROFILE"
    history_fields = {
        "registry_id",
        "owner_epoch",
        "base_sequence",
        "latest_sequence",
        "complete",
        "immutable",
        "as_of_utc",
        "entries",
    }
    history_entry_fields = {
        "sequence",
        "profile_id",
        "profile_payload_sha256",
        "owner_epoch",
        "scope_sha256",
        "risk_class",
        "lifecycle_state",
        "valid_from",
        "expires_at",
        "superseded_at",
    }
    as_of = (
        _parse_strict_utc(history.get("as_of_utc"))
        if isinstance(history, dict)
        else None
    )
    if (
        not isinstance(history, dict)
        or set(history) != history_fields
        or not isinstance(history.get("registry_id"), str)
        or history["registry_id"]
        != "validity-profile-family-history-v1"
        or isinstance(history.get("owner_epoch"), bool)
        or not isinstance(history.get("owner_epoch"), int)
        or history["owner_epoch"] < 1
        or history.get("owner_epoch") != lower["owner_epoch"]
        or isinstance(history.get("base_sequence"), bool)
        or not isinstance(history.get("base_sequence"), int)
        or history.get("base_sequence") != 0
        or isinstance(history.get("latest_sequence"), bool)
        or not isinstance(history.get("latest_sequence"), int)
        or history["latest_sequence"] < 1
        or history.get("complete") is not True
        or history.get("immutable") is not True
        or as_of is None
        or not isinstance(history.get("entries"), list)
        or len(history["entries"]) != history["latest_sequence"]
    ):
        return "DENY_INCOMPLETE_OR_UNTRUSTED_CROSS_RISK_HISTORY"
    scope_sha256 = canonical_json_digest(lower_scope)
    if not scope_sha256:
        return "DENY_CROSS_RISK_SCOPE_OR_FAMILY_MISMATCH"
    seen_identities: set[tuple[str, str]] = set()
    target_entries: dict[tuple[str, str], dict] = {}
    for expected_sequence, entry in enumerate(history["entries"], start=1):
        if (
            not isinstance(entry, dict)
            or set(entry) != history_entry_fields
            or isinstance(entry.get("sequence"), bool)
            or not isinstance(entry.get("sequence"), int)
            or entry.get("sequence") != expected_sequence
            or isinstance(entry.get("owner_epoch"), bool)
            or not isinstance(entry.get("owner_epoch"), int)
            or entry["owner_epoch"] < 1
            or entry.get("owner_epoch") != history["owner_epoch"]
            or not isinstance(entry.get("profile_id"), str)
            or not entry["profile_id"].strip()
            or not isinstance(entry.get("profile_payload_sha256"), str)
            or re.fullmatch(
                r"[0-9a-f]{64}",
                entry["profile_payload_sha256"],
            )
            is None
            or not isinstance(entry.get("scope_sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", entry["scope_sha256"])
            is None
            or entry["scope_sha256"] != scope_sha256
            or not isinstance(entry.get("risk_class"), str)
            or entry["risk_class"]
            not in {"B1_LIMITED_PILOT", "B2_EXISTING_PRODUCTION"}
            or not isinstance(entry.get("lifecycle_state"), str)
            or entry["lifecycle_state"]
            not in {
                "DRAFT",
                "EVIDENCE_READY",
                "OWNER_APPROVAL_PENDING",
                "ACTIVE",
                "SUSPENDED",
                "EXPIRED",
                "REVOKED",
                "SUPERSEDED",
                "INVALIDATED",
            }
        ):
            return "DENY_INCOMPLETE_OR_UNTRUSTED_CROSS_RISK_HISTORY"
        valid_from = _parse_strict_utc(entry.get("valid_from"))
        expires_at = _parse_strict_utc(entry.get("expires_at"))
        superseded_at = (
            None
            if entry.get("superseded_at") is None
            else _parse_strict_utc(entry.get("superseded_at"))
        )
        identity = (
            entry["profile_id"],
            entry["profile_payload_sha256"],
        )
        if (
            valid_from is None
            or expires_at is None
            or not valid_from < expires_at
            or (
                entry.get("superseded_at") is not None
                and superseded_at is None
            )
            or identity in seen_identities
        ):
            return "DENY_INCOMPLETE_OR_UNTRUSTED_CROSS_RISK_HISTORY"
        seen_identities.add(identity)
        target_entries[identity] = entry
    for profile in (lower, higher):
        identity = (
            profile["profile_id"],
            profile["profile_payload_sha256"],
        )
        entry = target_entries.get(identity)
        if (
            entry is None
            or entry["risk_class"] != profile["risk_class"]
            or entry["lifecycle_state"] != "ACTIVE"
            or entry["superseded_at"] is not None
        ):
            return "DENY_CROSS_RISK_PROFILES_NOT_SIMULTANEOUSLY_ACTIVE"
        valid_from = _parse_strict_utc(entry["valid_from"])
        expires_at = _parse_strict_utc(entry["expires_at"])
        if (
            valid_from is None
            or expires_at is None
            or not valid_from <= as_of < expires_at
        ):
            return "DENY_CROSS_RISK_PROFILES_NOT_SIMULTANEOUSLY_ACTIVE"
    if not set(higher["authorized_actions"]).issubset(
        set(lower["authorized_actions"])
    ):
        return "DENY_HIGHER_RISK_ACTION_SET_BROADER"
    for field in expected_fields:
        low = lower["values"][field]
        high = higher["values"][field]
        if not _strict_positive_duration(low) or not _strict_positive_duration(high):
            return "DENY_CROSS_RISK_TYPE_OR_BOUND_INVALID"
        direction = VALIDITY_NUMERIC_SAFETY_DIRECTIONS[field]
        if (direction == "DECREASE" and high > low) or (
            direction == "INCREASE" and high < low
        ):
            return "DENY_HIGHER_RISK_DURATION_VECTOR_WEAKER"
    return "NON_AUTHORIZING_CROSS_RISK_ORDER_SHAPE_VALID"


def validity_profile_transition_result(before: object, after: object) -> str:
    allowed = {
        ("DRAFT", "EVIDENCE_READY"), ("DRAFT", "SUSPENDED"), ("DRAFT", "INVALIDATED"),
        ("EVIDENCE_READY", "OWNER_APPROVAL_PENDING"), ("EVIDENCE_READY", "SUSPENDED"),
        ("EVIDENCE_READY", "INVALIDATED"), ("OWNER_APPROVAL_PENDING", "ACTIVE"),
        ("OWNER_APPROVAL_PENDING", "SUSPENDED"), ("OWNER_APPROVAL_PENDING", "REVOKED"),
        ("OWNER_APPROVAL_PENDING", "INVALIDATED"), ("ACTIVE", "SUSPENDED"),
        ("ACTIVE", "EXPIRED"), ("ACTIVE", "REVOKED"), ("ACTIVE", "SUPERSEDED"),
        ("ACTIVE", "INVALIDATED"), ("SUSPENDED", "EXPIRED"), ("SUSPENDED", "REVOKED"),
        ("SUSPENDED", "SUPERSEDED"), ("SUSPENDED", "INVALIDATED"),
    }
    states = {"DRAFT", "EVIDENCE_READY", "OWNER_APPROVAL_PENDING", "ACTIVE", "SUSPENDED", "EXPIRED", "REVOKED", "SUPERSEDED", "INVALIDATED"}
    if before not in states or after not in states or (before, after) not in allowed:
        return "DENY_ILLEGAL_PROFILE_TRANSITION"
    return "NON_AUTHORIZING_TRANSITION_SHAPE_VALID"


def validate_validity_profile_draft(profile: dict, schema: dict) -> list[str]:
    errors = validate_schema_subset(profile, schema)
    if errors:
        return errors
    for layer in ("owner_hard_bounds", "owner_selected_effective_values"):
        if profile[layer]["status"] != "UNRESOLVED" or profile[layer]["values"]:
            errors.append(f"{layer} must remain unresolved and empty in this draft")
    if (
        profile.get("authorization_result") != "DENY"
        or profile.get("eligible_for_authorization") is not False
        or profile.get("live_trading_enabled") is not False
        or profile["calibration_recommendation"].get("status") not in {"UNRESOLVED", "NON_AUTHORIZING_RECOMMENDATION"}
        or profile["evidence"].get("authorization_effect") != "NONE"
        or profile.get("capability_evidence_status") != "ABSENT_DENY"
        or profile.get("exact_key", {}).get("venue_capability_profile_id") != "UNRESOLVED_NONAUTHORIZING_CAPABILITY"
        or profile.get("exact_key", {}).get("venue_capability_profile_sha256") != "0" * 64
        or profile.get("exact_key", {}).get("calibration_stratum_id")
        != "UNRESOLVED_NONAUTHORIZING_STRATUM"
        or profile.get("exact_key", {}).get("calibration_stratum_sha256") != "0" * 64
        or profile.get("owner_authority", {}).get("status") != "ABSENT_DENY"
        or profile.get("owner_authority", {}).get("manifest_sequence") != 0
        or profile.get("owner_authority", {}).get("calibration_is_owner_authority") is not False
        or profile.get("supersedes_sequence") != 0
    ):
        errors.append("validity profile draft must remain non-authorizing")
    if profile.get("profile_payload_sha256") != validity_profile_payload_digest(profile):
        errors.append("validity profile canonical payload hash mismatch")
    tuple_result = validity_profile_tuple_result(profile, require_numeric_values=False)
    if tuple_result != "NON_AUTHORIZING_COHERENT_PROFILE_TUPLE":
        errors.append(f"validity profile tuple invalid: {tuple_result}")
    valid_from = _parse_strict_utc(profile.get("valid_from"))
    review_due = _parse_strict_utc(profile.get("review_due_at"))
    expires = _parse_strict_utc(profile.get("expires_at"))
    if None in (valid_from, review_due, expires) or not (valid_from < review_due < expires):
        errors.append("validity profile draft timestamps must be strictly ordered UTC")
    return errors


def validate_pm_dec003_v2_record(record: dict, v1: dict, root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    v1_path = root / "specs/portfolio-mandate-v1/decisions/PM-DEC-003.toml"
    if hashlib.sha256(v1_path.read_bytes()).hexdigest() != PM_DEC003_V1_SHA256:
        errors.append("PM-DEC-003 v1 byte hash changed")
    changed_identity_fields = {"decision_version", "decision_evidence_ref", "decision_type", "baseline_snapshot_archive", "artifact_hashes", "integrity"}
    added_fields = {
        "supersedes_ref", "supersedes_sha256", "validity_profile_model", "profile_exact_key",
        "risk_taxonomy", "owner_authority_separation", "adaptive_monotonicity",
        "calibration_method", "profile_lifecycle", "venue_profile_families", "numeric_feasibility",
        "owner_authority_binding", "owner_numeric_bound_semantics", "action_numeric_matrix",
        "reconciliation_escalation", "profile_artifact_security", "authority_change_contract",
        "protective_overlay_contract", "absolute_time_binding", "active_evidence_contract",
        "semantic_scope_binding", "sunset_reconciliation_contract", "cross_risk_and_history",
    }
    if set(record) != (set(v1) | added_fields):
        errors.append("PM-DEC-003 v2 top-level contract must be exact and closed")
    if (
        record.get("decision_id") != "PM-DEC-003"
        or record.get("decision_version") != 2
        or record.get("supersedes_ref") != "decisions/PM-DEC-003.toml"
        or record.get("supersedes_sha256") != PM_DEC003_V1_SHA256
        or record.get("decision_evidence_ref") != "conversation:2026-07-17:PM-DEC-003-profile-method:answer-3"
        or record.get("decision_type") != "VENUE_AND_RISK_SPECIFIC_VALIDITY_PROFILE_MODEL"
        or record.get("status") != "PARTIALLY_RESOLVED_NUMERIC_PROFILE_PENDING"
        or record.get("numeric_validity_profile_status") != "OWNER_INPUT_REQUIRED"
        or record.get("eligible_for_real_capital_authorization") is not False
        or record.get("live_trading_enabled") is not False
        or record.get("baseline_snapshot_authoritative") is not False
        or record.get("artifact_ratification_eligible") is not False
    ):
        errors.append("PM-DEC-003 v2 identity, supersession, or DENY status mismatch")
    for field in set(v1) - changed_identity_fields:
        if field not in added_fields and record.get(field) != v1.get(field):
            errors.append(f"PM-DEC-003 v2 changed inherited field: {field}")
    carried_sections = {
        "level_a_non_capital", "level_b_real_capital", "temporal_contract", "trusted_clock",
        "approval_lifecycle", "action_lifecycle", "single_use", "configuration_mutation",
        "reconciliation", "working_order_sunset", "automatic_invalidation", "revocation",
        "supersession", "open_exposure", "independent_validity", "pending_owner_values", "safety",
    }
    for section in carried_sections:
        if record.get(section) != v1.get(section):
            errors.append(f"PM-DEC-003 v2 did not carry v1 section unchanged: {section}")
    expected_additions = {
        "validity_profile_model", "profile_exact_key", "risk_taxonomy", "owner_authority_separation",
        "adaptive_monotonicity", "calibration_method", "profile_lifecycle", "venue_profile_families",
        "numeric_feasibility", "owner_authority_binding", "owner_numeric_bound_semantics",
        "action_numeric_matrix", "reconciliation_escalation", "profile_artifact_security",
        "authority_change_contract", "protective_overlay_contract", "absolute_time_binding",
        "active_evidence_contract", "semantic_scope_binding",
        "sunset_reconciliation_contract", "cross_risk_and_history",
    }
    if not expected_additions.issubset(record):
        errors.append("PM-DEC-003 v2 profile-method contract is incomplete")
    expected_profile_contract = {
        "validity_profile_model": {
            "model": "EXACT_VENUE_RISK_STAGE_PROFILE",
            "profile_artifact_family": "validity-profiles/<venue>/<profile-id>-vN.toml",
            "schema_ref": "validity-profiles/validity-profile.schema.json",
            "numeric_profile_instances_status": "OWNER_INPUT_REQUIRED",
            "profile_can_authorize": False,
            "mutable_current_alias_allowed_in_authorization": False,
            "zero_match_result": "DENY",
            "multiple_match_result": "DENY",
            "wildcard_or_default_result": "DENY",
            "cross_venue_risk_stage_fallback_allowed": False,
            "capital_stage_enum": list(PM_NORMATIVE_CAPITAL_STAGES),
        },
        "profile_exact_key": {
            "fields": list(PM_DEC003_V2_EXACT_KEY_FIELDS),
            "wildcards_nulls_or_empty_values_allowed": False,
            "exactly_one_active_match_required": True,
            "account_book_instrument_and_scope_bindings_required_in_manifest": True,
        },
        "risk_taxonomy": {
            "classes": ["A0_NON_CAPITAL", "B1_LIMITED_PILOT", "B2_EXISTING_PRODUCTION", "B3_CASH_ACTION", "B4_AUTHORITY_MUTATION"],
            "higher_class_may_be_less_conservative": False,
            "unknown_or_incomparable_class_result": "DENY",
        },
        "owner_authority_separation": {
            "required_layers": ["OWNER_HARD_BOUNDS", "CALIBRATION_RECOMMENDATION", "OWNER_SELECTED_EFFECTIVE_VALUES"],
            "calibration_recommendation_can_authorize": False,
            "owner_hard_bounds_required_for_real_capital": True,
            "owner_selected_effective_values_required_for_real_capital": True,
            "missing_numeric_owner_value_result": "DENY_REAL_CAPITAL",
            "recommendation_outside_owner_bounds_result": "DENY",
        },
        "adaptive_monotonicity": {
            "safety_directions": ["SAFER_DECREASE", "SAFER_INCREASE", "NON_MONOTONE_OWNER_ONLY"],
            "automatic_change_requires_authorized_action_subset": True,
            "allowed_automatic_results": ["SHORTER_VALIDITY", "LARGER_PROTECTIVE_BUFFER", "SUSPENDED", "INVALIDATED", "DENY"],
            "automatic_relaxation_allowed": False,
            "automatic_rebound_allowed": False,
            "unknown_or_incomparable_change_result": "DENY",
        },
        "calibration_method": {
            "authorization_effect": "NONE",
            "separate_clocks": ["OPERATING_APPROVAL_TTL", "ONE_TIME_ACTIVATION_WINDOW", "ORDER_TIF", "CANCEL_RECONCILIATION_BUFFER", "REVOCATION_AGE", "RECONCILIATION_ESCALATION_DEADLINE", "EVIDENCE_AGE"],
            "required_strata": ["VENUE", "API_OR_PROTOCOL_VERSION", "ACCOUNT_MODE", "MARKET", "ORDER_TYPE", "TIF", "SESSION", "LIQUIDITY_REGIME", "VOLATILITY_REGIME", "DEGRADED_STATE"],
            "censored_unknown_timeout_and_lost_ack_retained": True,
            "cancel_and_late_fill_method": "TIME_TO_EVENT_WITH_CENSORING_AND_COMPETING_RISKS",
            "tail_estimate": "PREREGISTERED_TAIL_QUANTILE_WITH_ONE_SIDED_UNCERTAINTY",
            "cluster_aware_effective_sample_required": True,
            "windows": ["ROLLING_RECENT", "STRESS_ARCHIVE", "FORWARD_CONFIRMATION"],
            "holdout_parameter_tuning_allowed": False,
            "sparse_or_unobserved_stratum_result": "DENY_OR_OWNER_BOUND_FALLBACK_WITHIN_SAME_EXACT_KEY",
            "deterministic_generation_and_canonical_hash_required": True,
        },
        "profile_lifecycle": {
            "states": ["DRAFT", "EVIDENCE_READY", "OWNER_APPROVAL_PENDING", "ACTIVE", "SUSPENDED", "EXPIRED", "REVOKED", "SUPERSEDED", "INVALIDATED"],
            "allowed_transitions": [
                "DRAFT->EVIDENCE_READY", "DRAFT->SUSPENDED", "DRAFT->INVALIDATED",
                "EVIDENCE_READY->OWNER_APPROVAL_PENDING", "EVIDENCE_READY->SUSPENDED", "EVIDENCE_READY->INVALIDATED",
                "OWNER_APPROVAL_PENDING->ACTIVE", "OWNER_APPROVAL_PENDING->SUSPENDED", "OWNER_APPROVAL_PENDING->REVOKED", "OWNER_APPROVAL_PENDING->INVALIDATED",
                "ACTIVE->SUSPENDED", "ACTIVE->EXPIRED", "ACTIVE->REVOKED", "ACTIVE->SUPERSEDED", "ACTIVE->INVALIDATED",
                "SUSPENDED->EXPIRED", "SUSPENDED->REVOKED", "SUSPENDED->SUPERSEDED", "SUSPENDED->INVALIDATED",
            ],
            "terminal_states": ["EXPIRED", "REVOKED", "SUPERSEDED", "INVALIDATED"],
            "terminal_reactivation_allowed": False,
            "unlisted_transition_result": "DENY",
        },
        "venue_profile_families": {
            "bitget_profile_family": "BITGET_EXACT_API_ACCOUNT_MARKET_PROFILE",
            "bitget_capability_policy_binding": "bitget-btc-v1",
            "moex_profile_family": "MOEX_EXACT_BROKER_API_MARKET_BOARD_SESSION_INSTRUMENT_CLASS_PROFILE",
            "moex_status": "FUTURE_BLOCKED",
            "cross_family_pooling_allowed": False,
            "cross_family_fallback_allowed": False,
        },
        "numeric_feasibility": {
            "duration_unit": "INTEGER_MILLISECONDS",
            "technical_representation_max_ms": VALIDITY_DURATION_TECHNICAL_MAX_MS,
            "technical_max_is_owner_approved_ttl": False,
            "boolean_float_or_string_coercion_allowed": False,
            "operating_ttl_constraint": "OPERATING_TTL_MS > CANCEL_RECONCILIATION_BUFFER_MS + DISPATCH_GUARD_MS",
            "risk_increasing_order_constraint": "ORDER_EXPIRY_AT <= MIN(APPROVAL,EVIDENCE,CAPABILITY,RISK_POLICY,RUNTIME_PROTECTION)_CUTOFF - CANCEL_RECONCILIATION_BUFFER_MS",
            "exact_order_identity_and_expiry_required": True,
            "shared_feasibility_and_sunset_deadline_helper_required": True,
            "incompatible_unit_direction_or_horizon_result": "DENY",
            "unresolved_numeric_values_result": "DENY_REAL_CAPITAL",
        },
        "owner_authority_binding": {
            "required_for_layers": ["OWNER_HARD_BOUNDS", "OWNER_SELECTED_EFFECTIVE_VALUES"],
            "manifest_bindings": ["MANIFEST_REF", "MANIFEST_SHA256", "MANIFEST_VERSION", "MONOTONIC_SEQUENCE", "CANONICAL_OWNER_PAYLOAD_SHA256"],
            "canonical_owner_payload_required_fields": ["PROFILE_ID", "PROFILE_VERSION", "PROFILE_PAYLOAD_SHA256", "OWNER_HARD_BOUNDS", "OWNER_SELECTED_EFFECTIVE_VALUES"],
            "calibration_is_owner_authority": False,
            "draft_status": "ABSENT_DENY",
            "missing_mismatch_or_replay_result": "DENY",
        },
        "owner_numeric_bound_semantics": {
            "required_active_status_owner_hard_bounds": "VERIFIED",
            "required_active_status_owner_selected_effective_values": "VERIFIED",
            "required_calibration_status": "NON_AUTHORIZING_RECOMMENDATION",
            "safer_decrease_fields": ["operating_ttl_ms", "single_use_activation_window_ms", "clock_skew_tolerance_ms", "revocation_snapshot_max_age_ms", "reconciliation_escalation_deadline_ms"],
            "safer_decrease_comparison": "EFFECTIVE_LE_OWNER_HARD_BOUND",
            "safer_increase_fields": ["cancel_reconciliation_buffer_ms", "dispatch_guard_ms", "review_lead_time_ms"],
            "safer_increase_comparison": "EFFECTIVE_GE_OWNER_HARD_BOUND",
            "non_monotone_owner_only_comparison": "EFFECTIVE_EQ_EXACT_OWNER_SELECTED_VALUE",
            "signed_but_unresolved_result": "DENY",
            "missing_incomparable_or_outside_bound_result": "DENY",
        },
        "action_numeric_matrix": {
            "operating_actions": ["PILOT_OPERATING_SCOPE", "PRODUCTION_OPERATING_SCOPE"],
            "operating_validity_mode": "TIME_BOXED_REAL_CAPITAL",
            "operating_required_fields": ["operating_ttl_ms", "cancel_reconciliation_buffer_ms", "dispatch_guard_ms", "clock_skew_tolerance_ms", "revocation_snapshot_max_age_ms", "review_lead_time_ms", "reconciliation_escalation_deadline_ms"],
            "operating_forbidden_fields": ["single_use_activation_window_ms"],
            "single_use_actions": ["REAL_BOOK_TRANSFER", "DISTRIBUTION", "REAL_ACCOUNT_OR_CREDENTIAL_CHANGE", "REAL_SCOPE_EXPANSION", "HARD_LIMIT_INCREASE", "LEVERAGE_OR_MARGIN_CHANGE", "VALIDITY_PROFILE_AUTHORITY_CHANGE"],
            "single_use_validity_mode": "ONE_TIME_REAL_CAPITAL",
            "single_use_required_fields": ["single_use_activation_window_ms", "dispatch_guard_ms", "clock_skew_tolerance_ms", "revocation_snapshot_max_age_ms", "reconciliation_escalation_deadline_ms"],
            "single_use_forbidden_fields": ["operating_ttl_ms", "cancel_reconciliation_buffer_ms", "review_lead_time_ms"],
            "noncapital_action": "NON_CAPITAL",
            "noncapital_validity_mode": "LONG_LIVED_NON_CAPITAL",
            "noncapital_forbidden_real_capital_fields": True,
            "missing_extra_or_inapplicable_result": "DENY",
        },
        "reconciliation_escalation": {
            "field": "reconciliation_escalation_deadline_ms",
            "safety_direction": "SAFER_DECREASE",
            "deadline_effect": "ESCALATE_ONLY",
            "deadline_proves_no_fill": False,
            "deadline_releases_exposure_or_reservation": False,
            "deadline_clears_no_new_risk_or_reconciliation_required": False,
            "clearance_requires": "VERIFIED_TERMINAL_VENUE_OUTCOME",
        },
        "profile_artifact_security": {
            "schema_exact_id_version_hash_required": True,
            "profile_canonical_payload_hash_required": True,
            "supersedes_ref_hash_and_monotonic_sequence_required": True,
            "future_active_evidence_bindings": ["EVIDENCE_REF", "EVIDENCE_SHA256", "ISSUER_REF", "AS_OF", "FRESHNESS"],
            "draft_sentinel_result": "DENY",
            "signed_persistent_registry_status": "PENDING_RUNTIME_IMPLEMENTATION",
            "registry_helper_authorization_effect": "NONE",
            "strict_canonical_json_required": True,
            "duplicate_keys_nan_infinity_or_malformed_json_result": "DENY",
            "release_archive_duplicate_traversal_symlink_or_special_member_result": "DENY",
            "release_source_lstat_containment_and_no_symlink_required": True,
            "release_source_symlink_or_nonregular_member_result": "DENY",
        },
        "authority_change_contract": {
            "action_class": "VALIDITY_PROFILE_AUTHORITY_CHANGE",
            "risk_class": "B4_AUTHORITY_MUTATION",
            "validity_mode": "ONE_TIME_REAL_CAPITAL",
            "level_b_signature_required": True,
            "independent_second_factor_required": True,
            "owner_selected_single_use_window_required": True,
            "canonical_payload_binds_window_and_absolute_timestamps": True,
            "durable_single_use_consumption_required": True,
            "durable_registry_shape": "CALLER_SUPPLIED_GLOBAL_CLOSED_APPEND_ONLY_SHAPE_ONLY",
            "durable_registry_id": B4_GLOBAL_REGISTRY_ID,
            "durable_registry_scope": B4_GLOBAL_REGISTRY_SCOPE,
            "durable_registry_complete_history_required": True,
            "durable_registry_genesis_base_sequence": 0,
            "durable_registry_genesis_owner_epoch": B4_GLOBAL_REGISTRY_GENESIS_OWNER_EPOCH,
            "durable_registry_empty_genesis_canonicalization": "SORTED_KEYS_COMPACT_UTF8_JSON_V1",
            "durable_registry_empty_genesis_sha256": B4_GLOBAL_REGISTRY_GENESIS_SHA256,
            "durable_registry_genesis_caller_selectable": False,
            "empty_registry_requires_pinned_genesis_and_zero_owner_head": True,
            "record_owner_epoch_monotonic_and_latest_head_exact_required": True,
            "proposal_owner_epoch_not_before_latest_record_owner_epoch_required": True,
            "consumption_indexes_global_across_owner_epochs": True,
            "owner_epoch_scoped_registry_reset_result": "DENY",
            "durable_sequence_and_cas_required": True,
            "atomic_unique_parent_consumption_required": True,
            "independent_parent_profile_and_manifest_consumption_required": True,
            "hidden_history_prefix_result": "DENY",
            "same_parent_branch_result": "DENY",
            "new_profile_and_configuration_hash_required": True,
            "canonical_payload_binds_previous_configuration_sha256": True,
            "previous_configuration_derived_from_exact_prior_manifest_bytes_and_record": True,
            "new_configuration_must_differ_from_previous_configuration": True,
            "old_profile_and_operating_manifest_invalidated": True,
            "old_operating_manifest_reuse_result": "DENY",
            "separate_new_operating_manifest_required": True,
            "operating_manifest_canonical_exact_bytes_required": True,
            "operating_manifest_canonical_pure_posix_versioned_ref_required": True,
            "operating_manifest_caller_supplied_registry_and_prior_exact_byte_shape_required": True,
            "operating_manifest_shape_proves_registry_trust_currentness_or_completeness": False,
            "operating_manifest_strict_sequence_and_supersedes_chain_required": True,
            "operating_manifest_identity_digest_key": ["MANIFEST_REF", "MANIFEST_VERSION", "MANIFEST_SEQUENCE"],
            "operating_manifest_identity_digest_conflict_or_replay_result": "DENY",
            "prior_configuration_reuse_result": "DENY",
            "operating_manifest_bindings": ["MANIFEST_REF", "MANIFEST_VERSION", "MANIFEST_SEQUENCE", "MANIFEST_SHA256", "SUPERSEDES_REF", "SUPERSEDES_VERSION", "SUPERSEDES_SEQUENCE", "SUPERSEDES_SHA256", "CHANGE_ACTION_ID", "CHANGE_PAYLOAD_SHA256", "PROFILE_SHA256", "CONFIGURATION_SHA256", "EFFECTIVE_FROM", "EXPIRES_AT"],
            "malformed_or_old_operating_manifest_result": "DENY",
            "registry_shape_validator_success_result": "NON_AUTHORIZING_B4_REGISTRY_SHAPE_VALID",
            "registry_shape_validator_proves_current_or_fresh_checkpoint": False,
            "registry_shape_validator_proves_persistence_or_atomicity": False,
            "authority_readiness_requires_independently_trusted_current_registry_checkpoint": True,
            "self_declared_registry_or_canonical_genesis_readiness_result": "DENY_B4_CURRENT_REGISTRY_CHECKPOINT_OR_RUNTIME_TRUST_UNAVAILABLE",
            "consumption_shape_proves_durable_consumption": False,
            "runtime_trust_root_status": "PENDING_PM-DEC-007",
            "validator_authorization_effect": "NONE",
        },
        "protective_overlay_contract": {
            "owner_envelope_mutable": False,
            "overlay_id_required": True,
            "overlay_immutable_and_versioned": True,
            "effective_authority": "RESTRICTIVE_INTERSECTION",
            "action_specific_vector_required": True,
            "complete_immutable_owner_epoch_history_required": True,
            "caller_supplied_incomplete_history_result": "DENY",
            "late_ack_restores_authority": False,
            "automatic_rebound_allowed": False,
            "new_owner_epoch_required_for_relaxation": True,
            "pure_helper_is_trust_root": False,
        },
        "absolute_time_binding": {
            "timestamps": ["EFFECTIVE_FROM", "REVIEW_DUE_AT", "EXPIRES_AT", "COMMIT_AT", "EVALUATED_AT", "REVOCATION_SNAPSHOT_AT", "FIRST_DURABLE_UNKNOWN_AT", "ESCALATION_DUE_AT", "ESCALATION_DISPATCHED_AT", "ESCALATION_ACK_AT"],
            "operating_interval_equals_owner_selected_ttl": True,
            "single_use_interval_equals_owner_selected_window": True,
            "review_due_equals_expiry_minus_review_lead": True,
            "positive_operating_interval_required": True,
            "operating_review_cutoff_order": "EFFECTIVE_FROM <= EVALUATED_AT <= COMMIT_AT < REVIEW_DUE_AT < EXPIRES_AT",
            "review_due_equality_or_post_cutoff_result": "DENY",
            "commit_not_before_effective_from": True,
            "commit_guard_required": True,
            "revocation_freshness_required": True,
            "causal_revocation_order": "REVOCATION_SNAPSHOT_AT <= EVALUATED_AT <= COMMIT_AT < EXPIRES_AT",
            "revocation_age_measurement": "COMMIT_AT_MINUS_REVOCATION_SNAPSHOT_AT",
            "protective_intervals_strictly_positive": True,
            "causal_escalation_order_required": True,
            "unknown_dispatch_and_ack_not_after_evaluation_or_now": True,
            "overflow_or_mismatch_result": "DENY",
        },
        "active_evidence_contract": {
            "active_schema_must_be_separate_exact_bytes": True,
            "draft_schema_in_memory_mutation_allowed": False,
            "active_schema_status": "NOT_IMPLEMENTED",
            "deterministic_evidence_evaluator_status": "NOT_IMPLEMENTED",
            "verified_requires_censored_and_unknown_outcomes": True,
            "verified_requires_competing_risks": True,
            "verified_requires_tail_quantile_and_one_sided_confidence": True,
            "verified_requires_estimator_clustering_and_effective_sample": True,
            "verified_requires_sealed_recent_stress_and_forward_windows": True,
            "verified_requires_holdout_access_history_and_provenance": True,
            "sealed_windows_not_after_as_of_now_or_expiry": True,
            "holdout_access_not_after_as_of_or_now": True,
            "owner_bound_minimum_sample_and_window_threshold_binding_required": True,
            "implicit_or_default_numeric_minimum_allowed": False,
            "actual_counts_must_meet_owner_bound_minima": True,
            "closed_liquidity_volatility_and_degraded_taxonomies_required": True,
            "unresolved_regime_or_degraded_scope_result": "DENY",
            "closed_holdout_access_purposes": ["FINAL_FORWARD_CONFIRMATION"],
            "owner_bound_exact_provenance_refs_required": True,
            "shape_validator_success_result": "NON_AUTHORIZING_DECLARED_EVIDENCE_SHAPE_CAUSALITY_VALID",
            "shape_validator_proves_estimator_correctness": False,
            "shape_validator_proves_statistical_truth": False,
            "shape_validator_proves_owner_authority": False,
            "future_statistical_evaluator_required": True,
            "complete_shape_authorization_effect": "NONE",
            "active_lookup_without_runtime_trust_root_result": ACTIVE_SCHEMA_UNAVAILABLE,
        },
        "semantic_scope_binding": {
            "exact_byte_hash_before_parse_required": True,
            "lifecycle_and_freshness_required": True,
            "scope_fields": ["VENUE", "ENVIRONMENT", "MARKET", "STAGE", "RISK", "API_OR_PROTOCOL_VERSION", "ACCOUNT_MODE", "ORDER_TYPE", "TIF", "SESSION", "LIQUIDITY_REGIME", "VOLATILITY_REGIME", "DEGRADED_STATE", "CALIBRATION_STRATUM_ID", "CALIBRATION_STRATUM_SHA256", "RISK_POLICY_ID", "RISK_POLICY_VERSION", "RISK_POLICY_SHA256"],
            "approved_bitget_risk_policy_id": "bitget-btc-v1",
            "approved_bitget_risk_policy_version": 1,
            "approved_bitget_risk_policy_sha256": APPROVED_BITGET_RISK_POLICY_SHA256,
            "approved_bitget_risk_policy_source_path": "governance/risk-policy.toml",
            "approved_policy_exact_source_bytes_required": True,
            "caller_selected_expected_policy_sha_allowed": False,
            "approved_policy_required_semantics": ["POLICY_ID_VERSION_SHA256", "BITGET", "USDT_MARGINED_FUTURES", "BTCUSDT_ONLY", "LIMIT_ONLY", "LIVE_DISABLED"],
            "bitget_limit_only_independent_of_caller_policy_id": True,
            "venue_mechanics_default": "REJECT_ALL",
            "venue_mechanics_matrix": ["BITGET:PAPER_SIMULATOR|BITGET_TESTNET|BITGET_PRODUCTION:BITGET_USDT_FUTURES:BITGET_API_V2:ONE_WAY_MODE:BITGET_24X7:LIMIT_GTC|LIMIT_IOC|LIMIT_FOK|LIMIT_POST_ONLY", "MOEX:FUTURE_BLOCKED"],
            "unknown_or_mixed_venue_mechanics_result": "DENY",
            "capability_and_policy_scope_mismatch_result": "DENY",
            "cross_bitget_moex_result": "DENY",
            "market_while_limit_only_result": "DENY",
            "moex_status": "FUTURE_BLOCKED",
        },
        "sunset_reconciliation_contract": {
            "new_risk_cutoff": "EARLIEST_MANDATORY_VALIDITY_CUTOFF_MINUS_CANCEL_RECONCILIATION_BUFFER",
            "mandatory_cutoffs": ["APPROVAL", "EVIDENCE", "CAPABILITY", "RISK_POLICY", "RUNTIME_PROTECTION"],
            "exact_order_identity_and_expiry_required": True,
            "order_expiry_not_after_earliest_cutoff_minus_buffer_required": True,
            "shared_feasibility_and_strict_sunset_helper_required": True,
            "completion_requires_terminal_order_outcomes": True,
            "completion_requires_fill_trade_watermark": True,
            "completion_requires_position_and_balance_reconciliation": True,
            "completion_requires_child_order_reconciliation": True,
            "completion_requires_durable_reservation_release_or_transfer_proof": True,
            "zero_open_orders_alone_is_terminal_proof": False,
            "legacy_working_order_helper_can_reconcile": False,
            "legacy_cancel_zero_open_and_generic_venue_reconciliation_result": "RECONCILIATION_REQUIRED_NO_ZERO_EFFECT_PROMISE",
            "strict_sunset_validator_required_for_reconciled_shape": True,
            "unknown_or_possible_fill_result": "RECONCILIATION_REQUIRED",
            "late_escalation_ack_restores_authority": False,
        },
        "cross_risk_and_history": {
            "comparable_family_required": True,
            "simultaneously_active_required": True,
            "canonical_exact_scope_fields": ["VENUE", "ENVIRONMENT", "MARKET", "APPROVAL_TIER", "VALIDITY_MODE", "CAPABILITY_ID_VERSION_SHA256", "RISK_POLICY_ID_VERSION_SHA256", "CALIBRATION_STRATUM_ID_SHA256", "API_OR_PROTOCOL_VERSION", "ACCOUNT_MODE", "ORDER_TYPE", "TIF", "SESSION", "LIQUIDITY_REGIME", "VOLATILITY_REGIME", "DEGRADED_STATE"],
            "active_comparison_requires_resolved_scope": True,
            "active_ineligible_sentinels": ["UNRESOLVED*", "*_DENY", "PENDING*", "NOT_IMPLEMENTED*"],
            "zero_capability_or_calibration_hash_result": "DENY",
            "draft_scope_plus_caller_active_history_result": "DENY",
            "caller_supplied_family_label_establishes_comparability": False,
            "simultaneous_active_derived_from_history": True,
            "caller_supplied_simultaneously_active_boolean_allowed": False,
            "compatibility_matrix": ["B1_LIMITED_PILOT->B2_EXISTING_PRODUCTION:OPERATING"],
            "noncapital_or_single_use_comparison_result": "DENY",
            "b2_may_be_weaker_than_b1": False,
            "higher_risk_action_set_must_be_subset": True,
            "higher_risk_directional_vector_must_be_no_weaker": True,
            "action_specific_vector_required": True,
            "complete_immutable_owner_epoch_history_required": True,
            "history_registry_id": "validity-profile-family-history-v1",
            "contiguous_history_from_base_sequence_zero_required": True,
            "history_shape_proves_runtime_active_or_trust": False,
            "omitted_history_or_union_vector_result": "DENY",
            "validator_authorization_effect": "NONE",
        },
    }
    for section, expected in expected_profile_contract.items():
        if record.get(section) != expected:
            errors.append(f"PM-DEC-003 v2 closed profile contract changed: {section}")
    model = record.get("validity_profile_model", {})
    key = record.get("profile_exact_key", {})
    owner = record.get("owner_authority_separation", {})
    adaptive = record.get("adaptive_monotonicity", {})
    venues = record.get("venue_profile_families", {})
    feasibility = record.get("numeric_feasibility", {})
    lifecycle = record.get("profile_lifecycle", {})
    if (
        model.get("profile_can_authorize") is not False
        or model.get("cross_venue_risk_stage_fallback_allowed") is not False
        or model.get("mutable_current_alias_allowed_in_authorization") is not False
        or model.get("capital_stage_enum")
        != list(PM_NORMATIVE_CAPITAL_STAGES)
        or key.get("fields") != list(PM_DEC003_V2_EXACT_KEY_FIELDS)
        or key.get("wildcards_nulls_or_empty_values_allowed") is not False
        or owner.get("calibration_recommendation_can_authorize") is not False
        or owner.get("missing_numeric_owner_value_result") != "DENY_REAL_CAPITAL"
        or adaptive.get("automatic_relaxation_allowed") is not False
        or adaptive.get("automatic_rebound_allowed") is not False
        or venues.get("moex_status") != "FUTURE_BLOCKED"
        or venues.get("cross_family_fallback_allowed") is not False
        or feasibility.get("duration_unit") != "INTEGER_MILLISECONDS"
        or feasibility.get("risk_increasing_order_constraint")
        != "ORDER_EXPIRY_AT <= MIN(APPROVAL,EVIDENCE,CAPABILITY,RISK_POLICY,RUNTIME_PROTECTION)_CUTOFF - CANCEL_RECONCILIATION_BUFFER_MS"
        or feasibility.get("exact_order_identity_and_expiry_required")
        is not True
        or feasibility.get(
            "shared_feasibility_and_sunset_deadline_helper_required"
        )
        is not True
        or feasibility.get("unresolved_numeric_values_result") != "DENY_REAL_CAPITAL"
        or lifecycle.get("terminal_reactivation_allowed") is not False
    ):
        errors.append("PM-DEC-003 v2 fail-closed profile method changed or is incomplete")
    artifact_map = {item.get("path"): item.get("sha256") for item in record.get("artifact_hashes", [])}
    artifact_entries = record.get("artifact_hashes", [])
    artifact_paths = [item.get("path") for item in artifact_entries if isinstance(item, dict)] if isinstance(artifact_entries, list) else []
    if (
        record.get("baseline_snapshot_archive") != "portfolio-mandate-v0.6.zip"
        or not isinstance(artifact_entries, list)
        or len(artifact_entries) != len(PM_DEC003_REQUIRED_ARTIFACTS)
        or len(artifact_paths) != len(set(artifact_paths))
        or set(artifact_map) != set(PM_DEC003_REQUIRED_ARTIFACTS)
    ):
        errors.append("PM-DEC-003 v2 artifact hash set must be exact")
    else:
        for relative, expected in artifact_map.items():
            if hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected:
                errors.append(f"PM-DEC-003 v2 artifact hash mismatch: {relative}")
    integrity = record.get("integrity", {})
    if integrity.get("canonicalization") != "SORTED_KEYS_COMPACT_UTF8_JSON_V1" or integrity.get("decision_payload_sha256") != pm_dec003_payload_digest(record):
        errors.append("PM-DEC-003 v2 canonical payload hash mismatch")
    return errors


def check_required_files(errors: list[str]) -> None:
    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            errors.append(f"missing required file: {relative}")


def check_parseable_files(errors: list[str]) -> None:
    for path in ROOT.rglob("*.toml"):
        try:
            load_toml(path)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            errors.append(f"invalid TOML {path.relative_to(ROOT)}: {exc}")
    for path in ROOT.rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON {path.relative_to(ROOT)}: {exc}")


def check_agents(errors: list[str]) -> None:
    source_config_path = ROOT / "config/codex/config.toml"
    installed_config_path = ROOT / ".codex/config.toml"
    config = load_toml(source_config_path)
    agents = config.get("agents", {})
    reserved = {"max_threads", "max_depth", "job_max_runtime_seconds", "interrupt_message"}
    configured = set(agents) - reserved
    if configured != REQUIRED_AGENTS:
        errors.append(f"agent set mismatch: expected {sorted(REQUIRED_AGENTS)}, got {sorted(configured)}")
    if agents.get("max_threads") != 4:
        errors.append("agents.max_threads must remain 4")
    if agents.get("max_depth") != 1:
        errors.append("agents.max_depth must remain 1")
    for name in REQUIRED_AGENTS:
        path = ROOT / "config/codex/agents" / f"{name}.toml"
        if not path.is_file():
            errors.append(f"missing agent file: {path.relative_to(ROOT)}")
            continue
        data = load_toml(path)
        if data.get("name") != name:
            errors.append(f"agent name mismatch in {path.relative_to(ROOT)}")
        if not data.get("developer_instructions", "").strip():
            errors.append(f"empty developer_instructions in {path.relative_to(ROOT)}")
    if not installed_config_path.is_file():
        errors.append("missing installed Codex config: .codex/config.toml")
        return
    installed_config = load_toml(installed_config_path)
    installed_agents = installed_config.get("agents", {})
    for name, expected in UI_AGENT_EXPECTATIONS.items():
        source_entry = agents.get(name, {})
        installed_entry = installed_agents.get(name, {})
        expected_ref = f"./agents/{name}.toml"
        if source_entry.get("config_file") != expected_ref:
            errors.append(f"source config must register {name} at {expected_ref}")
        if installed_entry.get("config_file") != expected_ref:
            errors.append(f"installed config must register {name} at {expected_ref}")
        source_path = ROOT / "config/codex/agents" / f"{name}.toml"
        installed_path = ROOT / ".codex/agents" / f"{name}.toml"
        if not installed_path.is_file():
            errors.append(f"missing installed UI agent file: {installed_path.relative_to(ROOT)}")
            continue
        if source_path.read_bytes() != installed_path.read_bytes():
            errors.append(f"UI agent source/install mismatch: {name}")
        data = load_toml(source_path)
        for field, value in expected.items():
            if data.get(field) != value:
                errors.append(f"{name}.{field} must be {value!r}")


def check_risk_policy(errors: list[str]) -> None:
    policy_path = ROOT / "governance/risk-policy.toml"
    if hashlib.sha256(policy_path.read_bytes()).hexdigest() != APPROVED_BITGET_RISK_POLICY_SHA256:
        errors.append("approved Bitget risk-policy bytes changed or were substituted")
    policy = load_toml(policy_path)
    risk = policy["position_risk"]
    total = float(risk["risk_total_cap_pct"])
    legs = sum(float(value) for value in risk["risk_legs_pct"])
    if abs(total - legs) > 1e-9:
        errors.append(f"risk legs sum to {legs}, expected total cap {total}")
    if total != 3.0:
        errors.append("baseline total risk cap must remain 3.0% without owner approval")
    if risk["max_simultaneous_positions"] != 5:
        errors.append("max_simultaneous_positions must remain 5")
    if policy["scope"]["allowed_symbols"] != ["BTCUSDT"]:
        errors.append("allowed symbol baseline must remain BTCUSDT only")
    if policy["live_trading"]["enabled"] is not False:
        errors.append("live trading must remain disabled in repository baseline")
    allocation = policy["allocation"]
    if float(allocation["scalping_pct"]) + float(allocation["intraday_pct"]) != 100.0:
        errors.append("source allocations must sum to 100%")


def check_pipeline(errors: list[str]) -> None:
    pipeline = load_toml(ROOT / "factory/pipeline.toml")
    if pipeline.get("max_parallel_agents") != 4:
        errors.append("pipeline max_parallel_agents must match Codex max_threads")
    if pipeline.get("max_agent_depth") != 1:
        errors.append("pipeline max_agent_depth must be 1")
    if pipeline.get("single_writer") is not True:
        errors.append("single_writer must remain enabled")
    stage_ids = [stage["id"] for stage in pipeline.get("stages", [])]
    expected = [
        "01_discovery",
        "02_architecture",
        "03_specification",
        "03_deep_spec_review",
        "04_implementation",
        "05_adversarial_tests",
        "06_independent_review",
        "06_deep_evidence_review",
        "07_release",
    ]
    if stage_ids != expected:
        errors.append(f"pipeline stages out of order: {stage_ids}")


def check_spec(errors: list[str]) -> None:
    spec = (ROOT / "specs/bitget-btc-telegram-v1/spec.md").read_text(encoding="utf-8")
    missing = sorted(REQUIRED_SPEC_HEADINGS - set(spec.splitlines()))
    if missing:
        errors.append(f"TB-001 spec missing headings: {missing}")
    acceptance = load_toml(ROOT / "specs/bitget-btc-telegram-v1/acceptance.toml")
    ids = [item.get("id") for item in acceptance.get("criteria", [])]
    if len(ids) < 10:
        errors.append("TB-001 requires at least 10 acceptance criteria")
    if len(ids) != len(set(ids)):
        errors.append("acceptance IDs must be unique")
    tasks = (ROOT / "specs/bitget-btc-telegram-v1/tasks.md").read_text(encoding="utf-8")
    unreferenced = [item for item in ids if item not in tasks]
    if unreferenced:
        errors.append(f"acceptance IDs not traced from tasks: {unreferenced}")


def check_portfolio_mandate(errors: list[str]) -> None:
    directory = ROOT / "specs/portfolio-mandate-v1"
    spec = (directory / "spec.md").read_text(encoding="utf-8")
    tasks = (directory / "tasks.md").read_text(encoding="utf-8")
    acceptance = load_toml(directory / "acceptance.toml")
    example = load_toml(directory / "mandate.example.toml")
    decision_001 = load_toml(directory / "decisions/PM-DEC-001.toml")
    decision_002 = load_toml(directory / "decisions/PM-DEC-002.toml")
    decision_003 = load_toml(directory / "decisions/PM-DEC-003.toml")
    decision_003_v2 = load_toml(directory / "decisions/PM-DEC-003-v2.toml")
    schema = json.loads((directory / "mandate.schema.json").read_text(encoding="utf-8"))
    profile_schema = json.loads((directory / "validity-profiles/validity-profile.schema.json").read_text(encoding="utf-8"))
    profile_example = load_toml(directory / "validity-profiles/bitget-pilot-draft-v1.toml")
    owner_schema = json.loads(
        (directory / "owner-decision-manifest.schema.json").read_text(encoding="utf-8")
    )
    try:
        dec002_snapshot_bytes = read_archive_member(
            ROOT,
            "portfolio-mandate-v0.4.zip",
            "specs/portfolio-mandate-v1/decisions/PM-DEC-002.toml",
        )
        if (directory / "decisions/PM-DEC-002.toml").read_bytes() != dec002_snapshot_bytes:
            errors.append("PM-DEC-002 must remain byte-identical to its v0.4 consistency snapshot")
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        errors.append(f"PM-DEC-002 v0.4 consistency snapshot is unavailable: {exc}")
    try:
        dec003_snapshot_bytes = read_archive_member(
            ROOT, "portfolio-mandate-v0.5.zip",
            "specs/portfolio-mandate-v1/decisions/PM-DEC-003.toml",
        )
        if (directory / "decisions/PM-DEC-003.toml").read_bytes() != dec003_snapshot_bytes:
            errors.append("PM-DEC-003 v1 must remain byte-identical to its v0.5 consistency snapshot")
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        errors.append(f"PM-DEC-003 v0.5 consistency snapshot is unavailable: {exc}")
    errors.extend(validate_release_snapshot_members(ROOT, "portfolio-mandate-v0.6.zip", directory))

    criteria = acceptance.get("criteria", [])
    criteria_ids = [item.get("id") for item in criteria]
    if len(criteria_ids) < 20:
        errors.append("PM-001 requires at least 20 acceptance criteria")
    if len(criteria_ids) != len(set(criteria_ids)):
        errors.append("PM-001 acceptance IDs must be unique")
    missing_task_links = [item for item in criteria_ids if item not in tasks]
    if missing_task_links:
        errors.append(f"PM-001 acceptance IDs not traced from tasks: {missing_task_links}")

    requirement_ids = sorted(set(re.findall(r"PM-REQ-\d{3}", spec)))
    acceptance_requirements = {
        requirement
        for item in criteria
        for requirement in item.get("requirements", [])
    }
    missing_requirements = [item for item in requirement_ids if item not in acceptance_requirements]
    if missing_requirements:
        errors.append(f"PM-001 requirements not covered by acceptance: {missing_requirements}")

    defined_task_ids = re.findall(r"^- \[[ x]\] `(PM-TASK-\d{3})`", tasks, flags=re.MULTILINE)
    defined_requirement_ids = re.findall(r"^`(PM-REQ-\d{3})`:", spec, flags=re.MULTILINE)
    defined_decision_ids = re.findall(r"^\| `(PM-DEC-\d{3})` \|", spec, flags=re.MULTILINE)
    for label, identifiers in (
        ("task", defined_task_ids),
        ("requirement", defined_requirement_ids),
        ("decision", defined_decision_ids),
    ):
        if len(identifiers) != len(set(identifiers)):
            errors.append(f"PM-001 duplicate {label} IDs")

    if schema.get("additionalProperties") is not False:
        errors.append("PM-001 mandate schema must reject additional properties")
    schema_errors = validate_schema_subset(example, schema)
    if schema_errors:
        errors.extend(f"PM-001 mandate schema validation: {error}" for error in schema_errors)
    owner_properties = owner_schema.get("properties", {})
    if (
        owner_schema.get("additionalProperties") is not False
        or owner_properties.get("artifact_purpose", {}).get("const") != "NON_AUTHORIZING_DRAFT"
        or owner_properties.get("authorization_result", {}).get("const") != "DENY"
        or owner_properties.get("eligible_for_authorization", {}).get("const") is not False
        or owner_properties.get("decision", {}).get("const") != "DENY"
    ):
        errors.append("PM-001 owner manifest draft schema must remain strictly non-authorizing")
    required_fields = set(schema.get("required", []))
    missing_example_fields = sorted(required_fields - set(example))
    if missing_example_fields:
        errors.append(f"PM-001 example missing schema-required fields: {missing_example_fields}")

    allowed_statuses = set(schema["$defs"]["status"]["enum"])
    if example.get("status") not in allowed_statuses:
        errors.append("PM-001 example has an unknown mandate status")
    if example.get("artifact_purpose") != "NON_AUTHORIZING_DRAFT_EXAMPLE":
        errors.append("PM-001 example must identify itself as a non-authorizing draft")
    if example.get("status") != "BLOCKED" or example.get("authorization_result") != "DENY":
        errors.append("PM-001 example must remain BLOCKED until owner decisions")
    expected_lifecycle = ["DEVELOPMENT", "RESEARCH", "REPLAY", "DRY_RUN", "PAPER"]
    if (
        example.get("normative_overlay_status") != "ACTIVE_NON_CAPITAL"
        or example.get("permitted_non_capital_lifecycle") != expected_lifecycle
        or example.get("resolved_decision_refs")
        != ["decisions/PM-DEC-001.toml", "decisions/PM-DEC-002.toml"]
        or example.get("partially_resolved_decision_refs")
        != ["decisions/PM-DEC-003-v2.toml"]
        or example.get("historical_decision_refs") != ["decisions/PM-DEC-003.toml"]
        or example.get("validity_model") != "EXACT_VENUE_RISK_STAGE_PROFILE"
        or example.get("validity_profile_lookup") != "EXACTLY_ONE_ACTIVE_MATCH_NO_CROSS_VENUE_RISK_STAGE_FALLBACK"
        or example.get("calibration_authorization_effect") != "NONE"
        or example.get("level_a_validity_mode") != "LONG_LIVED_NON_CAPITAL"
        or example.get("level_b_allowed_validity_modes")
        != list(PM_DEC003_LEVEL_B_MODES)
        or example.get("numeric_validity_profile_status") != "OWNER_INPUT_REQUIRED"
        or example.get("real_capital_validity_eligible") is not False
    ):
        errors.append("PM-001 example does not encode the resolved and partial owner decisions")
    if (
        decision_001.get("decision_id") != "PM-DEC-001"
        or decision_001.get("selected_option") != 3
        or decision_001.get("applies_to") != expected_lifecycle
        or decision_001.get("authorization_effect") != "DENY_REAL_ORDERS"
        or decision_001.get("real_capital_authority") is not False
        or decision_001.get("trading_endpoint_access") is not False
        or decision_001.get("live_trading_enabled") is not False
        or decision_001.get("changes_governance_risk_policy") is not False
    ):
        errors.append("PM-DEC-001 record must activate only the non-capital overlay")
    errors.extend(validate_pm_dec002_record(decision_002, ROOT))
    errors.extend(validate_pm_dec003_record(decision_003, ROOT))
    errors.extend(validate_pm_dec003_v2_record(decision_003_v2, decision_003, ROOT))
    profile_errors = validate_validity_profile_draft(profile_example, profile_schema)
    errors.extend(f"PM-001 validity profile validation: {error}" for error in profile_errors)
    if profile_example.get("schema_sha256") != hashlib.sha256((directory / "validity-profiles/validity-profile.schema.json").read_bytes()).hexdigest():
        errors.append("validity profile schema ID/version/hash binding mismatch")
    if profile_example.get("decision_sha256") != hashlib.sha256((directory / "decisions/PM-DEC-003-v2.toml").read_bytes()).hexdigest():
        errors.append("validity profile decision hash binding mismatch")
    if example.get("live_trading_enabled") is not False:
        errors.append("PM-001 example must keep live trading disabled")

    expected_books = set(schema["$defs"]["capital_book_name"]["enum"])
    actual_books = {item.get("name") for item in example.get("capital_books", [])}
    if actual_books != expected_books:
        errors.append("PM-001 example must define exactly the six capital books")
    if any(item.get("real_trading_authority") is not False for item in example.get("capital_books", [])):
        errors.append("PM-001 draft example cannot grant real trading authority")
    for scope in example.get("scopes", []):
        if (
            scope.get("authorization_effect") != "DENY_REAL_ORDERS"
            or scope.get("trading_endpoint_access") is not False
            or scope.get("real_capital_authority") is not False
            or scope.get("capital_book") != "RESEARCH_PAPER"
            or scope.get("credential_profile_ref") != "NO_REAL_ORDER_CREDENTIAL"
        ):
            errors.append(f"PM-001 draft scope can imply real authority: {scope.get('scope_id')}")

    expected_risk_hierarchy = [
        "OWNER_HARD_CAP",
        "PROTECTION_STATE",
        "ADAPTIVE_ONLY_DOWN",
        "PORTFOLIO_ALLOCATOR",
        "STRATEGY_BOT_CAP",
        "ORDER_INTENT",
    ]
    if example.get("risk_hierarchy") != expected_risk_hierarchy:
        errors.append("PM-001 risk hierarchy is missing or out of order")

    policy_refs = {item.get("path"): item for item in example.get("policy_refs", [])}
    for relative in ("governance/approval-policy.toml", "governance/risk-policy.toml"):
        path = ROOT / relative
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if policy_refs.get(relative, {}).get("sha256") != actual_hash:
            errors.append(f"PM-001 policy hash mismatch: {relative}")

    decisions = [item.get("decision_id") for item in example.get("unresolved_decisions", [])]
    if decisions != [f"PM-DEC-{index:03d}" for index in range(4, 16)]:
        errors.append("PM-001 example must retain unresolved decisions PM-DEC-004 through PM-DEC-015")


def check_evals(errors: list[str]) -> None:
    suite = load_toml(ROOT / "evals/scenarios.toml")
    cases = suite.get("cases", [])
    if suite.get("minimum_pass_rate_pct") != 100:
        errors.append("safety eval minimum pass rate must remain 100%")
    if len(cases) < 10:
        errors.append("safety eval suite requires at least 10 cases")
    ids = [case.get("id") for case in cases]
    if len(ids) != len(set(ids)):
        errors.append("eval case IDs must be unique")
    invalid = [case.get("id") for case in cases if case.get("expected") not in {"PASS", "FAIL", "BLOCKED"}]
    if invalid:
        errors.append(f"eval cases have invalid expected verdict: {invalid}")
    unknown = [case.get("id") for case in cases if case.get("owner") not in REQUIRED_AGENTS]
    if unknown:
        errors.append(f"eval cases reference unknown agents: {unknown}")


def check_secrets(errors: list[str]) -> None:
    ignored_parts = {".git", "__pycache__", ".venv", "node_modules"}
    text_suffixes = {".md", ".toml", ".json", ".yml", ".yaml", ".py", ".go", ".ts", ".js"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        if any(part in ignored_parts for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"possible committed secret in {path.relative_to(ROOT)}")
                break
    forbidden = list(ROOT.rglob("*.session")) + list(ROOT.rglob(".env"))
    for path in forbidden:
        if ".git" not in path.parts:
            errors.append(f"forbidden secret-bearing file: {path.relative_to(ROOT)}")


def run_checks() -> list[str]:
    errors: list[str] = []
    check_required_files(errors)
    if errors:
        return errors
    check_parseable_files(errors)
    if errors:
        return errors
    check_agents(errors)
    check_risk_policy(errors)
    check_pipeline(errors)
    check_spec(errors)
    check_portfolio_mandate(errors)
    check_evals(errors)
    check_secrets(errors)
    return errors


def main() -> int:
    errors = run_checks()
    if errors:
        print("SELF-CHECK: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("SELF-CHECK: PASS (factory configuration, policies, contracts, traceability, secrets)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
