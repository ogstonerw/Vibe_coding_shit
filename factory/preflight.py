"""Fail-closed deterministic preflight and READY-task selection."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from .integrity import safe_repo_path, verify_integrity
from .models import (
    ACTIVE_RUN_STATUSES,
    CheckResult,
    DailyConfig,
    PreflightResult,
    Registry,
    RepositoryState,
    Task,
)
from .repository import disallowed_dirty_paths, probe_repository


def _result(
    status: str,
    checks: list[CheckResult],
    *,
    task: Task | None = None,
    blockers: tuple[str, ...] = (),
    decisions: tuple[str, ...] = (),
) -> PreflightResult:
    return PreflightResult(status, task, tuple(checks), blockers, decisions)


def _contracts(root: Path, task: Task) -> tuple[str, ...]:
    errors: list[str] = []
    if not task.spec_path:
        errors.append(f"{task.id} has no spec_path")
    if not task.acceptance_path:
        errors.append(f"{task.id} has no acceptance_path")
    for label, relative in (("spec", task.spec_path), ("acceptance", task.acceptance_path)):
        if not relative:
            continue
        try:
            path = safe_repo_path(root, relative)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not path.is_file():
            errors.append(f"{task.id} missing {label}: {relative}")
    return tuple(errors)


def _dependency_blockers(registry: Registry, task: Task) -> tuple[str, ...]:
    blockers: list[str] = []
    for dependency in registry.dependencies_for(task.id):
        parent = registry.task(dependency.depends_on)
        if parent.status != "DONE":
            blockers.append(f"{task.id} depends on {parent.id}={parent.status}, expected DONE")
    return tuple(blockers)


def run_preflight(
    registry: Registry,
    config: DailyConfig,
    root: Path,
    run_date: date,
    *,
    repository_state: RepositoryState | None = None,
    integrity_issues: tuple[str, ...] | None = None,
) -> PreflightResult:
    checks: list[CheckResult] = []

    active = tuple(run.id for run in registry.runs if run.status in ACTIVE_RUN_STATUSES)
    checks.append(CheckResult("single_active_run", not active, "none" if not active else ", ".join(active)))
    if active:
        return _result("BLOCKED", checks, blockers=(f"active run exists: {', '.join(active)}",))

    unresolved = tuple(
        f"{decision.id}: {decision.summary}"
        for decision in registry.owner_decisions
        if decision.status == "NEEDS_OWNER"
    )
    unresolved += tuple(
        f"{task.id}: task status NEEDS_OWNER"
        for task in registry.tasks
        if task.status == "NEEDS_OWNER"
    )
    checks.append(
        CheckResult(
            "unresolved_owner_decisions",
            not unresolved,
            "none" if not unresolved else "; ".join(unresolved),
        )
    )
    if unresolved:
        return _result("NEEDS_OWNER", checks, decisions=unresolved)

    if integrity_issues is None:
        integrity_issues = verify_integrity(root, config)
    checks.append(
        CheckResult(
            "governance_and_frozen_evidence",
            not integrity_issues,
            "pass" if not integrity_issues else "; ".join(integrity_issues),
        )
    )
    if integrity_issues:
        return _result("BLOCKED", checks, blockers=integrity_issues)

    state = repository_state if repository_state is not None else probe_repository(root)
    dirty = disallowed_dirty_paths(state, config.allowed_dirty_prefixes)
    checks.append(
        CheckResult(
            "repository_state",
            not dirty,
            "clean/admissible" if not dirty else "; ".join(dirty),
        )
    )
    if dirty:
        return _result("BLOCKED", checks, blockers=dirty)

    selected_today = tuple(
        run.id for run in registry.runs if run.date == run_date.isoformat() and run.selected_task_id
    )
    daily_ok = len(selected_today) < config.max_tasks_per_day
    checks.append(
        CheckResult(
            "daily_task_budget",
            daily_ok,
            f"selected={len(selected_today)}, max={config.max_tasks_per_day}",
        )
    )
    if not daily_ok:
        return _result("BLOCKED", checks, blockers=("daily task budget exhausted",))

    ready = sorted(
        (task for task in registry.tasks if task.status == "READY"),
        key=lambda item: (item.priority, item.id),
    )
    checks.append(CheckResult("ready_task_exists", bool(ready), f"count={len(ready)}"))
    if not ready:
        return _result("NO_WORK", checks)

    blocked_candidates: list[str] = []
    for task in ready:
        if task.owner_gate_reasons:
            reasons = tuple(f"{task.id}: {reason}" for reason in task.owner_gate_reasons)
            checks.append(CheckResult("owner_decision_gate", False, "; ".join(reasons)))
            return _result("NEEDS_OWNER", checks, decisions=reasons)
        contract_errors = _contracts(root, task)
        if contract_errors:
            blocked_candidates.extend(contract_errors)
            continue
        dependency_errors = _dependency_blockers(registry, task)
        if dependency_errors:
            blocked_candidates.extend(dependency_errors)
            continue
        if task.estimated_minutes > config.max_run_time_minutes:
            blocked_candidates.append(
                f"{task.id} estimate {task.estimated_minutes} exceeds {config.max_run_time_minutes} minutes"
            )
            continue
        checks.extend(
            (
                CheckResult("task_contract", True, f"{task.spec_path}; {task.acceptance_path}"),
                CheckResult("dependencies_done", True, task.id),
                CheckResult(
                    "runtime_budget",
                    True,
                    f"{task.estimated_minutes}/{config.max_run_time_minutes}",
                ),
                CheckResult("task_selected", True, task.id),
            )
        )
        return _result("TASK_SELECTED", checks, task=task)

    checks.append(CheckResult("eligible_ready_task", False, "; ".join(blocked_candidates)))
    return _result("BLOCKED", checks, blockers=tuple(blocked_candidates))
