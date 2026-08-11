"""Deterministic daily-run state machine."""

from __future__ import annotations

from dataclasses import dataclass

from .models import RUN_STATUSES, STOP_RUN_STATUSES


class InvalidTransition(ValueError):
    """Raised when a run attempts a transition outside FACTORY-001A."""


TRANSITIONS = {
    "SCHEDULED": frozenset({"PREFLIGHT", "FAILED"}),
    "PREFLIGHT": frozenset({"TASK_SELECTED", "NO_WORK", "BLOCKED", "NEEDS_OWNER", "FAILED"}),
    "TASK_SELECTED": frozenset({"PLAN_CREATED", "BLOCKED", "NEEDS_OWNER", "FAILED"}),
    "PLAN_CREATED": frozenset({"REPORT_CREATED", "FAILED"}),
    "REPORT_CREATED": frozenset(),
    "NO_WORK": frozenset(),
    "BLOCKED": frozenset(),
    "NEEDS_OWNER": frozenset(),
    "FAILED": frozenset(),
}


@dataclass
class DailyRunStateMachine:
    status: str = "SCHEDULED"

    def __post_init__(self) -> None:
        if self.status not in RUN_STATUSES:
            raise InvalidTransition(f"unknown initial state: {self.status}")

    @property
    def terminal(self) -> bool:
        return self.status == "REPORT_CREATED" or self.status in STOP_RUN_STATUSES

    def transition(self, target: str) -> str:
        if target not in RUN_STATUSES:
            raise InvalidTransition(f"unknown target state: {target}")
        if target not in TRANSITIONS[self.status]:
            raise InvalidTransition(f"invalid transition: {self.status} -> {target}")
        self.status = target
        return self.status
