"""Strict loader for immutable FACTORY-001A daily limits."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from .models import DailyConfig, GovernanceEvidence


class ConfigurationError(ValueError):
    """Raised for unsafe or ambiguous daily-run configuration."""


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha(value: object, field: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise ConfigurationError(f"{field} must be a lowercase SHA-256")
    return value


def _relative(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"{field} must be a non-empty path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ConfigurationError(f"{field} must remain repository-relative")
    return value.replace("\\", "/")


def load_daily_config(path: Path) -> DailyConfig:
    try:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigurationError(f"cannot load daily config {path}: {exc}") from exc
    required_exact = {
        "schema_version": 1,
        "timezone": "Europe/Moscow",
        "max_tasks_per_day": 1,
        "max_parallel_writers": 1,
        "max_correction_loops": 2,
        "max_run_time_minutes": 90,
        "auto_merge": False,
        "auto_product_approval": False,
        "paper_authority": False,
        "live_authority": False,
    }
    for key, expected in required_exact.items():
        if raw.get(key) != expected:
            raise ConfigurationError(f"{key} must remain {expected!r}")
    repository = raw.get("repository", {})
    if repository.get("allow_dirty") is not False:
        raise ConfigurationError("repository.allow_dirty must remain false")
    prefixes = repository.get("allowed_dirty_prefixes", [])
    if not isinstance(prefixes, list) or any(not isinstance(item, str) or not item for item in prefixes):
        raise ConfigurationError("allowed_dirty_prefixes must be non-empty strings")
    integrity = raw.get("integrity", {})
    if integrity.get("canonicalization") != "UTF8_LF_TEXT_RAW_BINARY_V1":
        raise ConfigurationError("unsupported integrity canonicalization")
    governance_raw = integrity.get("governance", [])
    if not isinstance(governance_raw, list) or not governance_raw:
        raise ConfigurationError("at least one governance hash is required")
    governance = tuple(
        GovernanceEvidence(
            path=_relative(item.get("path"), f"integrity.governance[{index}].path"),
            sha256=_sha(item.get("sha256"), f"integrity.governance[{index}].sha256"),
        )
        for index, item in enumerate(governance_raw)
    )
    routing_raw = raw.get("routing", {})
    routing: dict[str, tuple[str, ...]] = {}
    for level in ("high", "medium", "low"):
        values = routing_raw.get(level)
        if not isinstance(values, list) or any(not isinstance(item, str) or not item for item in values):
            raise ConfigurationError(f"routing.{level} must be a list of non-empty strings")
        routing[level] = tuple(values)
    return DailyConfig(
        schema_version=1,
        timezone="Europe/Moscow",
        max_tasks_per_day=1,
        max_parallel_writers=1,
        max_correction_loops=2,
        max_run_time_minutes=90,
        auto_merge=False,
        auto_product_approval=False,
        paper_authority=False,
        live_authority=False,
        allow_dirty=False,
        allowed_dirty_prefixes=tuple(prefix.replace("\\", "/") for prefix in prefixes),
        canonicalization="UTF8_LF_TEXT_RAW_BINARY_V1",
        active_core_manifest=_relative(integrity.get("active_core_manifest"), "active_core_manifest"),
        active_core_manifest_sha256=_sha(
            integrity.get("active_core_manifest_sha256"), "active_core_manifest_sha256"
        ),
        pm_dec_007_manifest=_relative(integrity.get("pm_dec_007_manifest"), "pm_dec_007_manifest"),
        pm_dec_007_manifest_sha256=_sha(
            integrity.get("pm_dec_007_manifest_sha256"), "pm_dec_007_manifest_sha256"
        ),
        governance=governance,
        routing=routing,
    )
