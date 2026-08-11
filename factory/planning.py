"""Deterministic execution-plan and Owner Report generation."""

from __future__ import annotations

import json
import os
import tempfile
import tomllib
from pathlib import Path
from typing import Any

from .integrity import safe_repo_path
from .models import DailyConfig, PreflightResult, Registry, Task


def pipeline_preview(root: Path) -> tuple[dict[str, Any], ...]:
    path = root / "factory/pipeline.toml"
    with path.open("rb") as handle:
        pipeline = tomllib.load(handle)
    preview: list[dict[str, Any]] = []
    for stage in pipeline.get("stages", []):
        preview.append(
            {
                "id": stage.get("id", ""),
                "agents": tuple(stage.get("agents", [])),
                "mode": stage.get("mode", ""),
            }
        )
    return tuple(preview)


def build_execution_plan(
    root: Path,
    registry: Registry,
    config: DailyConfig,
    task: Task,
    run_date: str,
) -> dict[str, Any]:
    epic = registry.epic(task.epic_id)
    dependencies = tuple(dependency.depends_on for dependency in registry.dependencies_for(task.id))
    return {
        "schema_version": 1,
        "date": run_date,
        "run_mode": "DRY_RUN",
        "epic": {"id": epic.id, "title": epic.title},
        "selected_task": {"id": task.id, "title": task.title, "priority": task.priority},
        "why_this_task": "highest-priority eligible READY task after deterministic preflight",
        "dependencies": dependencies,
        "limits": {
            "max_tasks_per_day": config.max_tasks_per_day,
            "max_parallel_writers": config.max_parallel_writers,
            "max_correction_loops": config.max_correction_loops,
            "max_run_time_minutes": config.max_run_time_minutes,
        },
        "token_plan": {
            "MANDATORY": task.mandatory_context,
            "RELEVANT": task.relevant_context,
            "FROZEN": task.frozen_context,
            "SKIP": task.skip_context,
        },
        "agent_routing_policy": config.routing,
        "pipeline_preview_only": pipeline_preview(root),
        "authority": {
            "auto_merge": config.auto_merge,
            "auto_product_approval": config.auto_product_approval,
            "paper_authority": config.paper_authority,
            "live_authority": config.live_authority,
            "coding_agent_invocation": False,
            "commit": False,
            "push": False,
            "pull_request": False,
        },
        "ai_usage": 0,
        "next_action": "Owner reviews the plan; FACTORY-001A invokes no coding agent.",
    }


def _display_list(values: tuple[str, ...] | list[str]) -> str:
    return "NONE" if not values else "\n".join(f"- {value}" for value in values)


def render_owner_report(
    registry: Registry,
    config: DailyConfig,
    preflight: PreflightResult,
    run_date: str,
    run_status: str,
    plan: dict[str, Any] | None,
) -> str:
    task = preflight.selected_task
    epic = registry.epic(task.epic_id) if task else None
    dependencies = (
        tuple(dependency.depends_on for dependency in registry.dependencies_for(task.id)) if task else ()
    )
    decisions = tuple(
        f"{item.id} [{item.status}] — {item.summary}"
        for item in sorted(registry.owner_decisions, key=lambda item: item.id)
    )
    if plan:
        what_next = plan["pipeline_preview_only"][0]["id"] if plan["pipeline_preview_only"] else "NONE"
        why = plan["why_this_task"]
    else:
        what_next = "NONE"
        why = "No task was authorized for planning."
    if run_status == "NEEDS_OWNER":
        next_action = "Owner resolves the listed decision; the pipeline remains stopped."
    elif run_status == "BLOCKED":
        next_action = "Correct the deterministic blocker and rerun preflight."
    elif run_status == "NO_WORK":
        next_action = "Owner approves work; then a contracted task may be marked READY."
    elif run_status == "REPORT_CREATED":
        next_action = "Owner reviews this plan. FACTORY-001A will not invoke a coding agent."
    else:
        next_action = "Investigate the failed deterministic run."
    token_plan = plan["token_plan"] if plan else {"MANDATORY": (), "RELEVANT": (), "FROZEN": (), "SKIP": ()}
    token_lines = []
    for label in ("MANDATORY", "RELEVANT", "FROZEN", "SKIP"):
        values = token_plan[label]
        token_lines.append(f"- {label}: {', '.join(values) if values else 'NONE'}")
    blockers = tuple(preflight.blockers) + tuple(preflight.owner_decisions)
    return "\n".join(
        (
            "# FACTORY-001A Owner Report",
            "",
            "## DATE",
            run_date,
            "",
            "## RUN STATUS",
            run_status,
            "",
            "## EPIC",
            f"{epic.id} — {epic.title}" if epic else "NONE",
            "",
            "## SELECTED TASK",
            f"{task.id} — {task.title}" if task else "NONE",
            "",
            "## WHY THIS TASK",
            why,
            "",
            "## DEPENDENCIES",
            _display_list(dependencies),
            "",
            "## WHAT WOULD RUN NEXT",
            what_next,
            "",
            "## OWNER DECISIONS",
            _display_list(decisions),
            "",
            "## BLOCKERS",
            _display_list(blockers),
            "",
            "## TOKEN PLAN",
            "\n".join(token_lines),
            "",
            "## AI_USAGE",
            "0",
            "",
            "## NEXT ACTION",
            next_action,
            "",
        )
    )


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def write_plan(root: Path, output_dir: str, run_date: str, plan: dict[str, Any]) -> Path:
    directory = safe_repo_path(root, output_dir)
    path = directory / f"{run_date}-execution-plan.json"
    content = json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    atomic_write_text(path, content)
    return path


def write_report(root: Path, output_dir: str, run_date: str, report: str) -> Path:
    directory = safe_repo_path(root, output_dir)
    path = directory / f"{run_date}-owner-report.md"
    atomic_write_text(path, report)
    return path
