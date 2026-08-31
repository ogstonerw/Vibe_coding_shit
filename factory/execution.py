"""Controlled, evidence-first FACTORY-001B Work Unit orchestration."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Protocol

from .configuration import load_daily_config
from .daily_run import DEFAULT_CONFIG, DEFAULT_OUTPUT, DEFAULT_REGISTRY, exclusive_run_lock
from .integrity import canonical_sha256, safe_repo_path, verify_integrity
from .models import ACTIVE_RUN_STATUSES, DailyConfig, Registry, RepositoryState
from .planning import atomic_write_text
from .registry import RegistryError, load_registry
from .repository import disallowed_dirty_paths, probe_repository
from .work_units import (
    ContextCompiler,
    ContextPackage,
    TestCommand,
    WorkUnit,
    WorkUnitError,
    load_work_unit,
    normalize_repo_scope,
    path_allowed,
)


RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
MAX_CONTEXT_EXPANSIONS = 4
MAX_REVIEW_INVOCATIONS = 5
MAX_CAPTURE_BYTES = 1_000_000


@dataclass(frozen=True)
class ContextRequest:
    path: str
    reason: str


@dataclass(frozen=True)
class FileChange:
    path: str
    content: str | None


@dataclass(frozen=True)
class CodingRequest:
    work_unit: WorkUnit
    context: ContextPackage
    starting_head: str
    starting_status: tuple[str, ...]
    correction_loop: int
    correction_findings: tuple[str, ...]


@dataclass(frozen=True)
class CodingOutcome:
    status: str
    summary: str
    context_requests: tuple[ContextRequest, ...] = ()
    changes: tuple[FileChange, ...] = ()


class CodingAgentAdapter(Protocol):
    configured: bool
    name: str

    def execute(self, request: CodingRequest) -> CodingOutcome: ...


class NotConfiguredCodingAgentAdapter:
    configured = False
    name = "NOT_CONFIGURED"

    def execute(self, request: CodingRequest) -> CodingOutcome:
        del request
        return CodingOutcome("NOT_CONFIGURED", "No production coding-agent transport is configured.")


class DeterministicFakeCodingAgentAdapter:
    """Test-only deterministic writer; actions are applied in declared call order."""

    configured = True
    name = "DETERMINISTIC_FAKE"

    def __init__(
        self,
        actions_by_call: tuple[tuple[tuple[str, str | None], ...], ...],
        *,
        outcomes: tuple[str, ...] = (),
        context_requests: tuple[tuple[ContextRequest, ...], ...] = (),
    ) -> None:
        self.actions_by_call = actions_by_call
        self.outcomes = outcomes
        self.context_requests = context_requests
        self.calls = 0

    def execute(self, request: CodingRequest) -> CodingOutcome:
        index = self.calls
        self.calls += 1
        actions = self.actions_by_call[index] if index < len(self.actions_by_call) else ()
        status = self.outcomes[index] if index < len(self.outcomes) else "COMPLETED"
        requests = self.context_requests[index] if index < len(self.context_requests) else ()
        changes = tuple(FileChange(path, content) for path, content in actions)
        return CodingOutcome(status, f"deterministic fake call {index + 1}", requests, changes)


@dataclass(frozen=True)
class ReviewFinding:
    severity: str
    location: str
    message: str
    blocking: bool = True


@dataclass(frozen=True)
class ReviewRequest:
    work_unit: WorkUnit
    role: str
    changed_paths: tuple[str, ...]
    correction_loop: int


@dataclass(frozen=True)
class ReviewOutcome:
    role: str
    status: str
    findings: tuple[ReviewFinding, ...] = ()
    correction_loop: int = 0


class ReviewAdapter(Protocol):
    name: str

    def available_roles(self) -> frozenset[str]: ...

    def review(self, request: ReviewRequest) -> ReviewOutcome: ...


class NotConfiguredReviewAdapter:
    name = "NOT_CONFIGURED"

    def available_roles(self) -> frozenset[str]:
        return frozenset()

    def review(self, request: ReviewRequest) -> ReviewOutcome:
        return ReviewOutcome(request.role, "UNAVAILABLE")


class DeterministicFakeReviewAdapter:
    """Test-only reviewer returning configured role outcomes in order."""

    name = "DETERMINISTIC_FAKE"

    def __init__(self, outcomes: dict[str, tuple[ReviewOutcome, ...]]):
        self.outcomes = outcomes
        self.calls: list[str] = []

    def available_roles(self) -> frozenset[str]:
        return frozenset(self.outcomes)

    def review(self, request: ReviewRequest) -> ReviewOutcome:
        role_calls = self.calls.count(request.role)
        self.calls.append(request.role)
        choices = self.outcomes[request.role]
        return choices[min(role_calls, len(choices) - 1)]


@dataclass(frozen=True)
class RoutingPlan:
    selected_roles: tuple[str, ...]
    unavailable_required: tuple[str, ...]
    unavailable_optional: tuple[str, ...]


class AgentRouter:
    """Select only declared reviewers; never invent or fallback to another role."""

    @staticmethod
    def select(work_unit: WorkUnit, available_roles: frozenset[str]) -> RoutingPlan:
        required_available = tuple(
            role for role in work_unit.required_reviews if role in available_roles
        )
        unavailable_required = tuple(
            role for role in work_unit.required_reviews if role not in available_roles
        )
        remaining = work_unit.review_budget - len(required_available)
        optional_available = tuple(
            role
            for role in work_unit.optional_reviews
            if role in available_roles
        )[: max(0, remaining)]
        unavailable_optional = tuple(
            role for role in work_unit.optional_reviews if role not in available_roles
        )
        return RoutingPlan(
            selected_roles=required_available + optional_available,
            unavailable_required=unavailable_required,
            unavailable_optional=unavailable_optional,
        )


@dataclass(frozen=True)
class TestOutcome:
    id: str
    argv: tuple[str, ...]
    exit_code: int
    passed: bool
    elapsed_ms: int
    stdout_sha256: str
    stderr_sha256: str
    stdout_bytes: int
    stderr_bytes: int
    detail: str = ""
    correction_loop: int = 0


@dataclass(frozen=True)
class DiffSummary:
    changed_path_count: int
    added_lines: int
    deleted_lines: int
    unexpected_files: tuple[str, ...]


@dataclass(frozen=True)
class PhaseEvent:
    phase: str
    at: str


@dataclass(frozen=True)
class ExecutionResult:
    run_id: str
    work_unit_id: str
    task_id: str
    epic_id: str
    started_at: str
    finished_at: str
    elapsed_ms: int
    status: str
    phase_history: tuple[PhaseEvent, ...]
    agent_role: str
    starting_head: str
    starting_status: tuple[str, ...]
    files_changed: tuple[str, ...]
    files_created: tuple[str, ...]
    files_deleted: tuple[str, ...]
    tests_run: tuple[str, ...]
    test_results: tuple[TestOutcome, ...]
    reviews_run: tuple[str, ...]
    review_results: tuple[ReviewOutcome, ...]
    context_used: tuple[str, ...]
    context_expansions: tuple[tuple[str, str], ...]
    correction_loops_used: int
    diff_summary: DiffSummary
    evidence_refs: tuple[tuple[str, str], ...]
    blockers: tuple[str, ...]
    owner_decisions_required: tuple[str, ...]
    next_eligible_work: str
    authority: tuple[tuple[str, bool | str], ...]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _jsonable(value: object) -> object:
    if hasattr(value, "__dataclass_fields__"):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


def _json_text(value: object) -> str:
    return json.dumps(_jsonable(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _git(root: Path, argv: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[bytes]:
    try:
        completed = subprocess.run(
            ["git", *argv],
            cwd=root,
            check=False,
            capture_output=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise WorkUnitError(f"Git probe failed: {exc}") from exc
    if completed.returncode != 0:
        detail = os.fsdecode(completed.stderr).strip() or f"exit {completed.returncode}"
        raise WorkUnitError(f"Git {' '.join(argv)} failed: {detail}")
    return completed


def _starting_head(root: Path) -> str:
    value = os.fsdecode(_git(root, ["rev-parse", "HEAD"]).stdout).strip()
    if not re.fullmatch(r"[0-9a-f]{40,64}", value):
        raise WorkUnitError("starting HEAD is not a canonical Git object ID")
    return value


def _changed_path_sets(root: Path) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    completed = _git(root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    records = completed.stdout.split(b"\0")
    if not records or records[-1] != b"":
        raise WorkUnitError("malformed NUL-delimited Git status")
    records.pop()
    changed: set[str] = set()
    created: set[str] = set()
    deleted: set[str] = set()
    index = 0
    while index < len(records):
        entry = records[index]
        if len(entry) < 4 or entry[2:3] != b" " or not entry[3:]:
            raise WorkUnitError(f"malformed Git status record: {entry!r}")
        status = entry[:2]
        path = os.fsdecode(entry[3:]).replace("\\", "/")
        index += 1
        related = [path]
        if b"R" in status or b"C" in status:
            if index >= len(records) or not records[index]:
                raise WorkUnitError("Git rename/copy record is incomplete")
            related.append(os.fsdecode(records[index]).replace("\\", "/"))
            index += 1
        changed.update(related)
        if status == b"??" or b"A" in status:
            created.add(path)
        elif b"D" in status:
            deleted.update(related)
    modified = changed - created - deleted
    return tuple(sorted(modified)), tuple(sorted(created)), tuple(sorted(deleted))


def _apply_changes(root: Path, work_unit: WorkUnit, changes: tuple[FileChange, ...]) -> None:
    normalized: list[tuple[str, str | None]] = []
    for index, change in enumerate(changes):
        relative = normalize_repo_scope(change.path, f"changes[{index}].path")
        if relative.endswith("/"):
            raise WorkUnitError(f"file change cannot target a directory scope: {relative}")
        if not path_allowed(work_unit, relative):
            raise WorkUnitError(f"scope violation: {relative}")
        if change.content is not None and not isinstance(change.content, str):
            raise WorkUnitError(f"file change content must be UTF-8 text or null: {relative}")
        lexical = root.resolve()
        for part in PurePosixPath(relative).parts:
            lexical = lexical / part
            if lexical.is_symlink():
                raise WorkUnitError(f"file change must not traverse a symbolic link: {relative}")
        normalized.append((relative, change.content))
    paths = [path for path, _ in normalized]
    if len(paths) != len(set(paths)):
        raise WorkUnitError("coding adapter returned duplicate file changes")
    for relative, content in normalized:
        target = safe_repo_path(root, relative)
        if content is None:
            if target.is_file():
                target.unlink()
            elif target.exists():
                raise WorkUnitError(f"deletion target is not a regular file: {relative}")
            continue
        if target.exists() and not target.is_file():
            raise WorkUnitError(f"write target is not a regular file: {relative}")
        atomic_write_text(target, content)


def _diff_summary(root: Path, all_paths: tuple[str, ...], work_unit: WorkUnit) -> DiffSummary:
    added = 0
    deleted = 0
    completed = _git(root, ["diff", "--numstat", "HEAD", "--"])
    for line in os.fsdecode(completed.stdout).splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        if parts[0].isdigit():
            added += int(parts[0])
        if parts[1].isdigit():
            deleted += int(parts[1])
    tracked = set(os.fsdecode(_git(root, ["ls-files", "-z"]).stdout).split("\0"))
    for relative in all_paths:
        if relative in tracked or not (root / relative).is_file():
            continue
        try:
            added += len((root / relative).read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeDecodeError):
            pass
    unexpected = tuple(path for path in all_paths if not path_allowed(work_unit, path))
    return DiffSummary(len(all_paths), added, deleted, unexpected)


def _sanitized_environment() -> dict[str, str]:
    allowed = ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "COMSPEC")
    environment = {key: os.environ[key] for key in allowed if key in os.environ}
    environment.update({"PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    return environment


def _command_argv(command: TestCommand) -> list[str]:
    executable = Path(command.argv[0]).name.lower()
    if executable in {"python", "python.exe", "python3", "python3.exe", "py", "py.exe"}:
        return [sys.executable, *command.argv[1:]]
    return list(command.argv)


def _run_command(root: Path, command: TestCommand, correction_loop: int) -> TestOutcome:
    started = datetime.now(timezone.utc)
    try:
        completed = subprocess.run(
            _command_argv(command),
            cwd=root,
            env=_sanitized_environment(),
            shell=False,
            check=False,
            capture_output=True,
            timeout=command.timeout_seconds,
        )
        stdout = completed.stdout[:MAX_CAPTURE_BYTES]
        stderr = completed.stderr[:MAX_CAPTURE_BYTES]
        code = completed.returncode
        detail = "" if len(completed.stdout) <= MAX_CAPTURE_BYTES and len(completed.stderr) <= MAX_CAPTURE_BYTES else "output truncated before hashing"
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"")[:MAX_CAPTURE_BYTES]
        stderr = (exc.stderr or b"")[:MAX_CAPTURE_BYTES]
        code = -1
        detail = f"timeout after {command.timeout_seconds}s"
    except OSError as exc:
        stdout = b""
        stderr = str(exc).encode("utf-8", errors="replace")
        code = -1
        detail = "executable unavailable"
    elapsed = datetime.now(timezone.utc) - started
    return TestOutcome(
        id=command.id,
        argv=command.argv,
        exit_code=code,
        passed=code == 0,
        elapsed_ms=max(0, int(elapsed.total_seconds() * 1000)),
        stdout_sha256=hashlib.sha256(stdout).hexdigest(),
        stderr_sha256=hashlib.sha256(stderr).hexdigest(),
        stdout_bytes=len(stdout),
        stderr_bytes=len(stderr),
        detail=detail,
        correction_loop=correction_loop,
    )


def _baseline_commands(paths: tuple[str, ...]) -> tuple[TestCommand, ...]:
    python_paths = tuple(path for path in paths if path.endswith(".py") and Path(path).is_absolute() is False)
    commands: list[TestCommand] = []
    if python_paths:
        commands.append(TestCommand("compileall_changed_python", ("python", "-m", "compileall", "-q", *python_paths), 180))
    return tuple(commands)


def _eligibility(
    root: Path,
    registry: Registry,
    config: DailyConfig,
    work_unit: WorkUnit,
    repository_state: RepositoryState,
    integrity_issues: tuple[str, ...],
) -> tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    checks: list[str] = []
    blockers: list[str] = []
    decisions: list[str] = []
    if work_unit.status != "READY":
        blockers.append(f"Work Unit {work_unit.id} is {work_unit.status}, expected READY")
    try:
        task = registry.task(work_unit.task_id)
    except StopIteration:
        blockers.append(f"missing Task {work_unit.task_id}")
        task = None
    try:
        epic = registry.epic(work_unit.epic_id)
    except StopIteration:
        blockers.append(f"missing Epic {work_unit.epic_id}")
        epic = None
    if task is not None:
        if task.status != "READY":
            blockers.append(f"Task {task.id} is {task.status}, expected READY")
        if task.epic_id != work_unit.epic_id:
            blockers.append(f"Work Unit {work_unit.id} does not belong to Task {task.id} Epic")
    if epic is not None and epic.status != "OWNER_APPROVED":
        blockers.append(f"Epic {epic.id} is {epic.status}, expected OWNER_APPROVED")
    if work_unit.authority_level != "PRODUCT_CHANGE_LEVEL_A":
        decisions.append(f"{work_unit.authority_level} requires Owner authorization")
    expected_dependencies = (
        tuple(item.depends_on for item in registry.dependencies_for(work_unit.task_id))
        if task is not None
        else ()
    )
    if set(expected_dependencies) != set(work_unit.dependencies):
        blockers.append("Work Unit dependencies do not match canonical Task dependencies")
    for dependency in expected_dependencies:
        try:
            parent = registry.task(dependency)
        except StopIteration:
            blockers.append(f"missing dependency Task {dependency}")
            continue
        if parent.status != "DONE":
            blockers.append(f"dependency {parent.id}={parent.status}, expected DONE")
    active = tuple(run.id for run in registry.runs if run.status in ACTIVE_RUN_STATUSES)
    if active:
        blockers.append(f"conflicting active factory run: {', '.join(active)}")
    if work_unit.max_correction_loops > config.max_correction_loops:
        blockers.append("Work Unit correction budget exceeds canonical configuration")
    if integrity_issues:
        blockers.extend(integrity_issues)
    dirty = disallowed_dirty_paths(repository_state, config.allowed_dirty_prefixes)
    if dirty:
        blockers.extend(dirty)
    checks.extend(
        (
            f"work_unit={work_unit.id}",
            f"task={work_unit.task_id}",
            f"epic={work_unit.epic_id}",
            f"authority={work_unit.authority_level}",
            f"repository_known={repository_state.known}",
            f"integrity_issues={len(integrity_issues)}",
        )
    )
    status = "NEEDS_OWNER" if decisions else "BLOCKED" if blockers else "PREFLIGHT"
    return status, tuple(checks), tuple(blockers), tuple(decisions)


def _artifact_refs(directory: Path, names: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    return tuple((name, canonical_sha256(directory / name)) for name in names)


def _write_evidence(
    root: Path,
    run_id: str,
    work_unit: WorkUnit,
    preflight: dict[str, object],
    context: ContextPackage | None,
    diff: DiffSummary,
    tests: tuple[TestOutcome, ...],
    reviews: tuple[ReviewOutcome, ...],
    result_values: dict[str, object],
) -> ExecutionResult:
    directory = safe_repo_path(root, f"{DEFAULT_OUTPUT}/executions/{run_id}")
    directory.mkdir(parents=True, exist_ok=True)
    context_manifest = {
        "work_unit_id": context.work_unit_id if context else work_unit.id,
        "budget_bytes": context.budget_bytes if context else work_unit.context_budget,
        "used_bytes": context.used_bytes if context else 0,
        "entries": [
            {
                "path": item.path,
                "classification": item.classification,
                "sha256": item.sha256,
                "size_bytes": item.size_bytes,
                "content_in_evidence": False,
            }
            for item in (context.entries if context else ())
        ],
        "expansions": list(context.expansions if context else ()),
    }
    payloads = {
        "work-unit.json": _json_text(work_unit),
        "preflight.json": _json_text(preflight),
        "context-manifest.json": _json_text(context_manifest),
        "diff-summary.json": _json_text(diff),
        "test-results.json": _json_text(tests),
        "review-results.json": _json_text(reviews),
    }
    for name, content in payloads.items():
        atomic_write_text(directory / name, content)
    refs = _artifact_refs(directory, tuple(payloads))
    result_values["evidence_refs"] = refs
    result = ExecutionResult(**result_values)
    atomic_write_text(directory / "execution-result.json", _json_text(result))
    report = _render_owner_report(result)
    atomic_write_text(directory / "owner-report.md", report)
    return result


def _render_owner_report(result: ExecutionResult) -> str:
    def lines(values: tuple[str, ...]) -> str:
        return "NONE" if not values else "\n".join(f"- {item}" for item in values)

    changes = tuple(sorted(set(result.files_changed + result.files_created + result.files_deleted)))
    test_lines = tuple(
        f"{item.id}: {'PASS' if item.passed else 'FAIL'} (exit={item.exit_code})"
        for item in result.test_results
    )
    review_lines = tuple(f"{item.role}: {item.status}" for item in result.review_results)
    return "\n".join(
        (
            "# FACTORY-001B Owner Report",
            "",
            "## WHAT WAS ATTEMPTED",
            f"{result.work_unit_id} for {result.task_id} / {result.epic_id}",
            "",
            "## WHAT CHANGED",
            lines(changes),
            "",
            "## TESTS",
            lines(test_lines),
            "",
            "## REVIEWS",
            lines(review_lines),
            "",
            "## STATUS",
            result.status,
            "",
            "## BLOCKERS",
            lines(result.blockers),
            "",
            "## OWNER DECISIONS REQUIRED",
            lines(result.owner_decisions_required),
            "",
            "## NEXT ELIGIBLE WORK",
            result.next_eligible_work,
            "",
        )
    )


def _default_run_id(work_unit: WorkUnit) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{work_unit.id}-{stamp}"[:64]


def execute_work_unit(
    root: Path,
    work_unit_path: str,
    *,
    run_id: str | None = None,
    coding_adapter: CodingAgentAdapter | None = None,
    review_adapter: ReviewAdapter | None = None,
) -> ExecutionResult:
    """Execute one canonical Work Unit; callers cannot inject preflight evidence."""

    root = root.resolve()
    started_at = _utc_now()
    started_clock = time.monotonic()
    phase_history: list[PhaseEvent] = [PhaseEvent("READY", started_at)]
    contract_path = safe_repo_path(root, work_unit_path)
    work_unit = load_work_unit(contract_path, root=root)
    effective_run_id = run_id or _default_run_id(work_unit)
    if not RUN_ID.fullmatch(effective_run_id):
        raise WorkUnitError("run_id must be 1..64 safe identifier characters")
    writer = coding_adapter or NotConfiguredCodingAgentAdapter()
    reviewer = review_adapter or NotConfiguredReviewAdapter()

    with exclusive_run_lock(root):
        config = load_daily_config(safe_repo_path(root, DEFAULT_CONFIG))
        registry_error = ""
        try:
            registry = load_registry(safe_repo_path(root, DEFAULT_REGISTRY), root=root)
        except RegistryError as exc:
            registry = None
            registry_error = str(exc)
        repository_state = probe_repository(root)
        integrity_issues = verify_integrity(root, config)
        if registry is None:
            eligibility = "BLOCKED"
            checks = ("registry_valid=false",)
            blockers = (registry_error,)
            decisions = ()
        else:
            eligibility, checks, blockers, decisions = _eligibility(
                root, registry, config, work_unit, repository_state, integrity_issues
            )
        head = _starting_head(root)
        starting_status = repository_state.dirty_paths
        preflight_payload: dict[str, object] = {
            "status": eligibility,
            "checks": checks,
            "blockers": blockers,
            "owner_decisions_required": decisions,
            "starting_head": head,
            "starting_status": starting_status,
            "allowed_paths": work_unit.allowed_paths,
        }
        phase_history.append(PhaseEvent("PREFLIGHT", _utc_now()))
        context: ContextPackage | None = None
        tests: tuple[TestOutcome, ...] = ()
        reviews: tuple[ReviewOutcome, ...] = ()
        correction_loops = 0

        def finish(status: str, extra_blockers: tuple[str, ...] = ()) -> ExecutionResult:
            if phase_history[-1].phase != status:
                phase_history.append(PhaseEvent(status, _utc_now()))
            modified, created, deleted = _changed_path_sets(root)
            visible_paths = tuple(
                path
                for path in sorted(set(modified + created + deleted) - set(starting_status))
                if not path.startswith(f"{DEFAULT_OUTPUT}/")
            )
            final_modified = tuple(path for path in modified if path in visible_paths)
            final_created = tuple(path for path in created if path in visible_paths)
            final_deleted = tuple(path for path in deleted if path in visible_paths)
            diff = _diff_summary(root, visible_paths, work_unit)
            values: dict[str, object] = {
                "run_id": effective_run_id,
                "work_unit_id": work_unit.id,
                "task_id": work_unit.task_id,
                "epic_id": work_unit.epic_id,
                "started_at": started_at,
                "finished_at": _utc_now(),
                "elapsed_ms": max(0, int((time.monotonic() - started_clock) * 1000)),
                "status": status,
                "phase_history": tuple(phase_history),
                "agent_role": writer.name,
                "starting_head": head,
                "starting_status": starting_status,
                "files_changed": final_modified,
                "files_created": final_created,
                "files_deleted": final_deleted,
                "tests_run": tuple(item.id for item in tests),
                "test_results": tests,
                "reviews_run": tuple(item.role for item in reviews),
                "review_results": reviews,
                "context_used": tuple(item.path for item in context.entries) if context else (),
                "context_expansions": context.expansions if context else (),
                "correction_loops_used": correction_loops,
                "diff_summary": diff,
                "evidence_refs": (),
                "blockers": blockers + extra_blockers + diff.unexpected_files,
                "owner_decisions_required": decisions,
                "next_eligible_work": "NONE; dependent Work Units never start automatically.",
                "authority": (
                    ("product_change", work_unit.authority_level),
                    ("commit", False),
                    ("push", False),
                    ("pull_request", False),
                    ("paper", config.paper_authority),
                    ("live", config.live_authority),
                    ("capital", False),
                    ("trading_exchange_execution", False),
                ),
            }
            return _write_evidence(
                root,
                effective_run_id,
                work_unit,
                preflight_payload,
                context,
                diff,
                tests,
                reviews,
                values,
            )

        if eligibility != "PREFLIGHT":
            return finish(eligibility)

        try:
            context = ContextCompiler(root, work_unit).compile()
        except WorkUnitError as exc:
            return finish("BLOCKED", (str(exc),))
        if not writer.configured:
            return finish("NOT_CONFIGURED", ("production coding-agent backend is NOT_CONFIGURED",))

        routing = AgentRouter.select(work_unit, reviewer.available_roles())
        preflight_payload["review_routing"] = _jsonable(routing)
        if routing.unavailable_required:
            return finish(
                "BLOCKED",
                tuple(f"required reviewer unavailable: {role}" for role in routing.unavailable_required),
            )

        correction_findings: tuple[str, ...] = ()
        roles_to_review = routing.selected_roles
        total_review_invocations = 0
        phase_history.append(PhaseEvent("ACTIVE", _utc_now()))
        while True:
            while True:
                request = CodingRequest(
                    work_unit=work_unit,
                    context=context,
                    starting_head=head,
                    starting_status=starting_status,
                    correction_loop=correction_loops,
                    correction_findings=correction_findings,
                )
                outcome = writer.execute(request)
                if outcome.status != "COMPLETED":
                    return finish("FAIL", (f"coding adapter returned {outcome.status}: {outcome.summary}",))
                if outcome.context_requests and outcome.changes:
                    return finish(
                        "BLOCKED",
                        ("coding adapter cannot request context and propose changes together",),
                    )
                if len(context.expansions) + len(outcome.context_requests) > MAX_CONTEXT_EXPANSIONS:
                    return finish("BLOCKED", ("context expansion request limit exceeded",))
                if outcome.context_requests:
                    try:
                        for expansion in outcome.context_requests:
                            context = ContextCompiler(root, work_unit).expand(
                                context, expansion.path, expansion.reason
                            )
                    except WorkUnitError as exc:
                        return finish("BLOCKED", (str(exc),))
                    continue
                try:
                    _apply_changes(root, work_unit, outcome.changes)
                except WorkUnitError as exc:
                    return finish("BLOCKED", (str(exc),))
                break

            modified, created, deleted = _changed_path_sets(root)
            visible_paths = tuple(
                path
                for path in sorted(set(modified + created + deleted) - set(starting_status))
                if not path.startswith(f"{DEFAULT_OUTPUT}/")
            )
            scope_errors = tuple(path for path in visible_paths if not path_allowed(work_unit, path))
            if scope_errors:
                return finish("BLOCKED", tuple(f"scope violation: {path}" for path in scope_errors))

            commands = work_unit.required_tests + _baseline_commands(visible_paths)
            phase_history.append(PhaseEvent("TESTING", _utc_now()))
            diff_check = subprocess.run(
                ["git", "diff", "--check"],
                cwd=root,
                env=_sanitized_environment(),
                shell=False,
                check=False,
                capture_output=True,
                timeout=60,
            )
            diff_test = TestOutcome(
                id="git_diff_check",
                argv=("git", "diff", "--check"),
                exit_code=diff_check.returncode,
                passed=diff_check.returncode == 0,
                elapsed_ms=0,
                stdout_sha256=hashlib.sha256(diff_check.stdout).hexdigest(),
                stderr_sha256=hashlib.sha256(diff_check.stderr).hexdigest(),
                stdout_bytes=len(diff_check.stdout),
                stderr_bytes=len(diff_check.stderr),
                correction_loop=correction_loops,
            )
            test_batch = tuple(
                _run_command(root, command, correction_loops) for command in commands
            ) + (diff_test,)
            tests += test_batch
            failed_tests = tuple(item.id for item in test_batch if not item.passed)
            if failed_tests:
                if correction_loops >= work_unit.max_correction_loops:
                    return finish("FAIL", tuple(f"required test failed: {item}" for item in failed_tests))
                correction_loops += 1
                correction_findings = tuple(f"required test failed: {item}" for item in failed_tests)
                roles_to_review = ()
                continue

            if total_review_invocations + len(roles_to_review) > MAX_REVIEW_INVOCATIONS:
                return finish("BLOCKED", ("absolute reviewer invocation budget exhausted",))
            phase_history.append(PhaseEvent("REVIEW", _utc_now()))
            review_batch = tuple(
                reviewer.review(
                    ReviewRequest(
                        work_unit=work_unit,
                        role=role,
                        changed_paths=visible_paths,
                        correction_loop=correction_loops,
                    )
                )
                for role in roles_to_review
            )
            total_review_invocations += len(review_batch)
            stamped_batch = tuple(
                ReviewOutcome(item.role, item.status, item.findings, correction_loops)
                for item in review_batch
            )
            reviews += stamped_batch
            invalid_reviews = tuple(
                requested
                for requested, outcome_item in zip(roles_to_review, stamped_batch)
                if outcome_item.role != requested
                or outcome_item.status not in {"PASS", "BLOCKED", "FAIL"}
            )
            if invalid_reviews:
                return finish(
                    "BLOCKED",
                    tuple(f"invalid review outcome for requested role: {role}" for role in invalid_reviews),
                )
            blocking_roles = tuple(
                item.role
                for item in stamped_batch
                if item.status != "PASS" or any(finding.blocking for finding in item.findings)
            )
            if blocking_roles:
                if correction_loops >= work_unit.max_correction_loops:
                    return finish(
                        "BLOCKED",
                        tuple(f"blocking review remains: {role}" for role in blocking_roles),
                    )
                correction_loops += 1
                correction_findings = tuple(
                    f"{item.role}: {finding.severity} {finding.location} {finding.message}"
                    for item in stamped_batch
                    for finding in item.findings
                    if finding.blocking
                ) or tuple(f"blocking review: {role}" for role in blocking_roles)
                roles_to_review = blocking_roles
                continue
            return finish("PASS")
