from __future__ import annotations

import os
import tempfile
import subprocess
import sys
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path
from unittest.mock import patch

from factory.configuration import ConfigurationError, load_daily_config
from factory.daily_run import (
    RunLockError,
    _acquire_platform_lock,
    _execute_daily_run_for_test,
    _release_platform_lock,
    execute_daily_run,
    exclusive_run_lock,
)
from factory.decomposition import ChildTaskDraft, OwnerDecisionRequired, decompose_epic
from factory.integrity import canonical_sha256, verify_integrity
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
from factory.preflight import _run_preflight_for_test
from factory.registry import RegistryError, load_registry, validate_registry
from factory.repository import disallowed_dirty_paths, probe_repository
from factory.run_history import RunHistoryError, claim_daily_run, load_daily_claim
from factory.state_machine import DailyRunStateMachine, InvalidTransition


ROOT = Path(__file__).resolve().parents[1]
RUN_DATE = date(2026, 8, 11)
run_preflight = _run_preflight_for_test

LOCK_ATTEMPT_SCRIPT = """
import sys
from pathlib import Path
from factory.daily_run import exclusive_run_lock
try:
    with exclusive_run_lock(Path(sys.argv[1])):
        pass
except FileExistsError:
    raise SystemExit(3)
"""

LOCK_RELEASE_WITHOUT_OWNERSHIP_SCRIPT = """
import os
import sys
from pathlib import Path
from factory.daily_run import _release_platform_lock
path = Path(sys.argv[1]) / "factory/artifacts/.daily-run.lock"
descriptor = os.open(path, os.O_RDWR)
try:
    try:
        _release_platform_lock(descriptor)
    except OSError:
        pass
finally:
    os.close(descriptor)
"""

PUBLIC_RUN_ATTEMPT_SCRIPT = """
import sys
from datetime import date
from pathlib import Path
from factory.daily_run import execute_daily_run
try:
    execute_daily_run(
        Path(sys.argv[1]),
        owner_id="competing-public-run",
        run_date=date.fromisoformat(sys.argv[2]),
    )
except FileExistsError:
    raise SystemExit(3)
"""


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
        pm_dec_007_manifest="docs/FROZEN_PM_DEC_007_HYBRID_V2.sha256",
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
        for relative in item.mandatory_context + item.relevant_context + item.frozen_context:
            evidence = root / relative
            evidence.parent.mkdir(parents=True, exist_ok=True)
            if not evidence.exists():
                evidence.write_text("test evidence\n", encoding="utf-8")


def create_production_fixture(root: Path) -> None:
    (root / "factory").mkdir()
    (root / "evidence").mkdir()
    (root / "governance").mkdir()
    (root / "evidence/core.txt").write_text("core\n", encoding="utf-8")
    (root / "evidence/pm.txt").write_text("pm\n", encoding="utf-8")
    (root / "governance/approval-policy.toml").write_text(
        'schema_version = 1\n', encoding="utf-8"
    )
    core_digest = canonical_sha256(root / "evidence/core.txt")
    pm_digest = canonical_sha256(root / "evidence/pm.txt")
    (root / "docs").mkdir()
    (root / "docs/core.sha256").write_text(
        f"{core_digest}  *evidence/core.txt\n", encoding="utf-8"
    )
    (root / "docs/pm.sha256").write_text(
        f"{pm_digest}  *evidence/pm.txt\n", encoding="utf-8"
    )
    governance_digest = canonical_sha256(root / "governance/approval-policy.toml")
    core_manifest_digest = canonical_sha256(root / "docs/core.sha256")
    pm_manifest_digest = canonical_sha256(root / "docs/pm.sha256")
    (root / "factory/daily_run.toml").write_text(
        f'''schema_version = 1
timezone = "Europe/Moscow"
max_tasks_per_day = 1
max_parallel_writers = 1
max_correction_loops = 2
max_run_time_minutes = 90
auto_merge = false
auto_product_approval = false
paper_authority = false
live_authority = false

[repository]
allow_dirty = false
allowed_dirty_prefixes = ["factory/artifacts/"]

[integrity]
canonicalization = "UTF8_LF_TEXT_RAW_BINARY_V1"
active_core_manifest = "docs/core.sha256"
active_core_manifest_sha256 = "{core_manifest_digest}"
pm_dec_007_manifest = "docs/pm.sha256"
pm_dec_007_manifest_sha256 = "{pm_manifest_digest}"

[[integrity.governance]]
path = "governance/approval-policy.toml"
sha256 = "{governance_digest}"

[routing]
high = ["architecture"]
medium = ["bounded_implementation"]
low = ["summary"]
''',
        encoding="utf-8",
    )
    (root / "factory/registry.toml").write_text("schema_version = 1\n", encoding="utf-8")
    (root / "factory/pipeline.toml").write_text("schema_version = 1\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, timeout=10)
    subprocess.run(["git", "add", "."], cwd=root, check=True, timeout=10)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=FACTORY Test",
            "-c",
            "user.email=factory@example.invalid",
            "commit",
            "-q",
            "-m",
            "fixture",
        ],
        cwd=root,
        check=True,
        timeout=10,
    )


def create_injected_authority_fixture(root: Path) -> tuple[Path, Path]:
    injected_root = root / "factory/artifacts/injected-authority"
    injected_root.mkdir(parents=True)
    (injected_root / "spec.md").write_text("# injected spec\n", encoding="utf-8")
    (injected_root / "acceptance.toml").write_text(
        'work_item = "INJECTED"\n', encoding="utf-8"
    )
    registry_path = injected_root / "registry.toml"
    registry_path.write_text(
        '''schema_version = 1
[[epics]]
id = "INJECTED-EPIC"
title = "Injected Epic"
goal = "Create an unauthorized plan"
status = "OWNER_APPROVED"
approved_capabilities = ["registry"]
[[tasks]]
id = "INJECTED-TASK"
epic_id = "INJECTED-EPIC"
title = "Injected READY task"
status = "READY"
priority = 1
estimated_minutes = 1
spec_path = "factory/artifacts/injected-authority/spec.md"
acceptance_path = "factory/artifacts/injected-authority/acceptance.toml"
capabilities = ["registry"]
owner_gate_reasons = []
is_new_product_idea = false
mandatory_context = []
relevant_context = []
frozen_context = []
skip_context = []
''',
        encoding="utf-8",
    )
    config_path = injected_root / "daily_run.toml"
    config_path.write_bytes((root / "factory/daily_run.toml").read_bytes())
    return registry_path, config_path


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

    def test_ready_requires_existing_owner_approved_epic_and_capability_subset(self) -> None:
        ready = task("T-1")
        unapproved = replace(
            registry(ready),
            epics=(Epic("EPIC-1", "Epic", "Approved goal", "READY", ("registry",)),),
        )
        with self.assertRaisesRegex(RegistryError, "requires OWNER_APPROVED Epic"):
            validate_registry(unapproved)

        expanded = replace(ready, capabilities=("registry", "new_capability"))
        with self.assertRaisesRegex(RegistryError, "exceeds Epic"):
            validate_registry(registry(expanded))

        missing = replace(registry(ready), epics=())
        with self.assertRaisesRegex(RegistryError, "references missing Epic"):
            validate_registry(missing)

    def test_registry_validation_requires_ready_contracts_and_context_evidence(self) -> None:
        ready = task("T-1")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(RegistryError, "missing spec"):
                validate_registry(registry(ready), root=root)
            create_contracts(root, ready)
            validate_registry(registry(ready), root=root)
            (root / "AGENTS.md").unlink()
            with self.assertRaisesRegex(RegistryError, "missing mandatory_context"):
                validate_registry(registry(ready), root=root)


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

    def test_direct_ready_cannot_bypass_epic_authority_or_context_evidence(self) -> None:
        ready = task("T-1")
        cases = (
            replace(
                registry(ready),
                epics=(Epic("EPIC-1", "Epic", "Approved goal", "READY", ("registry",)),),
            ),
            registry(replace(ready, capabilities=("registry", "extra"))),
            replace(registry(ready), epics=()),
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_contracts(root, ready)
            for invalid in cases:
                result = run_preflight(
                    invalid,
                    config(),
                    root,
                    RUN_DATE,
                    repository_state=RepositoryState(True),
                    integrity_issues=(),
                )
                self.assertEqual("BLOCKED", result.status)
                self.assertIsNone(result.selected_task)

            (root / "AGENTS.md").unlink()
            missing_evidence = run_preflight(
                registry(ready),
                config(),
                root,
                RUN_DATE,
                repository_state=RepositoryState(True),
                integrity_issues=(),
            )
        self.assertEqual("BLOCKED", missing_evidence.status)
        self.assertIn("missing mandatory_context", missing_evidence.blockers[0])


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
            first = _execute_daily_run_for_test(
                root,
                run_date=RUN_DATE,
                repository_state=RepositoryState(True),
                integrity_issues=(),
            )
            plan_bytes = (root / first.plan_path).read_bytes()
            report_bytes = (root / first.report_path).read_bytes()
            second = _execute_daily_run_for_test(
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

    def _invoke_lock_process(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-c", LOCK_ATTEMPT_SCRIPT, str(root)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_persistent_handle_lock_blocks_and_cannot_be_released_by_competitor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock_path = root / "factory/artifacts/.daily-run.lock"
            with exclusive_run_lock(root):
                blocked = self._invoke_lock_process(root)
                self.assertEqual(3, blocked.returncode, blocked.stderr)
                release = subprocess.run(
                    [sys.executable, "-c", LOCK_RELEASE_WITHOUT_OWNERSHIP_SCRIPT, str(root)],
                    cwd=ROOT,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(0, release.returncode, release.stderr)
                still_blocked = self._invoke_lock_process(root)
                self.assertEqual(3, still_blocked.returncode, still_blocked.stderr)
                self.assertTrue(lock_path.is_file())
            self.assertTrue(lock_path.is_file())
            acquired_after_release = self._invoke_lock_process(root)
            self.assertEqual(0, acquired_after_release.returncode, acquired_after_release.stderr)
            self.assertTrue(lock_path.is_file())

    def test_lock_contents_have_no_authority_and_normal_release_never_unlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock_path = root / "factory/artifacts/.daily-run.lock"
            with exclusive_run_lock(root):
                mutation_permitted = True
                try:
                    lock_path.write_bytes(b"administrative content mutation")
                except PermissionError:
                    mutation_permitted = False
                blocked = self._invoke_lock_process(root)
                self.assertEqual(3, blocked.returncode, blocked.stderr)
            self.assertTrue(lock_path.is_file())
            if mutation_permitted:
                self.assertEqual(b"administrative content mutation", lock_path.read_bytes())

    @unittest.skipUnless(os.name == "posix", "POSIX permits administrative path replacement")
    def test_old_holder_cleanup_cannot_release_or_delete_replacement_holder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock_path = root / "factory/artifacts/.daily-run.lock"
            first = exclusive_run_lock(root)
            first.__enter__()
            replacement = lock_path.with_suffix(".replacement")
            replacement.write_bytes(b"replacement")
            os.replace(replacement, lock_path)
            second = exclusive_run_lock(root)
            second.__enter__()
            try:
                first.__exit__(None, None, None)
                blocked = self._invoke_lock_process(root)
                self.assertEqual(3, blocked.returncode, blocked.stderr)
                self.assertTrue(lock_path.is_file())
            finally:
                second.__exit__(None, None, None)
            self.assertEqual(0, self._invoke_lock_process(root).returncode)

    def test_posix_and_windows_lock_abstractions_are_nonblocking_and_non_destructive(self) -> None:
        class FakePosix:
            LOCK_EX = 1
            LOCK_NB = 2
            LOCK_UN = 4

            def __init__(self) -> None:
                self.calls: list[tuple[int, int]] = []

            def flock(self, descriptor: int, operation: int) -> None:
                self.calls.append((descriptor, operation))

        class FakeWindows:
            LK_NBLCK = 1
            LK_UNLCK = 2

            def __init__(self) -> None:
                self.calls: list[tuple[int, int, int]] = []

            def locking(self, descriptor: int, operation: int, count: int) -> None:
                self.calls.append((descriptor, operation, count))

        posix = FakePosix()
        _acquire_platform_lock(7, platform="posix", posix_module=posix)
        _release_platform_lock(7, platform="posix", posix_module=posix)
        self.assertEqual([(7, 3), (7, 4)], posix.calls)

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "lock"
            descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
            windows = FakeWindows()
            try:
                _acquire_platform_lock(descriptor, platform="nt", windows_module=windows)
                _release_platform_lock(descriptor, platform="nt", windows_module=windows)
                self.assertEqual(b"\0", path.read_bytes())
            finally:
                os.close(descriptor)
            path.write_bytes(b"existing")
            descriptor = os.open(path, os.O_RDWR)
            try:
                _acquire_platform_lock(descriptor, platform="nt", windows_module=windows)
                _release_platform_lock(descriptor, platform="nt", windows_module=windows)
            finally:
                os.close(descriptor)
            self.assertEqual(b"existing", path.read_bytes())
            self.assertEqual(4, len(windows.calls))

        with self.assertRaises(RunLockError):
            _acquire_platform_lock(7, platform="unsupported")


class ProductionTrustBoundaryTests(unittest.TestCase):
    def test_public_function_rejects_fabricated_probe_overrides(self) -> None:
        with self.assertRaises(TypeError):
            execute_daily_run(
                Path.cwd(),
                owner_id="owner-a",
                run_date=RUN_DATE,
                repository_state=RepositoryState(True),
                integrity_issues=(),
            )

    def test_lower_level_public_helpers_reject_output_namespace_substitution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(TypeError):
                claim_daily_run(
                    root,
                    RUN_DATE,
                    "injected-claim-owner",
                    output_dir="governance",
                )
            with self.assertRaises(TypeError):
                with exclusive_run_lock(root, output_dir="governance"):
                    self.fail("noncanonical lock unexpectedly acquired")
            self.assertFalse((root / "governance").exists())

    def test_public_api_rejects_registry_and_config_substitution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_production_fixture(root)
            registry_path, config_path = create_injected_authority_fixture(root)
            injected = load_registry(registry_path, root=root)
            self.assertEqual("READY", injected.tasks[0].status)
            load_daily_config(config_path)

            for keyword, relative in (
                ("registry_path", registry_path.relative_to(root).as_posix()),
                ("config_path", config_path.relative_to(root).as_posix()),
                ("output_dir", "factory/artifacts/alternate-a"),
                ("output_dir", "factory/artifacts/alternate-b"),
            ):
                with self.subTest(keyword=keyword, relative=relative), self.assertRaises(TypeError):
                    execute_daily_run(
                        root,
                        owner_id="public-substitution",
                        run_date=RUN_DATE,
                        **{keyword: relative},
                    )

            self.assertFalse(
                (root / "factory/artifacts/2026-08-11-execution-plan.json").exists()
            )

    def test_cli_rejects_registry_and_config_substitution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_production_fixture(root)
            registry_path, config_path = create_injected_authority_fixture(root)
            for flag, value in (
                ("--registry", registry_path.relative_to(root).as_posix()),
                ("--config", config_path.relative_to(root).as_posix()),
                ("--output-dir", "factory/artifacts/alternate"),
            ):
                attempted = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "factory.daily_run",
                        "--dry-run",
                        "--root",
                        str(root),
                        "--owner-id",
                        "cli-substitution",
                        flag,
                        value,
                    ],
                    cwd=ROOT,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                with self.subTest(flag=flag):
                    self.assertEqual(2, attempted.returncode, attempted.stderr)
                    self.assertIn(f"unrecognized arguments: {flag}", attempted.stderr)
            self.assertFalse(
                (root / "factory/artifacts/2026-08-11-execution-plan.json").exists()
            )

    def test_public_entry_owns_canonical_lock_and_claim_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_production_fixture(root)
            claim_path = root / "factory/artifacts/run-history/2026-08-11.json"
            with exclusive_run_lock(root):
                blocked = subprocess.run(
                    [sys.executable, "-c", PUBLIC_RUN_ATTEMPT_SCRIPT, str(root), RUN_DATE.isoformat()],
                    cwd=ROOT,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(3, blocked.returncode, blocked.stderr)
                self.assertFalse(claim_path.exists())

            with patch("factory.daily_run.github_actions_enabled", return_value=False):
                first = execute_daily_run(root, owner_id="canonical-owner", run_date=RUN_DATE)
                retry = execute_daily_run(root, owner_id="canonical-owner", run_date=RUN_DATE)
                with self.assertRaisesRegex(RunHistoryError, "already claimed"):
                    execute_daily_run(root, owner_id="different-owner", run_date=RUN_DATE)

            self.assertEqual("NO_WORK", first.status)
            self.assertEqual("NO_WORK", retry.status)
            self.assertEqual("canonical-owner", load_daily_claim(claim_path, RUN_DATE).owner_id)
            self.assertFalse((root / "factory/artifacts/alternate-a").exists())
            self.assertFalse((root / "factory/artifacts/alternate-b").exists())

    def test_production_cli_uses_canonical_lock_claim_and_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_production_fixture(root)
            environment = os.environ.copy()
            environment.pop("GITHUB_ACTIONS", None)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "factory.daily_run",
                    "--dry-run",
                    "--root",
                    str(root),
                    "--date",
                    RUN_DATE.isoformat(),
                    "--owner-id",
                    "canonical-cli-owner",
                ],
                cwd=ROOT,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            claim_path = root / "factory/artifacts/run-history/2026-08-11.json"
            self.assertEqual(
                "canonical-cli-owner", load_daily_claim(claim_path, RUN_DATE).owner_id
            )
            self.assertTrue((root / "factory/artifacts/2026-08-11-owner-report.md").is_file())
            self.assertFalse((root / "governance/run-history").exists())

    def test_dirty_allowlist_cannot_be_empty_arbitrary_multiple_or_self_expanded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_production_fixture(root)
            injected_registry, _ = create_injected_authority_fixture(root)
            (root / "factory/registry.toml").write_bytes(injected_registry.read_bytes())
            config_path = root / "factory/daily_run.toml"
            original = config_path.read_text(encoding="utf-8")
            for policy in (
                "[]",
                '["factory/"]',
                '["factory/artifacts/", "factory/"]',
                '["factory/artifacts/", "factory/artifacts/injected-authority/"]',
            ):
                config_path.write_text(
                    original.replace('["factory/artifacts/"]', policy), encoding="utf-8"
                )
                with self.subTest(policy=policy), self.assertRaisesRegex(
                    ConfigurationError, "must remain exactly"
                ):
                    load_daily_config(config_path)

            config_path.write_text(
                original.replace(
                    '["factory/artifacts/"]', '["factory/artifacts/", "factory/"]'
                ),
                encoding="utf-8",
            )
            with (
                patch("factory.daily_run.github_actions_enabled", return_value=False),
                self.assertRaisesRegex(ConfigurationError, "must remain exactly"),
            ):
                execute_daily_run(
                    root,
                    owner_id="expanded-dirty-policy",
                    run_date=RUN_DATE,
                )
            self.assertFalse(
                (root / "factory/artifacts/2026-08-11-execution-plan.json").exists()
            )

    def test_production_path_calls_canonical_validators_and_blocks_without_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_production_fixture(root)
            registry_before = (root / "factory/registry.toml").read_bytes()
            with (
                patch("factory.daily_run.github_actions_enabled", return_value=False),
                patch("factory.daily_run.probe_repository", wraps=probe_repository) as repo_probe,
                patch("factory.daily_run.verify_integrity", wraps=verify_integrity) as integrity_probe,
            ):
                first = execute_daily_run(
                    root,
                    owner_id="workflow-100:1",
                    run_date=RUN_DATE,
                )
            self.assertEqual("NO_WORK", first.status)
            repo_probe.assert_called_once_with(root.resolve())
            self.assertEqual(1, integrity_probe.call_count)

            (root / "evidence/core.txt").write_text("tampered\n", encoding="utf-8")
            with patch("factory.daily_run.github_actions_enabled", return_value=False):
                blocked = execute_daily_run(
                    root,
                    owner_id="workflow-101:1",
                    run_date=date(2026, 8, 12),
                )
            self.assertEqual("BLOCKED", blocked.status)
            self.assertEqual("", blocked.selected_task_id)
            self.assertFalse(
                (root / "factory/artifacts/2026-08-12-execution-plan.json").exists()
            )
            self.assertEqual(registry_before, (root / "factory/registry.toml").read_bytes())


class RepositoryProbeTests(unittest.TestCase):
    def test_outside_to_artifacts_rename_checks_source_and_blocks_production_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_production_fixture(root)
            injected_registry, _ = create_injected_authority_fixture(root)
            (root / "factory/registry.toml").write_bytes(injected_registry.read_bytes())
            source = "ordinary file [source].txt"
            destination = "factory/artifacts/renamed file [destination].txt"
            (root / source).write_text("tracked outside artifact namespace\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True, timeout=10)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=FACTORY Test",
                    "-c",
                    "user.email=factory@example.invalid",
                    "commit",
                    "-q",
                    "-m",
                    "ready rename fixture",
                ],
                cwd=root,
                check=True,
                timeout=10,
            )
            subprocess.run(
                ["git", "mv", "--", source, destination],
                cwd=root,
                check=True,
                timeout=10,
            )

            state = probe_repository(root)
            self.assertTrue(state.known, state.error)
            self.assertIn(source, state.dirty_paths)
            self.assertIn(destination, state.dirty_paths)
            self.assertEqual((source,), disallowed_dirty_paths(state, ("factory/artifacts/",)))

            with patch("factory.daily_run.github_actions_enabled", return_value=False):
                outcome = execute_daily_run(root, owner_id="rename-probe", run_date=RUN_DATE)
            self.assertEqual("BLOCKED", outcome.status)
            self.assertEqual("", outcome.selected_task_id)
            self.assertEqual("", outcome.plan_path)
            report = (root / outcome.report_path).read_text(encoding="utf-8")
            self.assertIn(source, report)


class DurableRunHistoryTests(unittest.TestCase):
    def test_same_date_owner_is_idempotent_other_owner_blocks_and_next_date_proceeds(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = claim_daily_run(root, RUN_DATE, "owner-a")
            claim_path = root / "factory/artifacts/run-history/2026-08-11.json"
            original = claim_path.read_bytes()
            retry = claim_daily_run(root, RUN_DATE, "owner-a")
            self.assertEqual(first, retry)
            self.assertEqual(original, claim_path.read_bytes())
            with self.assertRaisesRegex(RunHistoryError, "already claimed"):
                claim_daily_run(root, RUN_DATE, "owner-b")
            self.assertEqual(original, claim_path.read_bytes())
            next_day = claim_daily_run(root, date(2026, 8, 12), "owner-b")
        self.assertEqual("2026-08-12", next_day.date)

    def test_malformed_history_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            claim_path = root / "factory/artifacts/run-history/2026-08-11.json"
            claim_path.parent.mkdir(parents=True)
            claim_path.write_text('{"date":"2026-08-11"}\n', encoding="utf-8")
            with self.assertRaisesRegex(RunHistoryError, "malformed daily claim"):
                load_daily_claim(claim_path, RUN_DATE)
            with self.assertRaises(RunHistoryError):
                claim_daily_run(root, RUN_DATE, "owner-a")
            self.assertEqual('{"date":"2026-08-11"}\n', claim_path.read_text(encoding="utf-8"))

    def test_separate_process_invocations_share_durable_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def invoke(owner_id: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "factory.run_history",
                        "--root",
                        str(root),
                        "--date",
                        RUN_DATE.isoformat(),
                        "--owner-id",
                        owner_id,
                    ],
                    cwd=ROOT,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

            first = invoke("process-a")
            blocked = invoke("process-b")
            retry = invoke("process-a")
        self.assertEqual(0, first.returncode, first.stderr)
        self.assertEqual(1, blocked.returncode, blocked.stderr)
        self.assertEqual(0, retry.returncode, retry.stderr)

    def test_claim_cli_rejects_output_namespace_override_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rejected = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "factory.run_history",
                    "--root",
                    str(root),
                    "--date",
                    RUN_DATE.isoformat(),
                    "--owner-id",
                    "cli-output-injection",
                    "--output-dir",
                    "governance",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(2, rejected.returncode, rejected.stderr)
            self.assertIn("unrecognized arguments: --output-dir", rejected.stderr)
            self.assertFalse((root / "governance/run-history").exists())
            self.assertFalse((root / "factory/artifacts/run-history").exists())


if __name__ == "__main__":
    unittest.main()
