"""Canonical frozen/governance evidence checks for FACTORY-001A."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .models import DailyConfig


MANIFEST_LINE = re.compile(r"^([0-9a-f]{64})\s+\*?(.+)$")
BINARY_SUFFIXES = frozenset({".zip", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".sqlite", ".db"})


def safe_repo_path(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    resolved_root = root.resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"path escapes repository: {relative}") from exc
    return candidate


def canonical_bytes(path: Path) -> bytes:
    raw = path.read_bytes()
    if path.suffix.lower() in BINARY_SUFFIXES:
        return raw
    text = raw.decode("utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def canonical_sha256(path: Path) -> str:
    return hashlib.sha256(canonical_bytes(path)).hexdigest()


def parse_manifest(root: Path, manifest_path: str) -> tuple[tuple[str, str], ...]:
    path = safe_repo_path(root, manifest_path)
    entries: list[tuple[str, str]] = []
    seen: set[str] = set()
    for number, line in enumerate(canonical_bytes(path).decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        match = MANIFEST_LINE.fullmatch(line)
        if not match:
            raise ValueError(f"invalid manifest line {manifest_path}:{number}")
        digest, relative = match.groups()
        relative = relative.strip().replace("\\", "/")
        if relative in seen:
            raise ValueError(f"duplicate manifest path: {relative}")
        safe_repo_path(root, relative)
        seen.add(relative)
        entries.append((relative, digest))
    if not entries:
        raise ValueError(f"empty manifest: {manifest_path}")
    return tuple(entries)


def verify_manifest(root: Path, manifest_path: str, expected_manifest_sha256: str) -> tuple[str, ...]:
    errors: list[str] = []
    path = safe_repo_path(root, manifest_path)
    try:
        actual_manifest = canonical_sha256(path)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return (f"cannot read manifest {manifest_path}: {exc}",)
    if actual_manifest != expected_manifest_sha256:
        errors.append(f"manifest hash mismatch: {manifest_path}")
    try:
        entries = parse_manifest(root, manifest_path)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return tuple(errors + [str(exc)])
    for relative, expected in entries:
        target = safe_repo_path(root, relative)
        if not target.is_file():
            errors.append(f"missing frozen artifact: {relative}")
            continue
        try:
            actual = canonical_sha256(target)
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"cannot hash frozen artifact {relative}: {exc}")
            continue
        if actual != expected:
            errors.append(f"frozen artifact mismatch: {relative}")
    return tuple(errors)


def verify_integrity(root: Path, config: DailyConfig) -> tuple[str, ...]:
    errors = list(
        verify_manifest(root, config.active_core_manifest, config.active_core_manifest_sha256)
    )
    errors.extend(verify_manifest(root, config.pm_dec_007_manifest, config.pm_dec_007_manifest_sha256))
    for evidence in config.governance:
        path = safe_repo_path(root, evidence.path)
        if not path.is_file():
            errors.append(f"missing governance artifact: {evidence.path}")
            continue
        try:
            actual = canonical_sha256(path)
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"cannot hash governance artifact {evidence.path}: {exc}")
            continue
        if actual != evidence.sha256:
            errors.append(f"governance artifact mismatch: {evidence.path}")
    return tuple(errors)
