"""Strict FACTORY-001B Work Unit contracts and bounded context compilation."""

from __future__ import annotations

import hashlib
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .integrity import canonical_bytes, safe_repo_path


class WorkUnitError(ValueError):
    """Raised when a Work Unit is ambiguous, unsafe, or incomplete."""


AUTHORITY_LEVELS = frozenset(
    {"PRODUCT_CHANGE_LEVEL_A", "PRODUCT_CHANGE_LEVEL_B", "PRODUCT_CHANGE_LEVEL_C"}
)
WORK_UNIT_STATUSES = frozenset(
    {"READY", "PREFLIGHT", "ACTIVE", "TESTING", "REVIEW", "PASS", "FAIL", "BLOCKED", "NEEDS_OWNER"}
)
REASONING_BUDGETS = frozenset({"LOW", "MEDIUM", "HIGH", "XHIGH"})
WORK_SIZES = frozenset({"NORMAL", "LARGE"})
REVIEW_ROLES = frozenset(
    {
        "system_architect",
        "code_reviewer",
        "security_reviewer",
        "risk_reviewer",
        "institutional_portfolio_reviewer",
        "quant_methodology_reviewer",
        "market_microstructure_reviewer",
    }
)
SENSITIVE_SCOPES = (
    ".github/",
    "governance/",
    "risk/",
    "adapters/",
    "tradebot_mvp/",
    "factory/artifacts/",
    "docs/FROZEN_CORE_V12.sha256",
    "docs/FROZEN_PM_DEC_007_HYBRID_V2.sha256",
)
SENSITIVE_NAME_PARTS = frozenset({".env", "_env", "credentials", "credential", "secrets", "secret"})
EVIDENCE_REQUIREMENTS = frozenset(
    {
        "work_unit_contract",
        "preflight_result",
        "context_manifest",
        "execution_result",
        "diff_summary",
        "test_results",
        "review_results",
        "final_verdict",
        "owner_report",
    }
)
ROOT_KEYS = frozenset(
    {
        "schema_version",
        "id",
        "task_id",
        "epic_id",
        "goal",
        "status",
        "authority_level",
        "work_size",
        "allowed_paths",
        "forbidden_paths",
        "mandatory_context",
        "relevant_context",
        "frozen_context",
        "skip_context",
        "acceptance_criteria",
        "required_tests",
        "required_reviews",
        "optional_reviews",
        "reasoning_budget",
        "context_budget",
        "review_budget",
        "max_correction_loops",
        "dependencies",
        "evidence_requirements",
    }
)
TEST_KEYS = frozenset({"id", "argv", "timeout_seconds"})
PYTHON_TEST_MODULES = frozenset({"unittest", "pytest", "compileall"})
DIRECT_TEST_EXECUTABLES = frozenset({"pytest", "pytest.exe", "ruff", "ruff.exe"})
DRIVE_PATH = re.compile(r"^[A-Za-z]:")
WINDOWS_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL", *(f"COM{index}" for index in range(1, 10)), *(f"LPT{index}" for index in range(1, 10))}
)


@dataclass(frozen=True)
class TestCommand:
    id: str
    argv: tuple[str, ...]
    timeout_seconds: int


@dataclass(frozen=True)
class WorkUnit:
    schema_version: int
    id: str
    task_id: str
    epic_id: str
    goal: str
    status: str
    authority_level: str
    work_size: str
    allowed_paths: tuple[str, ...]
    forbidden_paths: tuple[str, ...]
    mandatory_context: tuple[str, ...]
    relevant_context: tuple[str, ...]
    frozen_context: tuple[str, ...]
    skip_context: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    required_tests: tuple[TestCommand, ...]
    required_reviews: tuple[str, ...]
    optional_reviews: tuple[str, ...]
    reasoning_budget: str
    context_budget: int
    review_budget: int
    max_correction_loops: int
    dependencies: tuple[str, ...]
    evidence_requirements: tuple[str, ...]


@dataclass(frozen=True)
class ContextEntry:
    path: str
    classification: str
    sha256: str
    size_bytes: int
    content: str | None = None


@dataclass(frozen=True)
class ContextPackage:
    work_unit_id: str
    budget_bytes: int
    used_bytes: int
    entries: tuple[ContextEntry, ...]
    expansions: tuple[tuple[str, str], ...] = ()


def normalize_repo_scope(value: object, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or "\x00" in value
        or any(ord(character) < 32 for character in value)
    ):
        raise WorkUnitError(f"{field} must be non-empty repository-relative text")
    raw = value.replace("\\", "/")
    directory = raw.endswith("/")
    if raw.startswith("/") or DRIVE_PATH.match(raw) or ":" in raw:
        raise WorkUnitError(f"{field} must remain repository-relative")
    path = PurePosixPath(raw)
    if any(
        part in {"", ".", ".."}
        or part.endswith((" ", "."))
        or part.split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES
        for part in path.parts
    ):
        raise WorkUnitError(f"{field} contains an ambiguous or escaping segment")
    normalized = path.as_posix()
    return f"{normalized}/" if directory else normalized


def scope_contains(scope: str, path: str) -> bool:
    return path.startswith(scope) if scope.endswith("/") else path == scope


def _scope_contains_casefold(scope: str, path: str) -> bool:
    folded_scope = scope.casefold()
    folded_path = path.casefold()
    return folded_path.startswith(folded_scope) if scope.endswith("/") else folded_path == folded_scope


def scopes_overlap(left: str, right: str) -> bool:
    return _scope_contains_casefold(left, right.rstrip("/")) or _scope_contains_casefold(
        right, left.rstrip("/")
    )


def sensitive_path(path: str) -> bool:
    lowered = path.lower()
    if any(scope_contains(scope.lower(), lowered) for scope in SENSITIVE_SCOPES):
        return True
    return any(
        part.lower() in SENSITIVE_NAME_PARTS
        or part.lower().startswith(".env")
        or any(marker in part.lower() for marker in ("credential", "secret", "api_key"))
        for part in PurePosixPath(path).parts
    )


def _reject_linked_path(root: Path, relative: str, field: str) -> Path:
    lexical = root.resolve()
    for part in PurePosixPath(relative).parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise WorkUnitError(f"{field} must not traverse a symbolic link: {relative}")
    return safe_repo_path(root, relative)


def path_allowed(work_unit: WorkUnit, path: str) -> bool:
    normalized = normalize_repo_scope(path, "changed path")
    if sensitive_path(normalized):
        return False
    if any(_scope_contains_casefold(scope, normalized) for scope in work_unit.forbidden_paths):
        return False
    return any(scope_contains(scope, normalized) for scope in work_unit.allowed_paths)


def _text(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise WorkUnitError(f"{key} must be non-empty text")
    return value


def _text_tuple(raw: dict[str, Any], key: str, *, paths: bool = False) -> tuple[str, ...]:
    value = raw.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise WorkUnitError(f"{key} must be a list of non-empty strings")
    result = tuple(
        normalize_repo_scope(item, f"{key}[{index}]") if paths else item
        for index, item in enumerate(value)
    )
    if len(result) != len(set(result)):
        raise WorkUnitError(f"{key} must not contain duplicates")
    return result


def _positive_int(raw: dict[str, Any], key: str, *, minimum: int = 1, maximum: int) -> int:
    value = raw.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise WorkUnitError(f"{key} must be an integer in [{minimum}, {maximum}]")
    return value


def _validate_test_command(raw: object, index: int) -> TestCommand:
    location = f"required_tests[{index}]"
    if not isinstance(raw, dict) or set(raw) != TEST_KEYS:
        raise WorkUnitError(f"{location} must contain exactly {sorted(TEST_KEYS)}")
    identifier = raw.get("id")
    argv = raw.get("argv")
    timeout = raw.get("timeout_seconds")
    if not isinstance(identifier, str) or not identifier:
        raise WorkUnitError(f"{location}.id must be non-empty text")
    if (
        not isinstance(argv, list)
        or not 1 <= len(argv) <= 64
        or any(not isinstance(item, str) or not item or "\x00" in item for item in argv)
    ):
        raise WorkUnitError(f"{location}.argv must contain 1..64 non-empty arguments")
    executable = PurePosixPath(argv[0].replace("\\", "/")).name.lower()
    module = ""
    if executable in {"python", "python.exe", "python3", "python3.exe", "py", "py.exe"}:
        if len(argv) < 3 or argv[1] != "-m" or argv[2] not in PYTHON_TEST_MODULES:
            raise WorkUnitError(f"{location}.argv uses an unapproved Python test module")
        module = argv[2]
    elif executable not in DIRECT_TEST_EXECUTABLES:
        raise WorkUnitError(f"{location}.argv uses an unapproved executable")
    arguments = argv[3:] if module else argv[1:]
    previous = ""
    for argument_index, argument in enumerate(arguments):
        if argument.startswith("-"):
            previous = argument
            continue
        if module == "unittest" and (
            argument != "discover"
            and previous not in {"-s", "-p", "-t"}
            and not argument.startswith("tests.")
        ):
            raise WorkUnitError(f"{location}.argv unittest targets must remain under tests")
        if module == "pytest" or executable in {"pytest", "pytest.exe"}:
            if "/" in argument or "\\" in argument:
                target = normalize_repo_scope(argument, f"{location}.argv[{argument_index}]")
                if not scope_contains("tests/", target):
                    raise WorkUnitError(f"{location}.argv pytest targets must remain under tests")
        if module == "compileall" and not argument.startswith("-"):
            target = normalize_repo_scope(argument, f"{location}.argv[{argument_index}]")
            if sensitive_path(target):
                raise WorkUnitError(f"{location}.argv targets sensitive scope")
        previous = argument
    if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 900:
        raise WorkUnitError(f"{location}.timeout_seconds must be in [1, 900]")
    return TestCommand(identifier, tuple(argv), timeout)


def parse_work_unit(raw: object) -> WorkUnit:
    if not isinstance(raw, dict):
        raise WorkUnitError("Work Unit root must be a table")
    unknown = set(raw) - ROOT_KEYS
    missing = ROOT_KEYS - set(raw)
    if unknown or missing:
        raise WorkUnitError(f"Work Unit fields mismatch: missing={sorted(missing)}, unknown={sorted(unknown)}")
    if raw.get("schema_version") != 1:
        raise WorkUnitError("schema_version must be 1")

    allowed = _text_tuple(raw, "allowed_paths", paths=True)
    forbidden = _text_tuple(raw, "forbidden_paths", paths=True)
    mandatory = _text_tuple(raw, "mandatory_context", paths=True)
    relevant = _text_tuple(raw, "relevant_context", paths=True)
    frozen = _text_tuple(raw, "frozen_context", paths=True)
    skipped = _text_tuple(raw, "skip_context", paths=True)
    acceptance = _text_tuple(raw, "acceptance_criteria")
    evidence = _text_tuple(raw, "evidence_requirements")
    dependencies = _text_tuple(raw, "dependencies")
    required_reviews = _text_tuple(raw, "required_reviews")
    optional_reviews = _text_tuple(raw, "optional_reviews")

    if not allowed:
        raise WorkUnitError("allowed_paths must not be empty")
    if not acceptance:
        raise WorkUnitError("acceptance_criteria must not be empty")
    if not evidence:
        raise WorkUnitError("evidence_requirements must not be empty")
    unknown_evidence = set(evidence) - EVIDENCE_REQUIREMENTS
    if unknown_evidence:
        raise WorkUnitError(f"unknown evidence requirements: {sorted(unknown_evidence)}")
    if set(required_reviews) & set(optional_reviews):
        raise WorkUnitError("required_reviews and optional_reviews must be disjoint")
    unknown_roles = (set(required_reviews) | set(optional_reviews)) - REVIEW_ROLES
    if unknown_roles:
        raise WorkUnitError(f"unknown review roles: {sorted(unknown_roles)}")

    context_groups = {
        "mandatory_context": set(mandatory),
        "relevant_context": set(relevant),
        "frozen_context": set(frozen),
        "skip_context": set(skipped),
    }
    names = tuple(context_groups)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            overlap = any(
                scopes_overlap(left_scope, right_scope)
                for left_scope in context_groups[left]
                for right_scope in context_groups[right]
            )
            if overlap:
                raise WorkUnitError(f"{left} and {right} must be disjoint scopes")
    for scope in allowed:
        if sensitive_path(scope) or any(scopes_overlap(scope, denied) for denied in forbidden):
            raise WorkUnitError(f"allowed path overlaps denied scope: {scope}")
    for relative in mandatory + relevant:
        if sensitive_path(relative):
            raise WorkUnitError(f"included context targets sensitive path: {relative}")

    tests_raw = raw.get("required_tests")
    if not isinstance(tests_raw, list) or not tests_raw:
        raise WorkUnitError("required_tests must be a non-empty list")
    tests = tuple(_validate_test_command(item, index) for index, item in enumerate(tests_raw))
    if len({item.id for item in tests}) != len(tests):
        raise WorkUnitError("required_tests ids must be unique")

    status = _text(raw, "status")
    authority = _text(raw, "authority_level")
    reasoning = _text(raw, "reasoning_budget")
    work_size = _text(raw, "work_size")
    if status not in WORK_UNIT_STATUSES:
        raise WorkUnitError(f"unknown Work Unit status: {status}")
    if authority not in AUTHORITY_LEVELS:
        raise WorkUnitError(f"unknown authority_level: {authority}")
    if reasoning not in REASONING_BUDGETS:
        raise WorkUnitError(f"unknown reasoning_budget: {reasoning}")
    if work_size not in WORK_SIZES:
        raise WorkUnitError(f"unknown work_size: {work_size}")

    context_budget = _positive_int(raw, "context_budget", maximum=10_000_000)
    review_budget = _positive_int(raw, "review_budget", minimum=0, maximum=5)
    correction_budget = _positive_int(raw, "max_correction_loops", minimum=0, maximum=2)
    routing_cap = 2 if work_size == "NORMAL" else 4
    if review_budget > routing_cap:
        raise WorkUnitError(f"{work_size} review_budget exceeds {routing_cap}")
    if len(required_reviews) > review_budget:
        raise WorkUnitError("required_reviews exceed review_budget")

    return WorkUnit(
        schema_version=1,
        id=_text(raw, "id"),
        task_id=_text(raw, "task_id"),
        epic_id=_text(raw, "epic_id"),
        goal=_text(raw, "goal"),
        status=status,
        authority_level=authority,
        work_size=work_size,
        allowed_paths=allowed,
        forbidden_paths=forbidden,
        mandatory_context=mandatory,
        relevant_context=relevant,
        frozen_context=frozen,
        skip_context=skipped,
        acceptance_criteria=acceptance,
        required_tests=tests,
        required_reviews=required_reviews,
        optional_reviews=optional_reviews,
        reasoning_budget=reasoning,
        context_budget=context_budget,
        review_budget=review_budget,
        max_correction_loops=correction_budget,
        dependencies=dependencies,
        evidence_requirements=evidence,
    )


def load_work_unit(path: Path, *, root: Path) -> WorkUnit:
    try:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise WorkUnitError(f"cannot load Work Unit {path}: {exc}") from exc
    work_unit = parse_work_unit(raw)
    for field in ("mandatory_context", "relevant_context", "frozen_context"):
        for relative in getattr(work_unit, field):
            candidate = _reject_linked_path(root, relative, field)
            if not candidate.is_file():
                raise WorkUnitError(f"missing {field}: {relative}")
    return work_unit


class ContextCompiler:
    """Compile minimum sufficient UTF-8 context under the Work Unit byte cap."""

    def __init__(self, root: Path, work_unit: WorkUnit):
        self.root = root.resolve()
        self.work_unit = work_unit

    def _entry(self, relative: str, classification: str, *, include: bool) -> ContextEntry:
        path = _reject_linked_path(self.root, relative, f"{classification} context")
        try:
            raw = canonical_bytes(path)
            text = raw.decode("utf-8") if include else None
        except (OSError, UnicodeDecodeError) as exc:
            raise WorkUnitError(f"cannot compile {classification} context {relative}: {exc}") from exc
        return ContextEntry(
            path=relative,
            classification=classification,
            sha256=hashlib.sha256(raw).hexdigest(),
            size_bytes=len(raw),
            content=text,
        )

    def compile(self) -> ContextPackage:
        entries: list[ContextEntry] = []
        used = 0
        for classification, values, include in (
            ("MANDATORY", self.work_unit.mandatory_context, True),
            ("RELEVANT", self.work_unit.relevant_context, True),
            ("FROZEN", self.work_unit.frozen_context, False),
        ):
            for relative in values:
                entry = self._entry(relative, classification, include=include)
                if include:
                    used += entry.size_bytes
                    if used > self.work_unit.context_budget:
                        raise WorkUnitError(
                            f"context budget exceeded: {used}/{self.work_unit.context_budget} bytes"
                        )
                entries.append(entry)
        entries.extend(
            ContextEntry(relative, "SKIP", "", 0, None)
            for relative in self.work_unit.skip_context
        )
        return ContextPackage(
            work_unit_id=self.work_unit.id,
            budget_bytes=self.work_unit.context_budget,
            used_bytes=used,
            entries=tuple(entries),
        )

    def expand(self, package: ContextPackage, path: str, reason: str) -> ContextPackage:
        relative = normalize_repo_scope(path, "context expansion path")
        if relative.endswith("/") or not reason.strip():
            raise WorkUnitError("context expansion requires a file and concrete reason")
        if any(_scope_contains_casefold(scope, relative) for scope in self.work_unit.skip_context):
            raise WorkUnitError(f"context expansion targets SKIP scope: {relative}")
        if sensitive_path(relative):
            raise WorkUnitError(f"context expansion targets sensitive scope: {relative}")
        if any(item.path == relative for item in package.entries):
            return package
        entry = self._entry(relative, "EXPANDED", include=True)
        used = package.used_bytes + entry.size_bytes
        if used > package.budget_bytes:
            raise WorkUnitError(f"context budget exceeded: {used}/{package.budget_bytes} bytes")
        return ContextPackage(
            work_unit_id=package.work_unit_id,
            budget_bytes=package.budget_bytes,
            used_bytes=used,
            entries=package.entries + (entry,),
            expansions=package.expansions + ((relative, reason.strip()),),
        )
