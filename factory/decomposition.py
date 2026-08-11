"""Owner-bounded Epic decomposition contract for future planners."""

from __future__ import annotations

from dataclasses import dataclass

from .models import OWNER_GATE_CATEGORIES, Dependency, Registry, Task


class OwnerDecisionRequired(ValueError):
    """Raised when decomposition would exceed approved Owner scope."""


@dataclass(frozen=True)
class ChildTaskDraft:
    id: str
    title: str
    status: str
    priority: int
    estimated_minutes: int
    parent_goal: str
    capabilities: tuple[str, ...]
    owner_gate_reasons: tuple[str, ...] = ()
    is_new_product_idea: bool = False
    spec_path: str = ""
    acceptance_path: str = ""


def decompose_epic(
    registry: Registry,
    epic_id: str,
    drafts: tuple[ChildTaskDraft, ...],
    dependencies: tuple[Dependency, ...] = (),
) -> tuple[tuple[Task, ...], tuple[Dependency, ...]]:
    try:
        epic = registry.epic(epic_id)
    except StopIteration as exc:
        raise OwnerDecisionRequired(f"missing Epic: {epic_id}") from exc
    if epic.status != "OWNER_APPROVED":
        raise OwnerDecisionRequired(f"Epic {epic_id} is {epic.status}, expected OWNER_APPROVED")
    existing = {task.id for task in registry.tasks}
    created: list[Task] = []
    draft_ids = [draft.id for draft in drafts]
    if len(draft_ids) != len(set(draft_ids)) or existing.intersection(draft_ids):
        raise ValueError("child task IDs must be unique and new")
    approved = set(epic.approved_capabilities)
    for draft in drafts:
        if draft.parent_goal != epic.goal:
            raise OwnerDecisionRequired(f"{draft.id} changes the approved Epic goal")
        expansion = set(draft.capabilities) - approved
        if expansion:
            raise OwnerDecisionRequired(f"{draft.id} expands capabilities: {sorted(expansion)}")
        unknown_gates = set(draft.owner_gate_reasons) - OWNER_GATE_CATEGORIES
        if unknown_gates:
            raise ValueError(f"{draft.id} has unknown Owner gates: {sorted(unknown_gates)}")
        if draft.owner_gate_reasons:
            raise OwnerDecisionRequired(f"{draft.id} requires Owner: {sorted(draft.owner_gate_reasons)}")
        if draft.status not in {"PROPOSED", "READY"}:
            raise ValueError(f"planner child {draft.id} must be PROPOSED or READY")
        if draft.is_new_product_idea and draft.status != "PROPOSED":
            raise OwnerDecisionRequired(f"new product idea {draft.id} must remain PROPOSED")
        created.append(
            Task(
                id=draft.id,
                epic_id=epic_id,
                title=draft.title,
                status=draft.status,
                priority=draft.priority,
                estimated_minutes=draft.estimated_minutes,
                spec_path=draft.spec_path,
                acceptance_path=draft.acceptance_path,
                capabilities=draft.capabilities,
                is_new_product_idea=draft.is_new_product_idea,
            )
        )
    all_ids = existing | set(draft_ids)
    for dependency in dependencies:
        if dependency.task_id not in draft_ids:
            raise ValueError(f"decomposition dependency target must be a new child: {dependency.task_id}")
        if dependency.depends_on not in all_ids or dependency.task_id == dependency.depends_on:
            raise ValueError(f"invalid child dependency: {dependency}")
    return tuple(created), dependencies
