"""Read-only Git working-tree probe used by deterministic preflight."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .models import RepositoryState


def probe_repository(root: Path) -> RepositoryState:
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            cwd=root,
            check=False,
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return RepositoryState(False, error=str(exc))
    if completed.returncode != 0:
        detail = os.fsdecode(completed.stderr).strip() or f"git status exited {completed.returncode}"
        return RepositoryState(False, error=detail)
    records = completed.stdout.split(b"\0")
    if not records or records[-1] != b"":
        return RepositoryState(False, error="malformed NUL-delimited git status")
    records.pop()
    paths: list[str] = []
    index = 0
    while index < len(records):
        entry = records[index]
        if len(entry) < 4 or entry[2:3] != b" " or not entry[3:]:
            return RepositoryState(False, error=f"malformed git status record: {entry!r}")
        status = entry[:2]
        paths.append(os.fsdecode(entry[3:]))
        index += 1
        if b"R" in status or b"C" in status:
            if index >= len(records) or not records[index]:
                return RepositoryState(False, error="rename/copy status is missing its source path")
            paths.append(os.fsdecode(records[index]))
            index += 1
    return RepositoryState(True, tuple(sorted(paths)))


def disallowed_dirty_paths(state: RepositoryState, allowed_prefixes: tuple[str, ...]) -> tuple[str, ...]:
    if not state.known:
        return (f"repository state unknown: {state.error}",)
    normalized = tuple(prefix.replace("\\", "/") for prefix in allowed_prefixes)
    return tuple(
        path
        for path in state.dirty_paths
        if not any(path.startswith(prefix) for prefix in normalized)
    )
