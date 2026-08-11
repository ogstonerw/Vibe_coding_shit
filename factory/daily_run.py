"""CLI entry point for the deterministic FACTORY-001A daily dry-run."""

from __future__ import annotations

import argparse
import os
import sys
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Iterator
from zoneinfo import ZoneInfo

from .configuration import ConfigurationError, load_daily_config
from .integrity import safe_repo_path
from .models import RepositoryState, RunOutcome
from .planning import build_execution_plan, render_owner_report, write_plan, write_report
from .preflight import run_preflight
from .registry import RegistryError, load_registry
from .state_machine import DailyRunStateMachine


DEFAULT_REGISTRY = "factory/registry.toml"
DEFAULT_CONFIG = "factory/daily_run.toml"
DEFAULT_OUTPUT = "factory/artifacts"


@contextmanager
def exclusive_run_lock(root: Path, output_dir: str) -> Iterator[None]:
    directory = safe_repo_path(root, output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    lock_path = directory / ".daily-run.lock"
    descriptor: int | None = None
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.write(descriptor, b"FACTORY-001A\n")
        os.close(descriptor)
        descriptor = None
        yield
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _date(value: str | None, timezone: str) -> date:
    if value is None:
        return datetime.now(ZoneInfo(timezone)).date()
    return date.fromisoformat(value)


def execute_daily_run(
    root: Path,
    *,
    registry_path: str = DEFAULT_REGISTRY,
    config_path: str = DEFAULT_CONFIG,
    output_dir: str = DEFAULT_OUTPUT,
    run_date: date | None = None,
    repository_state: RepositoryState | None = None,
    integrity_issues: tuple[str, ...] | None = None,
) -> RunOutcome:
    root = root.resolve()
    config = load_daily_config(safe_repo_path(root, config_path))
    registry = load_registry(safe_repo_path(root, registry_path))
    effective_date = run_date or datetime.now(ZoneInfo(config.timezone)).date()
    machine = DailyRunStateMachine()
    machine.transition("PREFLIGHT")
    preflight = run_preflight(
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
    parser.add_argument("--registry", default=DEFAULT_REGISTRY)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT)
    parser.add_argument("--date", help="deterministic Moscow date in YYYY-MM-DD")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.dry_run:
        print("FACTORY-001A refuses to run without --dry-run", file=sys.stderr)
        return 2
    root = Path(args.root).resolve()
    try:
        config = load_daily_config(safe_repo_path(root, args.config))
        run_date = _date(args.date, config.timezone)
        with exclusive_run_lock(root, args.output_dir):
            outcome = execute_daily_run(
                root,
                registry_path=args.registry,
                config_path=args.config,
                output_dir=args.output_dir,
                run_date=run_date,
            )
    except FileExistsError:
        print("FACTORY-001A BLOCKED: another daily-run lock exists", file=sys.stderr)
        return 3
    except (ConfigurationError, RegistryError, OSError, ValueError) as exc:
        print(f"FACTORY-001A FAILED: {exc}", file=sys.stderr)
        return 1
    print(
        f"FACTORY-001A {outcome.status}: task={outcome.selected_task_id or 'NONE'} "
        f"report={outcome.report_path} ai_usage=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
