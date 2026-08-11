#!/usr/bin/env python3
"""Install the versioned Codex project configuration into .codex/ safely."""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "config" / "codex"
TARGET = ROOT / ".codex"


def existing_conflicts() -> list[Path]:
    conflicts: list[Path] = []
    if not TARGET.exists():
        return conflicts
    for source in SOURCE.rglob("*"):
        if not source.is_file():
            continue
        relative = source.relative_to(SOURCE)
        target = TARGET / relative
        if target.exists() and (not target.is_file() or not filecmp.cmp(source, target, shallow=False)):
            conflicts.append(relative)
    return conflicts


def install(force: bool = False) -> int:
    conflicts = existing_conflicts()
    if conflicts and not force:
        print("INSTALL: BLOCKED; existing .codex files differ:")
        for path in conflicts:
            print(f"- {path}")
        print("Review them, then rerun with --force only if replacement is intended.")
        return 2

    TARGET.mkdir(parents=True, exist_ok=True)
    for source in SOURCE.rglob("*"):
        if not source.is_file():
            continue
        relative = source.relative_to(SOURCE)
        target = TARGET / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    print(f"INSTALL: PASS ({TARGET})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="replace conflicting project Codex files")
    args = parser.parse_args()
    return install(force=args.force)


if __name__ == "__main__":
    sys.exit(main())

