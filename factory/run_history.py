"""Durable, immutable daily-run claims for FACTORY-001A."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .integrity import safe_repo_path


SCHEMA_VERSION = 1
MOSCOW_TIMEZONE = "Europe/Moscow"
CANONICAL_OUTPUT = "factory/artifacts"
OWNER_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}$")


class RunHistoryError(ValueError):
    """Raised when a daily claim is conflicting, malformed, or unsafe."""


@dataclass(frozen=True)
class DailyClaim:
    schema_version: int
    date: str
    owner_id: str


def _validate_owner_id(owner_id: str) -> None:
    if not isinstance(owner_id, str) or not OWNER_ID_RE.fullmatch(owner_id):
        raise RunHistoryError("owner_id must be 1..128 safe non-whitespace characters")


def _claim_bytes(claim: DailyClaim) -> bytes:
    return (
        json.dumps(
            {
                "date": claim.date,
                "owner_id": claim.owner_id,
                "schema_version": claim.schema_version,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _claim_path(root: Path, output_dir: str, run_date: date) -> Path:
    directory = safe_repo_path(root, output_dir) / "run-history"
    return directory / f"{run_date.isoformat()}.json"


def load_daily_claim(path: Path, expected_date: date) -> DailyClaim:
    """Strictly load a canonical claim; any ambiguity fails closed."""

    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_json_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunHistoryError(f"cannot load daily claim {path}: {exc}") from exc
    if not isinstance(value, dict) or set(value) != {"schema_version", "date", "owner_id"}:
        raise RunHistoryError(f"malformed daily claim {path}: unexpected fields")
    schema_version = value.get("schema_version")
    claim_date = value.get("date")
    owner_id = value.get("owner_id")
    if type(schema_version) is not int or schema_version != SCHEMA_VERSION:
        raise RunHistoryError(f"malformed daily claim {path}: unsupported schema_version")
    if not isinstance(claim_date, str):
        raise RunHistoryError(f"malformed daily claim {path}: date must be text")
    try:
        parsed_date = date.fromisoformat(claim_date)
    except ValueError as exc:
        raise RunHistoryError(f"malformed daily claim {path}: invalid date") from exc
    if parsed_date != expected_date or claim_date != expected_date.isoformat():
        raise RunHistoryError(
            f"malformed daily claim {path}: expected date {expected_date.isoformat()}"
        )
    _validate_owner_id(owner_id)
    claim = DailyClaim(SCHEMA_VERSION, claim_date, owner_id)
    if raw != _claim_bytes(claim):
        raise RunHistoryError(f"malformed daily claim {path}: non-canonical encoding")
    return claim


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise RunHistoryError(f"malformed daily claim: duplicate field {key}")
        value[key] = item
    return value


def _claim_daily_run_for_test(
    root: Path, output_dir: str, run_date: date, owner_id: str
) -> DailyClaim:
    """Private deterministic seam for alternate test namespaces."""

    _validate_owner_id(owner_id)
    path = _claim_path(root.resolve(), output_dir, run_date)
    path.parent.mkdir(parents=True, exist_ok=True)
    claim = DailyClaim(SCHEMA_VERSION, run_date.isoformat(), owner_id)
    content = _claim_bytes(claim)
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        existing = load_daily_claim(path, run_date)
        if existing.owner_id != owner_id:
            raise RunHistoryError(
                f"production date {run_date.isoformat()} is already claimed by another owner"
            )
        return existing
    try:
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        if descriptor is not None:
            os.close(descriptor)
        # A partial or uncertain exclusive claim intentionally remains fail-closed.
        raise
    return claim


def claim_daily_run(root: Path, run_date: date, owner_id: str) -> DailyClaim:
    """Claim a production date only in the canonical artifact namespace."""

    return _claim_daily_run_for_test(root, CANONICAL_OUTPUT, run_date, owner_id)


def _run_date(value: str | None) -> date:
    if value is None:
        return datetime.now(ZoneInfo(MOSCOW_TIMEZONE)).date()
    return date.fromisoformat(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--date", help="Moscow production date in YYYY-MM-DD")
    parser.add_argument("--owner-id", required=True, help="stable invocation owner ID")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        run_date = _run_date(args.date)
        claim = claim_daily_run(Path(args.root), run_date, args.owner_id)
    except (OSError, RunHistoryError, ValueError) as exc:
        print(f"FACTORY-001A CLAIM BLOCKED: {exc}", file=sys.stderr)
        return 1
    print(f"FACTORY-001A CLAIMED: date={claim.date} owner={claim.owner_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
