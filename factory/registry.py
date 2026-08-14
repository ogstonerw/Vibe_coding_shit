"""Strict TOML loading and validation for the FACTORY-001A registry."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from .models import (
    ACTIVE_RUN_STATUSES,
    OWNER_GATE_CATEGORIES,
    RUN_STATUSES,
    TASK_STATUSES,
    Dependency,
    Epic,
    OwnerDecision,
    Registry,
    RunRecord,
    Task,
)


class RegistryError(ValueError):
    """Raised when registry input is ambiguous or invalid."""


TOP_LEVEL_KEYS = {"schema_version", "epics", "tasks", "dependencies", "owner_decisions", "runs"}
EPIC_KEYS = {"id", "title", "goal", "status", "approved_capabilities"}
TASK_KEYS = {
    "id",
    "epic_id",
    "title",
    "status",
    "priority",
    "estimated_minutes",
    "spec_path",
    "acceptance_path",
    "capabilities",
    "owner_gate_reasons",
    "is_new_product_idea",
    "mandatory_context",
    "relevant_context",
    "frozen_context",
    "skip_context",
}
DEPENDENCY_KEYS = {"task_id", "depends_on"}
DECISION_KEYS = {"id", "subject_id", "status", "summary"}
RUN_KEYS = {"id", "status", "date", "selected_task_id"}


def _reject_unknown(data: dict[str, Any], allowed: set[str], location: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise RegistryError(f"unknown keys at {location}: {unknown}")


def _required_text(data: dict[str, Any], key: str, location: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RegistryError(f"{location}.{key} must be non-empty text")
    return value


def _text_tuple(data: dict[str, Any], key: str, location: str) -> tuple[str, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise RegistryError(f"{location}.{key} must be a list of non-empty strings")
    if len(value) != len(set(value)):
        raise RegistryError(f"{location}.{key} contains duplicates")
    return tuple(value)


def _safe_relative(path: str, location: str) -> None:
    if not path:
        return
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise RegistryError(f"{location} must remain repository-relative")


def load_registry(path: Path, *, root: Path | None = None) -> Registry:
    try:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise RegistryError(f"cannot load registry {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise RegistryError("registry root must be a table")
    _reject_unknown(raw, TOP_LEVEL_KEYS, "registry")
    if raw.get("schema_version") != 1:
        raise RegistryError("registry.schema_version must be 1")

    epics: list[Epic] = []
    for index, item in enumerate(raw.get("epics", [])):
        location = f"epics[{index}]"
        _reject_unknown(item, EPIC_KEYS, location)
        epics.append(
            Epic(
                id=_required_text(item, "id", location),
                title=_required_text(item, "title", location),
                goal=_required_text(item, "goal", location),
                status=_required_text(item, "status", location),
                approved_capabilities=_text_tuple(item, "approved_capabilities", location),
            )
        )

    tasks: list[Task] = []
    for index, item in enumerate(raw.get("tasks", [])):
        location = f"tasks[{index}]"
        _reject_unknown(item, TASK_KEYS, location)
        priority = item.get("priority")
        estimate = item.get("estimated_minutes")
        if not isinstance(priority, int) or isinstance(priority, bool) or priority < 0:
            raise RegistryError(f"{location}.priority must be a non-negative integer")
        if not isinstance(estimate, int) or isinstance(estimate, bool) or estimate <= 0:
            raise RegistryError(f"{location}.estimated_minutes must be a positive integer")
        spec_path = item.get("spec_path", "")
        acceptance_path = item.get("acceptance_path", "")
        if not isinstance(spec_path, str) or not isinstance(acceptance_path, str):
            raise RegistryError(f"{location} contract paths must be strings")
        _safe_relative(spec_path, f"{location}.spec_path")
        _safe_relative(acceptance_path, f"{location}.acceptance_path")
        new_idea = item.get("is_new_product_idea", False)
        if not isinstance(new_idea, bool):
            raise RegistryError(f"{location}.is_new_product_idea must be boolean")
        tasks.append(
            Task(
                id=_required_text(item, "id", location),
                epic_id=_required_text(item, "epic_id", location),
                title=_required_text(item, "title", location),
                status=_required_text(item, "status", location),
                priority=priority,
                estimated_minutes=estimate,
                spec_path=spec_path,
                acceptance_path=acceptance_path,
                capabilities=_text_tuple(item, "capabilities", location),
                owner_gate_reasons=_text_tuple(item, "owner_gate_reasons", location),
                is_new_product_idea=new_idea,
                mandatory_context=_text_tuple(item, "mandatory_context", location),
                relevant_context=_text_tuple(item, "relevant_context", location),
                frozen_context=_text_tuple(item, "frozen_context", location),
                skip_context=_text_tuple(item, "skip_context", location),
            )
        )
        for field in ("mandatory_context", "relevant_context", "frozen_context"):
            for context_path in getattr(tasks[-1], field):
                _safe_relative(context_path, f"{location}.{field}")

    dependencies: list[Dependency] = []
    for index, item in enumerate(raw.get("dependencies", [])):
        location = f"dependencies[{index}]"
        _reject_unknown(item, DEPENDENCY_KEYS, location)
        dependencies.append(
            Dependency(
                task_id=_required_text(item, "task_id", location),
                depends_on=_required_text(item, "depends_on", location),
            )
        )

    decisions: list[OwnerDecision] = []
    for index, item in enumerate(raw.get("owner_decisions", [])):
        location = f"owner_decisions[{index}]"
        _reject_unknown(item, DECISION_KEYS, location)
        decisions.append(
            OwnerDecision(
                id=_required_text(item, "id", location),
                subject_id=_required_text(item, "subject_id", location),
                status=_required_text(item, "status", location),
                summary=_required_text(item, "summary", location),
            )
        )

    runs: list[RunRecord] = []
    for index, item in enumerate(raw.get("runs", [])):
        location = f"runs[{index}]"
        _reject_unknown(item, RUN_KEYS, location)
        selected = item.get("selected_task_id", "")
        if not isinstance(selected, str):
            raise RegistryError(f"{location}.selected_task_id must be text")
        runs.append(
            RunRecord(
                id=_required_text(item, "id", location),
                status=_required_text(item, "status", location),
                date=_required_text(item, "date", location),
                selected_task_id=selected,
            )
        )

    registry = Registry(1, tuple(epics), tuple(tasks), tuple(dependencies), tuple(decisions), tuple(runs))
    validate_registry(registry, root=root)
    return registry


def _unique(values: list[str], kind: str) -> None:
    if len(values) != len(set(values)):
        raise RegistryError(f"duplicate {kind} id")


def _check_dependency_cycles(registry: Registry) -> None:
    graph: dict[str, list[str]] = {task.id: [] for task in registry.tasks}
    for dependency in registry.dependencies:
        graph[dependency.task_id].append(dependency.depends_on)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise RegistryError(f"dependency cycle contains {task_id}")
        if task_id in visited:
            return
        visiting.add(task_id)
        for parent in graph[task_id]:
            visit(parent)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in sorted(graph):
        visit(task_id)


def validate_registry(registry: Registry, *, root: Path | None = None) -> None:
    epic_ids = [item.id for item in registry.epics]
    task_ids = [item.id for item in registry.tasks]
    decision_ids = [item.id for item in registry.owner_decisions]
    run_ids = [item.id for item in registry.runs]
    _unique(epic_ids, "Epic")
    _unique(task_ids, "Task")
    _unique(decision_ids, "Owner Decision")
    _unique(run_ids, "Run")
    epic_set = set(epic_ids)
    epic_by_id = {epic.id: epic for epic in registry.epics}
    task_set = set(task_ids)
    subject_set = epic_set | task_set

    for epic in registry.epics:
        if epic.status not in TASK_STATUSES:
            raise RegistryError(f"unknown Epic status: {epic.status}")
    for task in registry.tasks:
        if task.status not in TASK_STATUSES:
            raise RegistryError(f"unknown Task status: {task.status}")
        if task.epic_id not in epic_set:
            raise RegistryError(f"task {task.id} references missing Epic {task.epic_id}")
        if task.status == "READY":
            epic = epic_by_id[task.epic_id]
            if epic.status != "OWNER_APPROVED":
                raise RegistryError(
                    f"READY task {task.id} requires OWNER_APPROVED Epic {epic.id}"
                )
            extra_capabilities = sorted(set(task.capabilities) - set(epic.approved_capabilities))
            if extra_capabilities:
                raise RegistryError(
                    f"READY task {task.id} exceeds Epic {epic.id} approved capabilities: "
                    f"{extra_capabilities}"
                )
            if not task.spec_path or not task.acceptance_path:
                raise RegistryError(f"READY task {task.id} requires spec and acceptance contracts")
            if root is not None:
                referenced_paths = (
                    ("spec", task.spec_path),
                    ("acceptance", task.acceptance_path),
                    *(("mandatory_context", item) for item in task.mandatory_context),
                    *(("relevant_context", item) for item in task.relevant_context),
                    *(("frozen_context", item) for item in task.frozen_context),
                )
                for label, relative in referenced_paths:
                    candidate = (root.resolve() / relative).resolve()
                    try:
                        candidate.relative_to(root.resolve())
                    except ValueError as exc:
                        raise RegistryError(
                            f"READY task {task.id} {label} escapes repository: {relative}"
                        ) from exc
                    if not candidate.is_file():
                        raise RegistryError(
                            f"READY task {task.id} missing {label}: {relative}"
                        )
        unknown_gates = set(task.owner_gate_reasons) - OWNER_GATE_CATEGORIES
        if unknown_gates:
            raise RegistryError(f"task {task.id} has unknown Owner gates: {sorted(unknown_gates)}")
        if task.is_new_product_idea and task.status not in {"IDEA", "PROPOSED", "NEEDS_OWNER"}:
            raise RegistryError(f"new product idea {task.id} must remain IDEA/PROPOSED/NEEDS_OWNER")
    seen_dependencies: set[tuple[str, str]] = set()
    for dependency in registry.dependencies:
        key = (dependency.task_id, dependency.depends_on)
        if key in seen_dependencies:
            raise RegistryError(f"duplicate dependency {key}")
        seen_dependencies.add(key)
        if dependency.task_id not in task_set or dependency.depends_on not in task_set:
            raise RegistryError(f"dependency references missing task: {key}")
        if dependency.task_id == dependency.depends_on:
            raise RegistryError(f"task {dependency.task_id} cannot depend on itself")
    _check_dependency_cycles(registry)
    for decision in registry.owner_decisions:
        if decision.status not in TASK_STATUSES:
            raise RegistryError(f"unknown Owner Decision status: {decision.status}")
        if decision.subject_id not in subject_set:
            raise RegistryError(f"Owner Decision {decision.id} references missing subject")
    for run in registry.runs:
        if run.status not in RUN_STATUSES:
            raise RegistryError(f"unknown Run status: {run.status}")
        if run.selected_task_id and run.selected_task_id not in task_set:
            raise RegistryError(f"Run {run.id} references missing selected task")
    active = [run.id for run in registry.runs if run.status in ACTIVE_RUN_STATUSES]
    if len(active) > 1:
        raise RegistryError(f"more than one active run: {active}")
