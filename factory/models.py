"""Typed registry and daily-run models for FACTORY-001A."""

from __future__ import annotations

from dataclasses import dataclass, field


TASK_STATUSES = frozenset(
    {
        "IDEA",
        "PROPOSED",
        "OWNER_APPROVED",
        "READY",
        "RUNNING",
        "REVIEW",
        "NEEDS_OWNER",
        "BLOCKED",
        "FAILED",
        "DONE",
        "SUPERSEDED",
    }
)

RUN_STATUSES = frozenset(
    {
        "SCHEDULED",
        "PREFLIGHT",
        "TASK_SELECTED",
        "PLAN_CREATED",
        "REPORT_CREATED",
        "NO_WORK",
        "BLOCKED",
        "NEEDS_OWNER",
        "FAILED",
    }
)

ACTIVE_RUN_STATUSES = frozenset({"SCHEDULED", "PREFLIGHT", "TASK_SELECTED", "PLAN_CREATED"})
STOP_RUN_STATUSES = frozenset({"NO_WORK", "BLOCKED", "NEEDS_OWNER", "FAILED"})

OWNER_GATE_CATEGORIES = frozenset(
    {
        "new_fundamental_entity",
        "system_boundary",
        "external_service",
        "auth_secrets",
        "exchange",
        "market",
        "lifecycle",
        "risk_architecture",
        "global_navigation",
        "paper_live",
        "financial_authority",
        "governance",
    }
)


@dataclass(frozen=True)
class Epic:
    id: str
    title: str
    goal: str
    status: str
    approved_capabilities: tuple[str, ...] = ()


@dataclass(frozen=True)
class Task:
    id: str
    epic_id: str
    title: str
    status: str
    priority: int
    estimated_minutes: int
    spec_path: str = ""
    acceptance_path: str = ""
    capabilities: tuple[str, ...] = ()
    owner_gate_reasons: tuple[str, ...] = ()
    is_new_product_idea: bool = False
    mandatory_context: tuple[str, ...] = ()
    relevant_context: tuple[str, ...] = ()
    frozen_context: tuple[str, ...] = ()
    skip_context: tuple[str, ...] = ()


@dataclass(frozen=True)
class Dependency:
    task_id: str
    depends_on: str


@dataclass(frozen=True)
class OwnerDecision:
    id: str
    subject_id: str
    status: str
    summary: str


@dataclass(frozen=True)
class RunRecord:
    id: str
    status: str
    date: str
    selected_task_id: str = ""


@dataclass(frozen=True)
class Registry:
    schema_version: int
    epics: tuple[Epic, ...] = ()
    tasks: tuple[Task, ...] = ()
    dependencies: tuple[Dependency, ...] = ()
    owner_decisions: tuple[OwnerDecision, ...] = ()
    runs: tuple[RunRecord, ...] = ()

    def epic(self, epic_id: str) -> Epic:
        return next(item for item in self.epics if item.id == epic_id)

    def task(self, task_id: str) -> Task:
        return next(item for item in self.tasks if item.id == task_id)

    def dependencies_for(self, task_id: str) -> tuple[Dependency, ...]:
        return tuple(item for item in self.dependencies if item.task_id == task_id)


@dataclass(frozen=True)
class GovernanceEvidence:
    path: str
    sha256: str


@dataclass(frozen=True)
class DailyConfig:
    schema_version: int
    timezone: str
    max_tasks_per_day: int
    max_parallel_writers: int
    max_correction_loops: int
    max_run_time_minutes: int
    auto_merge: bool
    auto_product_approval: bool
    paper_authority: bool
    live_authority: bool
    allow_dirty: bool
    allowed_dirty_prefixes: tuple[str, ...]
    canonicalization: str
    active_core_manifest: str
    active_core_manifest_sha256: str
    pm_dec_007_manifest: str
    pm_dec_007_manifest_sha256: str
    governance: tuple[GovernanceEvidence, ...]
    routing: dict[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class RepositoryState:
    known: bool
    dirty_paths: tuple[str, ...] = ()
    error: str = ""


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class PreflightResult:
    status: str
    selected_task: Task | None
    checks: tuple[CheckResult, ...]
    blockers: tuple[str, ...] = ()
    owner_decisions: tuple[str, ...] = ()


@dataclass(frozen=True)
class RunOutcome:
    date: str
    status: str
    selected_task_id: str
    plan_path: str
    report_path: str
