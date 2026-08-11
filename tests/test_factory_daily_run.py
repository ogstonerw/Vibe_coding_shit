from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

from factory.daily_run import execute_daily_run, exclusive_run_lock
from factory.decomposition import ChildTaskDraft, OwnerDecisionRequired, decompose_epic
from factory.models import (
    DailyConfig,
    Dependency,
    Epic,
    OwnerDecision,
    Registry,
    RepositoryState,
    RunRecord,
    Task,
)
from factory.preflight import run_preflight
from factory.registry import RegistryError, load_registry, validate_registry
from factory.state_machine import DailyRunStateMachine, InvalidTransition


ROOT = Path(__file__).resolve().parents[1]
RUN_DATE = date(2026, 8, 11)


def config() -> DailyConfig:
    return DailyConfig(
        schema_version=1,
        timezone="Europe/Moscow",
        max_tasks_per_day=1,
        max_parallel_writers=1,
        max_correction_loops=2,
        max_run_time_minutes=90,
        auto_merge=False,
        auto_product_approval=False,
        paper_authority=False,
        live_authority=False,
        allow_dirty=False,
        allowed_dirty_prefixes=("factory/artifacts/",),
        canonicalization="UTF8_LF_TEXT_RAW_BINARY_V1",
        active_core_manifest="docs/FROZEN_CORE_V12.sha256",
        active_core_manifest_sha256="0" * 64,
        pm_dec_007_manifest="docs/FROZEN_PM_DEC_007_HYBRID_V1.sha256",
        pm_dec_007_manifest_sha256="0" * 64,
        governance=(),
        routing={"high": ("architecture",), "medium": ("bounded_implementation",), "low": ("summary",)},
    )


def task(task_id: str, status: str = "READY", priority: int = 1, estimate: int = 30) -> Task:
    return Task(
        id=task_id,
        epic_id="EPIC-1",
        title=task_id,
        status=status,
        priority=priority,
        estimated_minutes=estimate,
        spec_path=f"specs/{task_id}/spec.md",
        acceptance_path=f"specs/{task_id}/acceptance.toml",
        capabilities=("registry",),
        mandatory_context=("AGENTS.md",),
        relevant_context=("factory/pipeline.toml",),
        frozen_context=("docs/FROZEN_CORE_V12.sha256",),
        skip_context=("historical reviews",),
    )


def registry(
    *tasks: Task,
    dependencies: tuple[Dependency, ...] = (),
    decisions: tuple[OwnerDecision, ...] = (),
    runs: tuple[RunRecord, ...] = (),
) -> Registry:
    return Registry(
        schema_version=1,
        epics=(Epic("EPIC-1", "Epic", "Approved goal", "OWNER_APPROVED", ("registry",)),),
        tasks=tuple(tasks),
        dependencies=dependencies,
        owner_decisions=decisions,
        runs=runs,
    )


def create_contracts(root: Path, *tasks: Task) -> None:
    for item in tasks:
        spec = root / item.spec_path
        acceptance = root / item.acceptance_path
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text("# spec\n", encoding="utf-8")
        acceptance.write_text('work_item = "test"\n', encoding="utf-8")


class StateMachineTests(unittest.TestCase):
    def test_success_path_and_terminal_state(self) -> None:
        machine = DailyRunStateMachine()
        for target in ("PREFLIGHT", "TASK_SELECTED", "PLAN_CREATED", "REPORT_CREATED"):
            machine.transition(target)
        self.assertTrue(machine.terminal)
        with self.assertRaises(InvalidTransition):
            machine.transition("PREFLIGHT")

    def test_invalid_transition_is_rejected(self) -> None:
        with self.assertRaises(InvalidTransition):
            DailyRunStateMachine().transition("PLAN_CREATED")


class RegistryValidationTests(unittest.TestCase):
    def test_unknown_status_and_duplicate_id_are_rejected(self) -> None:
        with self.assertRaisesRegex(RegistryError, "unknown Task status"):
            validate_registry(registry(task("T-1", "UNKNOWN")))
        with self.assertRaisesRegex(RegistryError, "duplicate Task"):
            validate_registry(registry(task("T-1"), task("T-1")))

    def test_missing_reference_cycle_and_multiple_active_runs_are_rejected(self) -> None:
        with self.assertRaisesRegex(RegistryError, "missing task"):
            validate_registry(registry(task("T-1"), dependencies=(Dependency("T-1", "MISSING"),)))
        one = task("T-1")
        two = task("T-2")
        with self.assertRaisesRegex(RegistryError, "dependency cycle"):
            validate_registry(
                registry(one, two, dependencies=(Dependency("T-1", "T-2"), Dependency("T-2", "T-1")))
            )
        runs = (
            RunRecord("R-1", "PREFLIGHT", RUN_DATE.isoformat()),
            RunRecord("R-2", "PLAN_CREATED", RUN_DATE.isoformat()),
        )
        with self.assertRaisesRegex(RegistryError, "more than one active run"):
            validate_registry(registry(one, runs=runs))

    def test_registry_path_escape_is_rejected(self) -> None:
        content = """
schema_version = 1
[[epics]]
id = "E"
title = "E"
goal = "G"
status = "OWNER_APPROVED"
approved_capabilities = []
[[tasks]]
id = "T"
epic_id = "E"
title = "T"
status = "READY"
priority = 1
estimated_minutes = 1
spec_path = "../outside.md"
acceptance_path = "acceptance.toml"
"""
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "registry.toml"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(RegistryError, "repository-relative"):
                load_registry(path)


class PreflightTests(unittest.TestCase):
    def test_ready_selection_is_stable_and_only_ready_is_selected(self) -> None:
        proposed = task("T-0", "PROPOSED", priority=0)
        second = task("T-2", priority=2)
        first = task("T-1", priority=1)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_contracts(root, first, second)
            result = run_preflight(
                registry(proposed, second, first),
                config(),
                root,
                RUN_DATE,
                repository_state=RepositoryState(True),
                integrity_issues=(),
            )
        self.assertEqual("TASK_SELECTED", result.status)
        self.assertEqual("T-1", result.selected_task.id)

    def test_dependencies_active_run_and_needs_owner_block(self) -> None:
        ready = task("T-1")
        parent = task("T-0", "REVIEW")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_contracts(root, ready)
            blocked = run_preflight(
                registry(parent, ready, dependencies=(Dependency("T-1", "T-0"),)),
                config(),
                root,
                RUN_DATE,
                repository_state=RepositoryState(True),
                integrity_issues=(),
            )
            active = run_preflight(
                registry(ready, runs=(RunRecord("R", "PREFLIGHT", RUN_DATE.isoformat()),)),
                config(),
                root,
                RUN_DATE,
                repository_state=RepositoryState(True),
                integrity_issues=(),
            )
            owner = run_preflight(
                registry(
                    ready,
                    decisions=(OwnerDecision("D", "T-1", "NEEDS_OWNER", "Owner choice"),),
                ),
                config(),
                root,
                RUN_DATE,
                repository_state=RepositoryState(True),
                integrity_issues=(),
            )
        self.assertEqual("BLOCKED", blocked.status)
        self.assertEqual("BLOCKED", active.status)
        self.assertEqual("NEEDS_OWNER", owner.status)

    def test_contract_repository_integrity_and_budgets_fail_closed(self) -> None:
        ready = task("T-1")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            missing = run_preflight(
                registry(ready), config(), root, RUN_DATE,
                repository_state=RepositoryState(True), integrity_issues=(),
            )
            create_contracts(root, ready)
            dirty = run_preflight(
                registry(ready), config(), root, RUN_DATE,
                repository_state=RepositoryState(True, ("unexpected.txt",)), integrity_issues=(),
            )
            uncertain = run_preflight(
                registry(ready), config(), root, RUN_DATE,
                repository_state=RepositoryState(False, error="git unavailable"), integrity_issues=(),
            )
            evidence = run_preflight(
                registry(ready), config(), root, RUN_DATE,
                repository_state=RepositoryState(True), integrity_issues=("frozen mismatch",),
            )
            runtime = run_preflight(
                registry(replace(ready, estimated_minutes=91)), config(), root, RUN_DATE,
                repository_state=RepositoryState(True), integrity_issues=(),
            )
            daily = run_preflight(
                registry(ready, runs=(RunRecord("R", "REPORT_CREATED", RUN_DATE.isoformat(), "T-1"),)),
                config(), root, RUN_DATE,
                repository_state=RepositoryState(True), integrity_issues=(),
            )
        for result in (missing, dirty, uncertain, evidence, runtime, daily):
            self.assertEqual("BLOCKED", result.status)

    def test_no_ready_task_returns_no_work(self) -> None:
        result = run_preflight(
            registry(task("T-1", "PROPOSED")), config(), Path.cwd(), RUN_DATE,
            repository_state=RepositoryState(True), integrity_issues=(),
        )
        self.assertEqual("NO_WORK", result.status)

    def test_ready_task_owner_gate_returns_needs_owner(self) -> None:
        gated = replace(task("T-1"), owner_gate_reasons=("external_service",))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_contracts(root, gated)
            result = run_preflight(
                registry(gated), config(), root, RUN_DATE,
                repository_state=RepositoryState(True), integrity_issues=(),
            )
        self.assertEqual("NEEDS_OWNER", result.status)
        self.assertIsNone(result.selected_task)


class DecompositionTests(unittest.TestCase):
    def test_only_approved_epic_and_capabilities_are_allowed(self) -> None:
        base = registry()
        draft = ChildTaskDraft("T-1", "Child", "READY", 1, 30, "Approved goal", ("registry",))
        created, dependencies = decompose_epic(base, "EPIC-1", (draft,))
        self.assertEqual(("T-1",), tuple(item.id for item in created))
        self.assertEqual((), dependencies)

        unapproved = replace(base, epics=(replace(base.epics[0], status="PROPOSED"),))
        with self.assertRaises(OwnerDecisionRequired):
            decompose_epic(unapproved, "EPIC-1", (draft,))
        expanded = replace(draft, capabilities=("registry", "new_market"))
        with self.assertRaises(OwnerDecisionRequired):
            decompose_epic(base, "EPIC-1", (expanded,))
        changed_goal = replace(draft, parent_goal="Different goal")
        with self.assertRaises(OwnerDecisionRequired):
            decompose_epic(base, "EPIC-1", (changed_goal,))

    def test_new_product_idea_can_only_be_proposed(self) -> None:
        draft = ChildTaskDraft(
            "T-1", "Idea", "READY", 1, 30, "Approved goal", (), is_new_product_idea=True
        )
        with self.assertRaises(OwnerDecisionRequired):
            decompose_epic(registry(), "EPIC-1", (draft,))


class DryRunIntegrationTests(unittest.TestCase):
    def test_dry_run_writes_deterministic_plan_and_complete_report(self) -> None:
        registry_text = """
schema_version = 1
[[epics]]
id = "EPIC-1"
title = "Epic"
goal = "Approved goal"
status = "OWNER_APPROVED"
approved_capabilities = ["registry"]
[[tasks]]
id = "T-1"
epic_id = "EPIC-1"
title = "Ready task"
status = "READY"
priority = 1
estimated_minutes = 30
spec_path = "specs/T-1/spec.md"
acceptance_path = "specs/T-1/acceptance.toml"
capabilities = ["registry"]
owner_gate_reasons = []
is_new_product_idea = false
mandatory_context = ["AGENTS.md"]
relevant_context = ["factory/pipeline.toml"]
frozen_context = ["docs/FROZEN_CORE_V12.sha256"]
skip_context = ["historical reviews"]
"""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "factory").mkdir()
            (root / "factory/daily_run.toml").write_text(
                (ROOT / "factory/daily_run.toml").read_text(encoding="utf-8"), encoding="utf-8"
            )
            (root / "factory/registry.toml").write_text(registry_text, encoding="utf-8")
            (root / "factory/pipeline.toml").write_text(
                (ROOT / "factory/pipeline.toml").read_text(encoding="utf-8"), encoding="utf-8"
            )
            ready = task("T-1")
            create_contracts(root, ready)
            first = execute_daily_run(
                root,
                run_date=RUN_DATE,
                repository_state=RepositoryState(True),
                integrity_issues=(),
            )
            plan_bytes = (root / first.plan_path).read_bytes()
            report_bytes = (root / first.report_path).read_bytes()
            second = execute_daily_run(
                root,
                run_date=RUN_DATE,
                repository_state=RepositoryState(True),
                integrity_issues=(),
            )
            self.assertEqual(plan_bytes, (root / second.plan_path).read_bytes())
            self.assertEqual(report_bytes, (root / second.report_path).read_bytes())
            report = report_bytes.decode("utf-8")
        self.assertEqual("REPORT_CREATED", first.status)
        self.assertEqual("T-1", first.selected_task_id)
        for heading in (
            "DATE", "RUN STATUS", "EPIC", "SELECTED TASK", "WHY THIS TASK", "DEPENDENCIES",
            "WHAT WOULD RUN NEXT", "OWNER DECISIONS", "BLOCKERS", "TOKEN PLAN", "AI_USAGE",
            "NEXT ACTION",
        ):
            self.assertIn(f"## {heading}", report)
        self.assertIn("## AI_USAGE\n0", report)
        self.assertIn("FACTORY-001A will not invoke a coding agent", report)

    def test_exclusive_lock_blocks_second_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with exclusive_run_lock(root, "factory/artifacts"):
                with self.assertRaises(FileExistsError):
                    with exclusive_run_lock(root, "factory/artifacts"):
                        self.fail("nested lock unexpectedly acquired")


if __name__ == "__main__":
    unittest.main()
