"""Authoritative GitHub Actions daily-run witness for FACTORY-001A."""

from __future__ import annotations

import json
import os
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Callable
from zoneinfo import ZoneInfo


WORKFLOW_FILE = "daily-factory-control-plane.yml"
WORKFLOW_PATH = f".github/workflows/{WORKFLOW_FILE}"
MOSCOW = ZoneInfo("Europe/Moscow")
API_VERSION = "2022-11-28"
USER_AGENT = "FACTORY-001A/1"
PER_PAGE = 100
MAX_PAGES = 3
MAX_BODY_BYTES = 2 * 1024 * 1024
TIMEOUT_SECONDS = 10.0
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
BRANCH_RE = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9._/-]{0,254}$")
TIMESTAMP_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
ALLOWED_STATUSES = frozenset(
    {"queued", "in_progress", "completed", "waiting", "requested", "pending"}
)
ALLOWED_CONCLUSIONS = frozenset(
    {
        None,
        "action_required",
        "cancelled",
        "failure",
        "neutral",
        "skipped",
        "stale",
        "startup_failure",
        "success",
        "timed_out",
    }
)
PRODUCTION_EVENTS = frozenset({"schedule", "workflow_dispatch"})


class GitHubHistoryError(ValueError):
    """Raised when workflow history is consuming, incomplete, or untrusted."""


@dataclass(frozen=True)
class _GitHubContext:
    token: str
    repository: str
    run_id: int
    run_attempt: int
    ref: str
    branch: str
    workflow_path: str
    api_url: str


@dataclass(frozen=True)
class _WorkflowMetadata:
    workflow_id: int
    path: str
    state: str


@dataclass(frozen=True)
class _WorkflowRun:
    run_id: int
    run_attempt: int
    workflow_id: int
    event: str
    status: str
    conclusion: str | None
    run_started_at: datetime
    repository: str
    branch: str


@dataclass(frozen=True)
class GitHubHistoryWitness:
    current_run_id: int
    workflow_id: int
    checked_runs: int


Transport = Callable[[str, dict[str, str], float], tuple[int, bytes]]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def github_actions_enabled() -> bool:
    return os.environ.get("GITHUB_ACTIONS") == "true"


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if not isinstance(value, str) or not value or any(character.isspace() for character in value):
        raise GitHubHistoryError(f"missing or malformed trusted environment field: {name}")
    return value


def _positive_integer(value: str, name: str) -> int:
    if not value.isascii() or not value.isdecimal():
        raise GitHubHistoryError(f"malformed trusted environment field: {name}")
    parsed = int(value)
    if parsed <= 0 or str(parsed) != value:
        raise GitHubHistoryError(f"malformed trusted environment field: {name}")
    return parsed


def _valid_branch(branch: str) -> bool:
    if (
        not BRANCH_RE.fullmatch(branch)
        or branch.endswith(("/", "."))
        or "//" in branch
        or ".." in branch
    ):
        return False
    return all(
        component
        and not component.startswith(".")
        and not component.lower().endswith(".lock")
        for component in branch.split("/")
    )


def _load_github_context() -> _GitHubContext:
    if not github_actions_enabled():
        raise GitHubHistoryError("GitHub Actions witness requested outside GITHUB_ACTIONS")
    token = _required_environment("FACTORY_GITHUB_TOKEN")
    if len(token) > 4096:
        raise GitHubHistoryError("malformed trusted environment field: FACTORY_GITHUB_TOKEN")
    repository = _required_environment("GITHUB_REPOSITORY")
    if not REPOSITORY_RE.fullmatch(repository):
        raise GitHubHistoryError("malformed trusted environment field: GITHUB_REPOSITORY")
    run_id = _positive_integer(_required_environment("GITHUB_RUN_ID"), "GITHUB_RUN_ID")
    run_attempt = _positive_integer(
        _required_environment("GITHUB_RUN_ATTEMPT"), "GITHUB_RUN_ATTEMPT"
    )
    ref = _required_environment("GITHUB_REF")
    if not ref.startswith("refs/heads/"):
        raise GitHubHistoryError("trusted GITHUB_REF must be a branch ref")
    branch = ref.removeprefix("refs/heads/")
    if not _valid_branch(branch):
        raise GitHubHistoryError("malformed trusted branch ref")
    if _required_environment("GITHUB_REF_NAME") != branch:
        raise GitHubHistoryError("trusted GitHub ref and branch name are inconsistent")
    ref_type = os.environ.get("GITHUB_REF_TYPE")
    if ref_type is not None and ref_type != "branch":
        raise GitHubHistoryError("trusted GITHUB_REF_TYPE must be branch")
    workflow_ref = _required_environment("GITHUB_WORKFLOW_REF")
    expected_workflow_ref = f"{repository}/{WORKFLOW_PATH}@{ref}"
    if workflow_ref != expected_workflow_ref:
        raise GitHubHistoryError("trusted GitHub workflow identity is inconsistent")
    api_url = _required_environment("GITHUB_API_URL").rstrip("/")
    parsed_url = urllib.parse.urlsplit(api_url)
    if (
        parsed_url.scheme != "https"
        or not parsed_url.netloc
        or parsed_url.username is not None
        or parsed_url.password is not None
        or parsed_url.query
        or parsed_url.fragment
    ):
        raise GitHubHistoryError("malformed trusted environment field: GITHUB_API_URL")
    return _GitHubContext(
        token,
        repository,
        run_id,
        run_attempt,
        ref,
        branch,
        WORKFLOW_PATH,
        api_url,
    )


def _github_transport(url: str, headers: dict[str, str], timeout: float) -> tuple[int, bytes]:
    request = urllib.request.Request(url, method="GET", headers=headers)
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read(MAX_BODY_BYTES + 1)
            status = response.status
    except urllib.error.HTTPError as exc:
        raise GitHubHistoryError(f"GitHub Actions history HTTP status {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
        raise GitHubHistoryError("GitHub Actions history request unavailable") from exc
    if len(body) > MAX_BODY_BYTES:
        raise GitHubHistoryError("GitHub Actions history response exceeds size limit")
    return status, body


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise GitHubHistoryError(f"malformed GitHub Actions response: duplicate field {key}")
        value[key] = item
    return value


def _load_json_object(body: bytes, location: str) -> dict[str, object]:
    if not isinstance(body, bytes) or len(body) > MAX_BODY_BYTES:
        raise GitHubHistoryError(f"malformed GitHub Actions {location} response")
    try:
        value = json.loads(body.decode("utf-8"), object_pairs_hook=_unique_json_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GitHubHistoryError(f"malformed GitHub Actions {location} response") from exc
    if not isinstance(value, dict):
        raise GitHubHistoryError(f"malformed GitHub Actions {location} response")
    return value


def _positive_int_field(value: object, location: str) -> int:
    if type(value) is not int or value <= 0:
        raise GitHubHistoryError(f"malformed GitHub Actions field: {location}")
    return value


def _text_field(value: object, location: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 512:
        raise GitHubHistoryError(f"malformed GitHub Actions field: {location}")
    return value


def _parse_timestamp(value: object, location: str) -> datetime:
    text = _text_field(value, location)
    if not TIMESTAMP_RE.fullmatch(text):
        raise GitHubHistoryError(f"malformed GitHub Actions field: {location}")
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise GitHubHistoryError(f"malformed GitHub Actions field: {location}") from exc


def _parse_metadata(body: bytes, expected_path: str) -> _WorkflowMetadata:
    value = _load_json_object(body, "workflow metadata")
    metadata = _WorkflowMetadata(
        workflow_id=_positive_int_field(value.get("id"), "workflow.id"),
        path=_text_field(value.get("path"), "workflow.path"),
        state=_text_field(value.get("state"), "workflow.state"),
    )
    if metadata.path != expected_path:
        raise GitHubHistoryError("workflow metadata path does not match trusted workflow path")
    if metadata.state != "active":
        raise GitHubHistoryError("trusted workflow metadata is not active")
    return metadata


def _parse_run(value: object, location: str) -> _WorkflowRun:
    if not isinstance(value, dict):
        raise GitHubHistoryError(f"malformed GitHub Actions field: {location}")
    repository = value.get("repository")
    if not isinstance(repository, dict):
        raise GitHubHistoryError(f"malformed GitHub Actions field: {location}.repository")
    conclusion = value.get("conclusion")
    if conclusion not in ALLOWED_CONCLUSIONS:
        raise GitHubHistoryError(f"malformed GitHub Actions field: {location}.conclusion")
    status = _text_field(value.get("status"), f"{location}.status")
    if status not in ALLOWED_STATUSES:
        raise GitHubHistoryError(f"malformed GitHub Actions field: {location}.status")
    return _WorkflowRun(
        run_id=_positive_int_field(value.get("id"), f"{location}.id"),
        run_attempt=_positive_int_field(
            value.get("run_attempt"), f"{location}.run_attempt"
        ),
        workflow_id=_positive_int_field(
            value.get("workflow_id"), f"{location}.workflow_id"
        ),
        event=_text_field(value.get("event"), f"{location}.event"),
        status=status,
        conclusion=conclusion,
        run_started_at=_parse_timestamp(
            value.get("run_started_at"), f"{location}.run_started_at"
        ),
        repository=_text_field(
            repository.get("full_name"), f"{location}.repository.full_name"
        ),
        branch=_text_field(value.get("head_branch"), f"{location}.head_branch"),
    )


def _parse_runs_page(body: bytes, page: int) -> tuple[int, tuple[_WorkflowRun, ...]]:
    value = _load_json_object(body, "workflow runs")
    total_count = value.get("total_count")
    runs = value.get("workflow_runs")
    if type(total_count) is not int or total_count < 0:
        raise GitHubHistoryError("malformed GitHub Actions workflow runs total_count")
    if not isinstance(runs, list) or len(runs) > PER_PAGE:
        raise GitHubHistoryError("malformed GitHub Actions workflow runs list")
    return total_count, tuple(
        _parse_run(item, f"page[{page}].workflow_runs[{index}]")
        for index, item in enumerate(runs)
    )


def _request(
    url: str,
    headers: dict[str, str],
    transport: Transport,
    response_name: str,
) -> bytes:
    try:
        status, body = transport(url, dict(headers), TIMEOUT_SECONDS)
    except GitHubHistoryError:
        raise
    except (TimeoutError, socket.timeout, OSError) as exc:
        raise GitHubHistoryError(f"GitHub Actions {response_name} request unavailable") from exc
    if status != 200:
        raise GitHubHistoryError(f"GitHub Actions {response_name} HTTP status {status}")
    if not isinstance(body, bytes) or len(body) > MAX_BODY_BYTES:
        raise GitHubHistoryError(f"malformed GitHub Actions {response_name} response")
    return body


def verify_github_daily_history(run_date: date) -> GitHubHistoryWitness:
    """Verify authoritative history from trusted GitHub environment and API only."""

    context = _load_github_context()
    return _verify_github_daily_history_for_test(
        context, run_date, transport=_github_transport
    )


def _verify_github_daily_history_for_test(
    context: _GitHubContext,
    run_date: date,
    *,
    transport: Transport,
) -> GitHubHistoryWitness:
    """Private deterministic seam for bounded transport tests."""

    if context.run_attempt > 1:
        raise GitHubHistoryError("GitHub workflow rerun attempt already consumes this production run")
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {context.token}",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": API_VERSION,
    }
    encoded_repository = "/".join(
        urllib.parse.quote(part, safe="") for part in context.repository.split("/", 1)
    )
    encoded_workflow_file = urllib.parse.quote(WORKFLOW_FILE, safe="")
    metadata_url = (
        f"{context.api_url}/repos/{encoded_repository}/actions/workflows/"
        f"{encoded_workflow_file}"
    )
    metadata = _parse_metadata(
        _request(metadata_url, headers, transport, "workflow metadata"),
        context.workflow_path,
    )

    all_runs: list[_WorkflowRun] = []
    expected_total: int | None = None
    seen_ids: set[int] = set()
    for page in range(1, MAX_PAGES + 1):
        query = urllib.parse.urlencode(
            {"branch": context.branch, "per_page": PER_PAGE, "page": page}
        )
        runs_url = (
            f"{context.api_url}/repos/{encoded_repository}/actions/workflows/"
            f"{metadata.workflow_id}/runs?{query}"
        )
        total_count, runs = _parse_runs_page(
            _request(runs_url, headers, transport, "workflow runs"), page
        )
        if expected_total is None:
            expected_total = total_count
        elif total_count != expected_total:
            raise GitHubHistoryError("GitHub Actions workflow history changed during pagination")
        for run in runs:
            if run.run_id in seen_ids:
                raise GitHubHistoryError("duplicate GitHub Actions workflow run ID")
            if run.workflow_id != metadata.workflow_id:
                raise GitHubHistoryError("workflow run contradicts resolved workflow ID")
            if run.repository != context.repository:
                raise GitHubHistoryError("workflow run contradicts trusted repository")
            if run.branch != context.branch:
                raise GitHubHistoryError("workflow run contradicts trusted branch")
            seen_ids.add(run.run_id)
            all_runs.append(run)
        if len(all_runs) >= expected_total:
            if len(all_runs) != expected_total:
                raise GitHubHistoryError("inconsistent GitHub Actions workflow run count")
            break
        if not runs:
            raise GitHubHistoryError("truncated GitHub Actions workflow history pagination")
    else:
        raise GitHubHistoryError("truncated GitHub Actions workflow history pagination")

    current: _WorkflowRun | None = None
    for run in all_runs:
        if run.run_id == context.run_id:
            if current is not None:
                raise GitHubHistoryError("duplicate current GitHub workflow run witness")
            current = run
    if current is None:
        raise GitHubHistoryError("current GitHub workflow run is absent from authoritative history")
    if (
        current.run_attempt != context.run_attempt
        or current.event not in PRODUCTION_EVENTS
        or current.run_started_at.astimezone(MOSCOW).date() != run_date
    ):
        raise GitHubHistoryError("current GitHub workflow run witness is inconsistent")

    consuming_prior = tuple(
        run.run_id
        for run in all_runs
        if run.run_id != current.run_id
        and run.event in PRODUCTION_EVENTS
        and run.run_started_at.astimezone(MOSCOW).date() == run_date
    )
    if consuming_prior:
        raise GitHubHistoryError("Moscow production date is already consumed by a prior workflow run")
    return GitHubHistoryWitness(context.run_id, metadata.workflow_id, len(all_runs))
