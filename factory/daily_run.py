"""CLI entry point for the deterministic FACTORY-001A daily dry-run."""

from __future__ import annotations

import argparse
import errno
import os
import sys
from contextlib import AbstractContextManager, contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Iterator
from zoneinfo import ZoneInfo

from .configuration import ConfigurationError, load_daily_config
from .github_history import (
    GitHubHistoryError,
    github_actions_enabled,
    verify_github_daily_history,
)
from .integrity import safe_repo_path, verify_integrity
from .models import DailyConfig, Registry, RepositoryState, RunOutcome
from .planning import build_execution_plan, render_owner_report, write_plan, write_report
from .preflight import _evaluate_preflight
from .registry import RegistryError, load_registry
from .repository import probe_repository
from .run_history import RunHistoryError, claim_daily_run
from .state_machine import DailyRunStateMachine


DEFAULT_REGISTRY = "factory/registry.toml"
DEFAULT_CONFIG = "factory/daily_run.toml"
DEFAULT_OUTPUT = "factory/artifacts"


class RunLockError(OSError):
    """Raised when platform lock ownership is unsupported or ambiguous."""


def _contention_error(exc: OSError) -> FileExistsError | None:
    contention_codes = {errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK}
    if exc.errno in contention_codes or getattr(exc, "winerror", None) in {33, 36}:
        return FileExistsError(errno.EEXIST, "another daily-run lock holder exists")
    return None


def _ensure_windows_lock_byte(descriptor: int) -> None:
    if os.fstat(descriptor).st_size == 0:
        os.lseek(descriptor, 0, os.SEEK_SET)
        if os.write(descriptor, b"\0") != 1:
            raise RunLockError("could not initialize persistent Windows lock byte")
        os.fsync(descriptor)
    os.lseek(descriptor, 0, os.SEEK_SET)


def _acquire_platform_lock(
    descriptor: int,
    *,
    platform: str | None = None,
    posix_module=None,
    windows_module=None,
) -> None:
    selected = platform or os.name
    try:
        if selected == "posix":
            if posix_module is None:
                import fcntl as posix_module

            posix_module.flock(descriptor, posix_module.LOCK_EX | posix_module.LOCK_NB)
            return
        if selected == "nt":
            if windows_module is None:
                import msvcrt as windows_module

            _ensure_windows_lock_byte(descriptor)
            windows_module.locking(descriptor, windows_module.LK_NBLCK, 1)
            return
    except OSError as exc:
        contention = _contention_error(exc)
        if contention is not None:
            raise contention from exc
        raise RunLockError(f"ambiguous {selected} daily-run lock acquisition") from exc
    raise RunLockError(f"unsupported daily-run lock platform: {selected}")


def _release_platform_lock(
    descriptor: int,
    *,
    platform: str | None = None,
    posix_module=None,
    windows_module=None,
) -> None:
    selected = platform or os.name
    try:
        if selected == "posix":
            if posix_module is None:
                import fcntl as posix_module

            posix_module.flock(descriptor, posix_module.LOCK_UN)
            return
        if selected == "nt":
            if windows_module is None:
                import msvcrt as windows_module

            os.lseek(descriptor, 0, os.SEEK_SET)
            windows_module.locking(descriptor, windows_module.LK_UNLCK, 1)
            return
    except OSError as exc:
        raise RunLockError(f"ambiguous {selected} daily-run lock release") from exc
    raise RunLockError(f"unsupported daily-run lock platform: {selected}")


@contextmanager
def _exclusive_run_lock_for_test(root: Path, output_dir: str) -> Iterator[None]:
    directory = safe_repo_path(root, output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    lock_path = directory / ".daily-run.lock"
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    acquired = False
    try:
        _acquire_platform_lock(descriptor)
        acquired = True
        yield
    finally:
        try:
            if acquired:
                _release_platform_lock(descriptor)
        finally:
            os.close(descriptor)


def exclusive_run_lock(root: Path) -> AbstractContextManager[None]:
    """Return the canonical production lock context."""

    return _exclusive_run_lock_for_test(root, DEFAULT_OUTPUT)


def _date(value: str | None, timezone: str) -> date:
    if value is None:
        return datetime.now(ZoneInfo(timezone)).date()
    return date.fromisoformat(value)


def execute_daily_run(
    root: Path,
    *,
    owner_id: str,
    run_date: date | None = None,
) -> RunOutcome:
    """Execute production planning from canonical repository inputs and probes."""

    root = root.resolve()
    effective_date = run_date or datetime.now(ZoneInfo("Europe/Moscow")).date()
    with exclusive_run_lock(root):
        config = load_daily_config(safe_repo_path(root, DEFAULT_CONFIG))
        registry = load_registry(safe_repo_path(root, DEFAULT_REGISTRY), root=root)
        if github_actions_enabled():
            verify_github_daily_history(effective_date)
        claim_daily_run(root, effective_date, owner_id)
        repository_state = probe_repository(root)
        integrity_issues = verify_integrity(root, config)
        return _execute_daily_run_core(
            root,
            registry=registry,
            config=config,
            output_dir=DEFAULT_OUTPUT,
            effective_date=effective_date,
            repository_state=repository_state,
            integrity_issues=integrity_issues,
        )


def _execute_daily_run_for_test(
    root: Path,
    *,
    registry_path: str = DEFAULT_REGISTRY,
    config_path: str = DEFAULT_CONFIG,
    output_dir: str = DEFAULT_OUTPUT,
    run_date: date,
    repository_state: RepositoryState,
    integrity_issues: tuple[str, ...],
) -> RunOutcome:
    """Private deterministic test boundary; never used by the CLI."""

    root = root.resolve()
    config = load_daily_config(safe_repo_path(root, config_path))
    registry = load_registry(safe_repo_path(root, registry_path), root=root)
    return _execute_daily_run_core(
        root,
        registry=registry,
        config=config,
        output_dir=output_dir,
        effective_date=run_date,
        repository_state=repository_state,
        integrity_issues=integrity_issues,
    )


def _execute_daily_run_core(
    root: Path,
    *,
    registry: Registry,
    config: DailyConfig,
    output_dir: str,
    effective_date: date,
    repository_state: RepositoryState,
    integrity_issues: tuple[str, ...],
) -> RunOutcome:
    machine = DailyRunStateMachine()
    machine.transition("PREFLIGHT")
    preflight = _evaluate_preflight(
        registry,
        config,
        root,
        effective_date,
        repository_state=repository_state,
        integrity_issues=integrity_issues,
    )
    plan = None
    plan_path = ""
    report_path = ""
    if preflight.status == "TASK_SELECTED":
        machine.transition("TASK_SELECTED")
        assert preflight.selected_task is not None
        plan = build_execution_plan(
            root,
            registry,
            config,
            preflight.selected_task,
            effective_date.isoformat(),
        )
        written_plan = write_plan(root, output_dir, effective_date.isoformat(), plan)
        plan_path = written_plan.relative_to(root).as_posix()
        machine.transition("PLAN_CREATED")
        target_status = "REPORT_CREATED"
        report = render_owner_report(
            registry, config, preflight, effective_date.isoformat(), target_status, plan
        )
        written_report = write_report(root, output_dir, effective_date.isoformat(), report)
        report_path = written_report.relative_to(root).as_posix()
        machine.transition(target_status)
    else:
        target_status = preflight.status
        report = render_owner_report(
            registry, config, preflight, effective_date.isoformat(), target_status, None
        )
        written_report = write_report(root, output_dir, effective_date.isoformat(), report)
        report_path = written_report.relative_to(root).as_posix()
        machine.transition(target_status)
    return RunOutcome(
        date=effective_date.isoformat(),
        status=machine.status,
        selected_task_id=preflight.selected_task.id if preflight.selected_task else "",
        plan_path=plan_path,
        report_path=report_path,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="required: never invoke a coding agent")
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--date", help="deterministic Moscow date in YYYY-MM-DD")
    parser.add_argument("--owner-id", required=True, help="stable invocation owner ID")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.dry_run:
        print("FACTORY-001A refuses to run without --dry-run", file=sys.stderr)
        return 2
    root = Path(args.root).resolve()
    try:
        run_date = _date(args.date, "Europe/Moscow")
        outcome = execute_daily_run(
            root,
            run_date=run_date,
            owner_id=args.owner_id,
        )
    except FileExistsError:
        print("FACTORY-001A BLOCKED: another daily-run lock exists", file=sys.stderr)
        return 3
    except (
        ConfigurationError,
        GitHubHistoryError,
        RegistryError,
        RunHistoryError,
        OSError,
        ValueError,
    ) as exc:
        print(f"FACTORY-001A FAILED: {exc}", file=sys.stderr)
        return 1
    print(
        f"FACTORY-001A {outcome.status}: task={outcome.selected_task_id or 'NONE'} "
        f"report={outcome.report_path} ai_usage=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
