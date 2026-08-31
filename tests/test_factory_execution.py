from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from factory.daily_run import exclusive_run_lock
from factory.execution import (
    AgentRouter,
    CodingRequest,
    ContextRequest,
    DeterministicFakeCodingAgentAdapter,
    DeterministicFakeReviewAdapter,
    ReviewFinding,
    ReviewOutcome,
    execute_work_unit,
)
from factory.integrity import canonical_sha256
from factory.work_units import ContextCompiler, WorkUnitError, load_work_unit, parse_work_unit


ROOT = Path(__file__).resolve().parents[1]
PASSING_REVIEWS = {
    "security_reviewer": (ReviewOutcome("security_reviewer", "PASS"),),
    "code_reviewer": (ReviewOutcome("code_reviewer", "PASS"),),
}


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8", newline="\n")


def _array(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(json.dumps(value) for value in values) + "]"


def create_fixture(
    root: Path,
    *,
    authority: str = "PRODUCT_CHANGE_LEVEL_A",
    epic_status: str = "OWNER_APPROVED",
    task_status: str = "READY",
    dependency_status: str = "DONE",
    allowed_paths: tuple[str, ...] = ("src/",),
    forbidden_paths: tuple[str, ...] = ("governance/",),
    required_reviews: tuple[str, ...] = ("security_reviewer", "code_reviewer"),
    optional_reviews: tuple[str, ...] = (),
    review_budget: int = 2,
    max_correction_loops: int = 2,
    context_budget: int = 10000,
) -> Path:
    _write(root / ".gitignore", "factory/artifacts/\n__pycache__/\n")
    _write(root / "context.txt", "mandatory context\n")
    _write(root / "frozen.txt", "frozen identity\n")
    _write(root / "skip/never-read.txt", "skip secret-like content\n")
    for index in range(1, 6):
        _write(root / f"extra{index}.txt", f"expansion {index}\n")
    _write(root / "governance/approval-policy.toml", 'policy_id = "test"\n')
    _write(root / "governance/risk-policy.toml", 'policy_id = "test-risk"\n')
    _write(root / "specs/factory-001b/acceptance.toml", 'work_item = "FACTORY-001B"\n')
    core_manifest = root / "docs/FROZEN_CORE_V12.sha256"
    pm_manifest = root / "docs/FROZEN_PM_DEC_007_HYBRID_V2.sha256"
    _write(core_manifest, f"{canonical_sha256(root / 'frozen.txt')}  frozen.txt\n")
    _write(pm_manifest, f"{canonical_sha256(root / 'context.txt')}  context.txt\n")
    approval_hash = canonical_sha256(root / "governance/approval-policy.toml")
    risk_hash = canonical_sha256(root / "governance/risk-policy.toml")
    _write(
        root / "factory/daily_run.toml",
        f"""
        schema_version = 1
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
        active_core_manifest = "docs/FROZEN_CORE_V12.sha256"
        active_core_manifest_sha256 = "{canonical_sha256(core_manifest)}"
        pm_dec_007_manifest = "docs/FROZEN_PM_DEC_007_HYBRID_V2.sha256"
        pm_dec_007_manifest_sha256 = "{canonical_sha256(pm_manifest)}"

        [[integrity.governance]]
        path = "governance/approval-policy.toml"
        sha256 = "{approval_hash}"

        [[integrity.governance]]
        path = "governance/risk-policy.toml"
        sha256 = "{risk_hash}"

        [routing]
        high = ["architecture"]
        medium = ["bounded_implementation"]
        low = ["summary"]
        """,
    )
    _write(
        root / "factory/registry.toml",
        f"""
        schema_version = 1

        [[epics]]
        id = "FACTORY-001"
        title = "Factory"
        goal = "Controlled work"
        status = "{epic_status}"
        approved_capabilities = ["controlled_execution"]

        [[tasks]]
        id = "FACTORY-001A"
        epic_id = "FACTORY-001"
        title = "Baseline"
        status = "{dependency_status}"
        priority = 1
        estimated_minutes = 10
        capabilities = []
        owner_gate_reasons = []
        is_new_product_idea = false
        mandatory_context = []
        relevant_context = []
        frozen_context = []
        skip_context = []

        [[tasks]]
        id = "FACTORY-001B"
        epic_id = "FACTORY-001"
        title = "Controlled execution"
        status = "{task_status}"
        priority = 2
        estimated_minutes = 20
        spec_path = "specs/factory-001b/work-unit.toml"
        acceptance_path = "specs/factory-001b/acceptance.toml"
        capabilities = ["controlled_execution"]
        owner_gate_reasons = []
        is_new_product_idea = false
        mandatory_context = ["context.txt"]
        relevant_context = []
        frozen_context = ["frozen.txt"]
        skip_context = ["skip/"]

        [[dependencies]]
        task_id = "FACTORY-001B"
        depends_on = "FACTORY-001A"
        """,
    )
    work_unit = root / "specs/factory-001b/work-unit.toml"
    _write(
        work_unit,
        f"""
        schema_version = 1
        id = "FACTORY-001B-WU-TEST"
        task_id = "FACTORY-001B"
        epic_id = "FACTORY-001"
        goal = "Change one allowed file"
        status = "READY"
        authority_level = "{authority}"
        work_size = "NORMAL"
        allowed_paths = {_array(allowed_paths)}
        forbidden_paths = {_array(forbidden_paths)}
        mandatory_context = ["context.txt"]
        relevant_context = []
        frozen_context = ["frozen.txt"]
        skip_context = ["skip/"]
        acceptance_criteria = ["FACTORY-001B-AC-TEST"]
        required_reviews = {_array(required_reviews)}
        optional_reviews = {_array(optional_reviews)}
        reasoning_budget = "HIGH"
        context_budget = {context_budget}
        review_budget = {review_budget}
        max_correction_loops = {max_correction_loops}
        dependencies = ["FACTORY-001A"]
        evidence_requirements = ["execution_result", "owner_report"]

        [[required_tests]]
        id = "compile_candidate"
        argv = ["python", "-m", "compileall", "-q", "src"]
        timeout_seconds = 30
        """,
    )
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, timeout=10)
    subprocess.run(["git", "config", "user.name", "Factory Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "factory@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True, timeout=10)
    subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=root, check=True, timeout=10)
    return work_unit


class WorkUnitContractTests(unittest.TestCase):
    def test_contract_requires_acceptance_allowed_paths_and_safe_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = create_fixture(root)
            import tomllib

            with path.open("rb") as handle:
                raw = tomllib.load(handle)
            for field in ("acceptance_criteria", "allowed_paths"):
                candidate = dict(raw)
                candidate[field] = []
                with self.subTest(field=field), self.assertRaises(WorkUnitError):
                    parse_work_unit(candidate)
            candidate = dict(raw)
            candidate["required_tests"] = [
                {"id": "unsafe", "argv": ["powershell", "Remove-Item", "x"], "timeout_seconds": 10}
            ]
            with self.assertRaisesRegex(WorkUnitError, "unapproved executable"):
                parse_work_unit(candidate)
            candidate = dict(raw)
            candidate["evidence_requirements"] = ["fabricated_evidence"]
            with self.assertRaisesRegex(WorkUnitError, "unknown evidence"):
                parse_work_unit(candidate)
            candidate = dict(raw)
            candidate["mandatory_context"] = ["_env"]
            with self.assertRaisesRegex(WorkUnitError, "sensitive path"):
                parse_work_unit(candidate)
            candidate = dict(raw)
            candidate["skip_context"] = ["context.txt/"]
            with self.assertRaisesRegex(WorkUnitError, "disjoint scopes"):
                parse_work_unit(candidate)

    def test_level_a_contract_rejects_sensitive_allowed_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = create_fixture(root)
            import tomllib

            with path.open("rb") as handle:
                raw = tomllib.load(handle)
            raw["allowed_paths"] = ["governance/approval-policy.toml"]
            raw["forbidden_paths"] = []
            with self.assertRaisesRegex(WorkUnitError, "denied scope"):
                parse_work_unit(raw)


class ContextAndRoutingTests(unittest.TestCase):
    def test_context_excludes_skip_summarizes_frozen_and_enforces_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = create_fixture(root)
            work_unit = load_work_unit(path, root=root)
            package = ContextCompiler(root, work_unit).compile()
            by_class = {item.classification: item for item in package.entries}
            self.assertEqual("mandatory context\n", by_class["MANDATORY"].content)
            self.assertIsNone(by_class["FROZEN"].content)
            self.assertIsNone(by_class["SKIP"].content)
            (root / "extra.txt").write_text("x" * 20000, encoding="utf-8")
            with self.assertRaisesRegex(WorkUnitError, "budget exceeded"):
                ContextCompiler(root, work_unit).expand(package, "extra.txt", "concrete import")

    def test_context_loader_rejects_symlink_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = create_fixture(root)
            alias = root / "alias.txt"
            try:
                os.symlink(root / "context.txt", alias)
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")
            content = path.read_text(encoding="utf-8").replace(
                'mandatory_context = ["context.txt"]',
                'mandatory_context = ["alias.txt"]',
            )
            path.write_text(content, encoding="utf-8", newline="\n")
            with self.assertRaisesRegex(WorkUnitError, "symbolic link"):
                load_work_unit(path, root=root)

    def test_router_is_minimal_and_never_falls_back_for_optional_role(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = create_fixture(
                root,
                required_reviews=("code_reviewer",),
                optional_reviews=("security_reviewer",),
                review_budget=2,
            )
            work_unit = load_work_unit(path, root=root)
            plan = AgentRouter.select(work_unit, frozenset({"code_reviewer", "risk_reviewer"}))
            self.assertEqual(("code_reviewer",), plan.selected_roles)
            self.assertEqual(("security_reviewer",), plan.unavailable_optional)
            self.assertNotIn("risk_reviewer", plan.selected_roles)


class ExecutionEligibilityTests(unittest.TestCase):
    def test_level_a_executes_passes_and_writes_evidence_without_git_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = create_fixture(root)
            starting_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            writer = DeterministicFakeCodingAgentAdapter(((("src/allowed.py", "VALUE = 1\n"),),))
            reviewer = DeterministicFakeReviewAdapter(PASSING_REVIEWS)
            result = execute_work_unit(
                root,
                path.relative_to(root).as_posix(),
                run_id="eligible-level-a",
                coding_adapter=writer,
                review_adapter=reviewer,
            )
            self.assertEqual("PASS", result.status)
            self.assertEqual(("src/allowed.py",), result.files_created)
            self.assertTrue(all(item.passed for item in result.test_results))
            self.assertEqual(("security_reviewer", "code_reviewer"), result.reviews_run)
            self.assertEqual(
                ("READY", "PREFLIGHT", "ACTIVE", "TESTING", "REVIEW", "PASS"),
                tuple(item.phase for item in result.phase_history),
            )
            self.assertGreaterEqual(result.elapsed_ms, 0)
            self.assertEqual(starting_head, subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip())
            evidence = root / "factory/artifacts/executions/eligible-level-a"
            for name in (
                "work-unit.json",
                "preflight.json",
                "context-manifest.json",
                "diff-summary.json",
                "test-results.json",
                "review-results.json",
                "execution-result.json",
                "owner-report.md",
            ):
                self.assertTrue((evidence / name).is_file(), name)
            report = (evidence / "owner-report.md").read_text(encoding="utf-8")
            for heading in (
                "WHAT WAS ATTEMPTED",
                "WHAT CHANGED",
                "TESTS",
                "REVIEWS",
                "STATUS",
                "BLOCKERS",
                "OWNER DECISIONS REQUIRED",
                "NEXT ELIGIBLE WORK",
            ):
                self.assertIn(heading, report)
            authority = dict(result.authority)
            self.assertFalse(authority["commit"])
            self.assertFalse(authority["push"])
            self.assertFalse(authority["pull_request"])
            self.assertFalse(authority["paper"])
            self.assertFalse(authority["live"])
            self.assertFalse(authority["capital"])
            self.assertFalse(authority["trading_exchange_execution"])

    def test_level_b_and_c_need_owner_before_writer(self) -> None:
        for authority in ("PRODUCT_CHANGE_LEVEL_B", "PRODUCT_CHANGE_LEVEL_C"):
            with self.subTest(authority=authority), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                path = create_fixture(root, authority=authority)
                writer = DeterministicFakeCodingAgentAdapter(((("src/allowed.py", "x = 1\n"),),))
                result = execute_work_unit(
                    root,
                    path.relative_to(root).as_posix(),
                    run_id=f"authority-{authority[-1].lower()}",
                    coding_adapter=writer,
                    review_adapter=DeterministicFakeReviewAdapter(PASSING_REVIEWS),
                )
                self.assertEqual("NEEDS_OWNER", result.status)
                self.assertEqual(0, writer.calls)
                self.assertIn(authority, result.owner_decisions_required[0])

    def test_unapproved_epic_nonready_task_and_dependency_fail_closed(self) -> None:
        cases = (
            {"epic_status": "PROPOSED", "message": "Epic"},
            {"task_status": "PROPOSED", "message": "Task"},
            {"dependency_status": "REVIEW", "message": "dependency"},
        )
        for index, case in enumerate(cases):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                kwargs = {key: value for key, value in case.items() if key != "message"}
                path = create_fixture(root, **kwargs)
                writer = DeterministicFakeCodingAgentAdapter(())
                result = execute_work_unit(
                    root,
                    path.relative_to(root).as_posix(),
                    run_id=f"ineligible-{index}",
                    coding_adapter=writer,
                )
                self.assertEqual("BLOCKED", result.status)
                self.assertEqual(0, writer.calls)
                self.assertTrue(any(case["message"] in item for item in result.blockers))

    def test_scope_violation_is_preserved_and_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = create_fixture(root)
            writer = DeterministicFakeCodingAgentAdapter(((("outside.py", "x = 1\n"),),))
            result = execute_work_unit(
                root,
                path.relative_to(root).as_posix(),
                run_id="scope-violation",
                coding_adapter=writer,
                review_adapter=DeterministicFakeReviewAdapter(PASSING_REVIEWS),
            )
            self.assertEqual("BLOCKED", result.status)
            self.assertFalse((root / "outside.py").exists())
            self.assertTrue(any("scope violation: outside.py" in item for item in result.blockers))

    def test_public_entry_has_no_probe_override_and_default_is_not_configured(self) -> None:
        signature = inspect.signature(execute_work_unit)
        self.assertNotIn("repository_state", signature.parameters)
        self.assertNotIn("integrity_issues", signature.parameters)
        self.assertNotIn("root", CodingRequest.__dataclass_fields__)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = create_fixture(root)
            result = execute_work_unit(root, path.relative_to(root).as_posix(), run_id="not-configured")
            self.assertEqual("NOT_CONFIGURED", result.status)
            self.assertEqual((), result.files_created)

    def test_second_writer_cannot_acquire_factory_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = textwrap.dedent(
                """
                import sys
                from pathlib import Path
                from factory.daily_run import exclusive_run_lock
                try:
                    with exclusive_run_lock(Path(sys.argv[1])):
                        raise SystemExit(0)
                except FileExistsError:
                    raise SystemExit(3)
                """
            )
            with exclusive_run_lock(root):
                completed = subprocess.run(
                    [sys.executable, "-c", script, str(root)],
                    cwd=ROOT,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            self.assertEqual(3, completed.returncode, completed.stderr)

    def test_context_expansion_limit_is_cumulative_across_adapter_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = create_fixture(root)
            writer = DeterministicFakeCodingAgentAdapter(
                ((), ()),
                context_requests=(
                    tuple(ContextRequest(f"extra{index}.txt", f"dependency {index}") for index in range(1, 5)),
                    (ContextRequest("extra5.txt", "dependency 5"),),
                ),
            )
            result = execute_work_unit(
                root,
                path.relative_to(root).as_posix(),
                run_id="context-expansion-limit",
                coding_adapter=writer,
                review_adapter=DeterministicFakeReviewAdapter(PASSING_REVIEWS),
            )
            self.assertEqual("BLOCKED", result.status)
            self.assertEqual(2, writer.calls)
            self.assertEqual(4, len(result.context_expansions))
            self.assertTrue(any("expansion request limit" in item for item in result.blockers))

    def test_mismatched_review_role_cannot_fabricate_required_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = create_fixture(root, required_reviews=("code_reviewer",), review_budget=1)
            writer = DeterministicFakeCodingAgentAdapter(((("src/allowed.py", "VALUE = 1\n"),),))
            reviewer = DeterministicFakeReviewAdapter(
                {"code_reviewer": (ReviewOutcome("security_reviewer", "PASS"),)}
            )
            result = execute_work_unit(
                root,
                path.relative_to(root).as_posix(),
                run_id="mismatched-review",
                coding_adapter=writer,
                review_adapter=reviewer,
            )
            self.assertEqual("BLOCKED", result.status)
            self.assertTrue(any("invalid review outcome" in item for item in result.blockers))


class CorrectionGateTests(unittest.TestCase):
    def test_test_failure_uses_exactly_two_corrections_then_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = create_fixture(root, required_reviews=(), review_budget=0)
            bad = (("src/bad.py", "def broken(:\n"),)
            writer = DeterministicFakeCodingAgentAdapter((bad, bad, bad))
            result = execute_work_unit(
                root,
                path.relative_to(root).as_posix(),
                run_id="test-corrections",
                coding_adapter=writer,
            )
            self.assertEqual("FAIL", result.status)
            self.assertEqual(2, result.correction_loops_used)
            self.assertEqual(3, writer.calls)
            self.assertTrue(any("required test failed" in item for item in result.blockers))

    def test_blocking_review_uses_two_corrections_and_only_affected_reviewer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = create_fixture(root)
            writer = DeterministicFakeCodingAgentAdapter(
                (
                    (("src/allowed.py", "VALUE = 1\n"),),
                    (("src/allowed.py", "VALUE = 2\n"),),
                    (("src/allowed.py", "VALUE = 3\n"),),
                )
            )
            blocking = ReviewFinding("HIGH", "src/allowed.py:1", "still blocking")
            reviewer = DeterministicFakeReviewAdapter(
                {
                    "security_reviewer": (ReviewOutcome("security_reviewer", "PASS"),),
                    "code_reviewer": (
                        ReviewOutcome("code_reviewer", "BLOCKED", (blocking,)),
                        ReviewOutcome("code_reviewer", "BLOCKED", (blocking,)),
                        ReviewOutcome("code_reviewer", "BLOCKED", (blocking,)),
                    ),
                }
            )
            result = execute_work_unit(
                root,
                path.relative_to(root).as_posix(),
                run_id="review-corrections",
                coding_adapter=writer,
                review_adapter=reviewer,
            )
            self.assertEqual("BLOCKED", result.status)
            self.assertEqual(2, result.correction_loops_used)
            self.assertEqual(1, reviewer.calls.count("security_reviewer"))
            self.assertEqual(3, reviewer.calls.count("code_reviewer"))


if __name__ == "__main__":
    unittest.main()
