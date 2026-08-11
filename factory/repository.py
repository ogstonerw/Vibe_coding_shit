"""Read-only Git working-tree probe used by deterministic preflight."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .models import RepositoryState


def probe_repository(root: Path) -> RepositoryState:
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return RepositoryState(False, error=str(exc))
    if completed.returncode != 0:
        detail = completed.stderr.strip() or f"git status exited {completed.returncode}"
        return RepositoryState(False, error=detail)
    paths: list[str] = []
    for line in completed.stdout.splitlines():
        if len(line) < 4:
            return RepositoryState(False, error=f"malformed git status line: {line!r}")
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path.strip('"').replace("\\", "/"))
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
