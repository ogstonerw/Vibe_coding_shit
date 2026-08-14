from __future__ import annotations

import json
import os
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path
from unittest.mock import patch

from factory.configuration import ConfigurationError
from factory.daily_run import execute_daily_run
from factory.github_history import (
    API_VERSION,
    MAX_PAGES,
    PER_PAGE,
    TIMEOUT_SECONDS,
    USER_AGENT,
    WORKFLOW_FILE,
    WORKFLOW_PATH,
    GitHubHistoryError,
    _GitHubContext,
    _load_github_context,
    _verify_github_daily_history_for_test,
    verify_github_daily_history,
)


RUN_DATE = date(2026, 8, 11)
WORKFLOW_ID = 4242
CONTEXT = _GitHubContext(
    token="test-token-never-log",
    repository="owner/repository",
    run_id=100,
    run_attempt=1,
    ref="refs/heads/main",
    branch="main",
    workflow_path=WORKFLOW_PATH,
    api_url="https://api.github.com",
)
_MISSING = object()


def workflow_metadata(
    *,
    workflow_id: object = WORKFLOW_ID,
    path: object = WORKFLOW_PATH,
    state: object = "active",
) -> dict[str, object]:
    return {
        "id": workflow_id,
        "node_id": "W_kwDO-test",
        "name": "daily-factory-control-plane",
        "path": path,
        "state": state,
    }


def workflow_run(
    run_id: int,
    *,
    workflow_id: object = WORKFLOW_ID,
    event: object = "workflow_dispatch",
    status: object = "completed",
    conclusion: object = "success",
    started: object = "2026-08-11T07:00:00Z",
    repository: object = "owner/repository",
    branch: object = "main",
    run_attempt: object = 1,
    path: object = _MISSING,
) -> dict[str, object]:
    value: dict[str, object] = {
        "id": run_id,
        "workflow_id": workflow_id,
        "run_attempt": run_attempt,
        "event": event,
        "status": status,
        "conclusion": conclusion,
        "run_started_at": started,
        "repository": {"full_name": repository},
        "head_branch": branch,
    }
    if path is not _MISSING:
        value["path"] = path
    return value


class FakeTransport:
    def __init__(
        self,
        runs: list[dict[str, object]] | None = None,
        *,
        metadata: dict[str, object] | None = None,
        pages: dict[int, list[dict[str, object]]] | None = None,
        total_count: int | None = None,
        metadata_status: int = 200,
        runs_status: int = 200,
        metadata_body: bytes | None = None,
        runs_body: bytes | None = None,
        error: BaseException | None = None,
    ) -> None:
        self.metadata = metadata if metadata is not None else workflow_metadata()
        self.pages = pages if pages is not None else {1: list(runs or [])}
        self.total_count = (
            total_count
            if total_count is not None
            else sum(len(items) for items in self.pages.values())
        )
        self.metadata_status = metadata_status
        self.runs_status = runs_status
        self.metadata_body = metadata_body
        self.runs_body = runs_body
        self.error = error
        self.calls: list[tuple[str, dict[str, str], float]] = []

    def __call__(
        self, url: str, headers: dict[str, str], timeout: float
    ) -> tuple[int, bytes]:
        self.calls.append((url, headers, timeout))
        if self.error is not None:
            raise self.error
        if "/runs?" not in url:
            body = self.metadata_body
            if body is None:
                body = json.dumps(self.metadata).encode("utf-8")
            return self.metadata_status, body
        body = self.runs_body
        if body is None:
            page = int(url.rsplit("page=", 1)[1])
            body = json.dumps(
                {
                    "total_count": self.total_count,
                    "workflow_runs": self.pages.get(page, []),
                }
            ).encode("utf-8")
        return self.runs_status, body


def verify_with(
    runs: list[dict[str, object]],
    *,
    context: _GitHubContext = CONTEXT,
    transport: FakeTransport | None = None,
):
    effective_transport = transport or FakeTransport(runs)
    witness = _verify_github_daily_history_for_test(
        context, RUN_DATE, transport=effective_transport
    )
    return witness, effective_transport


def trusted_environment(**overrides: str) -> dict[str, str]:
    value = {
        "GITHUB_ACTIONS": "true",
        "FACTORY_GITHUB_TOKEN": CONTEXT.token,
        "GITHUB_REPOSITORY": CONTEXT.repository,
        "GITHUB_RUN_ID": str(CONTEXT.run_id),
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_REF": CONTEXT.ref,
        "GITHUB_REF_NAME": CONTEXT.branch,
        "GITHUB_REF_TYPE": "branch",
        "GITHUB_WORKFLOW_REF": (
            f"{CONTEXT.repository}/{WORKFLOW_PATH}@{CONTEXT.ref}"
        ),
        "GITHUB_API_URL": CONTEXT.api_url,
    }
    value.update(overrides)
    return value


class GitHubHistoryWitnessTests(unittest.TestCase):
    def test_metadata_resolves_canonical_numeric_identity_then_runs_query_uses_only_id(self) -> None:
        current = workflow_run(100, status="in_progress", conclusion=None)
        witness, transport = verify_with([current])
        self.assertEqual((100, WORKFLOW_ID, 1), (
            witness.current_run_id,
            witness.workflow_id,
            witness.checked_runs,
        ))
        self.assertEqual(2, len(transport.calls))
        metadata_url, headers, timeout = transport.calls[0]
        runs_url = transport.calls[1][0]
        self.assertEqual(
            f"https://api.github.com/repos/owner/repository/actions/workflows/{WORKFLOW_FILE}",
            metadata_url,
        )
        self.assertIn(f"/actions/workflows/{WORKFLOW_ID}/runs?", runs_url)
        self.assertNotIn(f"/actions/workflows/{WORKFLOW_FILE}/runs", runs_url)
        self.assertIn("branch=main", runs_url)
        self.assertIn("per_page=100", runs_url)
        self.assertNotIn(CONTEXT.token, metadata_url + runs_url)
        self.assertEqual("application/vnd.github+json", headers["Accept"])
        self.assertEqual(f"Bearer {CONTEXT.token}", headers["Authorization"])
        self.assertEqual(API_VERSION, headers["X-GitHub-Api-Version"])
        self.assertEqual(USER_AGENT, headers["User-Agent"])
        self.assertEqual(TIMEOUT_SECONDS, timeout)

    def test_metadata_failures_are_closed(self) -> None:
        current = workflow_run(100, status="in_progress", conclusion=None)
        cases = {
            "non_200": FakeTransport([current], metadata_status=404),
            "non_object": FakeTransport([current], metadata_body=b"[]"),
            "bool_id": FakeTransport([current], metadata=workflow_metadata(workflow_id=True)),
            "zero_id": FakeTransport([current], metadata=workflow_metadata(workflow_id=0)),
            "path_mismatch": FakeTransport(
                [current], metadata=workflow_metadata(path=".github/workflows/other.yml")
            ),
            "disabled": FakeTransport(
                [current], metadata=workflow_metadata(state="disabled_manually")
            ),
            "duplicate_key": FakeTransport(
                [current],
                metadata_body=(
                    b'{"id":4242,"id":4243,"path":".github/workflows/'
                    b'daily-factory-control-plane.yml","state":"active"}'
                ),
            ),
        }
        for name, transport in cases.items():
            with self.subTest(name=name):
                with self.assertRaises(GitHubHistoryError):
                    verify_with([current], transport=transport)

    def test_candidate_workflow_id_repository_and_branch_contradictions_fail_closed(self) -> None:
        current = workflow_run(100, status="in_progress", conclusion=None)
        cases = (
            workflow_run(99, workflow_id=WORKFLOW_ID + 1),
            workflow_run(99, repository="other/repository"),
            workflow_run(99, branch="attacker"),
        )
        for candidate in cases:
            with self.subTest(candidate=candidate):
                with self.assertRaisesRegex(GitHubHistoryError, "contradicts"):
                    verify_with([current, candidate])

    def test_candidate_path_has_zero_authority_for_current_and_consuming_prior(self) -> None:
        representations = (
            ".github/workflows/daily-factory-control-plane.yml@refs/heads/attacker",
            ".github/workflows/daily-factory-control-plane.yml@attacker",
            ".github/workflows/daily-factory-control-plane.yml@main",
            _MISSING,
            12345,
        )
        for path in representations:
            with self.subTest(path=path):
                current = workflow_run(
                    100, status="in_progress", conclusion=None, path=path
                )
                witness, _ = verify_with([current])
                self.assertEqual(WORKFLOW_ID, witness.workflow_id)
                prior = workflow_run(99, event="schedule", path=path)
                with self.assertRaisesRegex(GitHubHistoryError, "already consumed"):
                    verify_with([current, prior])

    def test_branch_refs_are_strict_and_feature_branch_uses_encoded_short_name(self) -> None:
        invalid = {
            "tag": trusted_environment(
                GITHUB_REF="refs/tags/v1",
                GITHUB_REF_NAME="v1",
                GITHUB_REF_TYPE="tag",
                GITHUB_WORKFLOW_REF=f"{CONTEXT.repository}/{WORKFLOW_PATH}@refs/tags/v1",
            ),
            "pull": trusted_environment(
                GITHUB_REF="refs/pull/12/merge",
                GITHUB_REF_NAME="12/merge",
                GITHUB_WORKFLOW_REF=(
                    f"{CONTEXT.repository}/{WORKFLOW_PATH}@refs/pull/12/merge"
                ),
            ),
            "malformed": trusted_environment(
                GITHUB_REF="refs/heads/feature//unsafe",
                GITHUB_REF_NAME="feature//unsafe",
                GITHUB_WORKFLOW_REF=(
                    f"{CONTEXT.repository}/{WORKFLOW_PATH}@refs/heads/feature//unsafe"
                ),
            ),
            "name_contradiction": trusted_environment(GITHUB_REF_NAME="attacker"),
            "type_contradiction": trusted_environment(GITHUB_REF_TYPE="tag"),
        }
        for name, environment in invalid.items():
            with self.subTest(name=name), patch.dict(os.environ, environment, clear=True):
                with self.assertRaises(GitHubHistoryError):
                    _load_github_context()

        feature = "feature/factory-witness"
        feature_context = replace(
            CONTEXT,
            ref=f"refs/heads/{feature}",
            branch=feature,
        )
        current = workflow_run(
            100, status="in_progress", conclusion=None, branch=feature
        )
        witness, transport = verify_with([current], context=feature_context)
        self.assertEqual(WORKFLOW_ID, witness.workflow_id)
        self.assertIn("branch=feature%2Ffactory-witness", transport.calls[1][0])

    def test_trusted_workflow_ref_is_exactly_cross_checked(self) -> None:
        cases = {
            "missing": None,
            "empty": "",
            "foreign_repository": (
                f"attacker/repository/{WORKFLOW_PATH}@{CONTEXT.ref}"
            ),
            "foreign_workflow": (
                f"{CONTEXT.repository}/.github/workflows/other.yml@{CONTEXT.ref}"
            ),
            "foreign_ref": (
                f"{CONTEXT.repository}/{WORKFLOW_PATH}@refs/heads/attacker"
            ),
            "short_ref": f"{CONTEXT.repository}/{WORKFLOW_PATH}@main",
            "unsuffixed": f"{CONTEXT.repository}/{WORKFLOW_PATH}",
            "similar_path": (
                f"{CONTEXT.repository}/{WORKFLOW_PATH}.evil@{CONTEXT.ref}"
            ),
            "duplicate_at": (
                f"{CONTEXT.repository}/{WORKFLOW_PATH}@@{CONTEXT.ref}"
            ),
        }
        for name, workflow_ref in cases.items():
            with self.subTest(name=name):
                environment = trusted_environment()
                if workflow_ref is None:
                    del environment["GITHUB_WORKFLOW_REF"]
                else:
                    environment["GITHUB_WORKFLOW_REF"] = workflow_ref
                with patch.dict(os.environ, environment, clear=True):
                    with self.assertRaises(GitHubHistoryError):
                        _load_github_context()

    def test_no_prior_is_available_and_all_started_production_outcomes_consume(self) -> None:
        current = workflow_run(100, status="in_progress", conclusion=None)
        witness, _ = verify_with([current])
        self.assertEqual(1, witness.checked_runs)
        cases = (
            ("schedule", "completed", "success"),
            ("workflow_dispatch", "completed", "failure"),
            ("schedule", "completed", "cancelled"),
            ("workflow_dispatch", "in_progress", None),
        )
        for event, status, conclusion in cases:
            with self.subTest(event=event, status=status, conclusion=conclusion):
                prior = workflow_run(
                    99, event=event, status=status, conclusion=conclusion
                )
                with self.assertRaisesRegex(GitHubHistoryError, "already consumed"):
                    verify_with([current, prior])

    def test_schedule_and_manual_history_block_each_other(self) -> None:
        for current_event, prior_event in (
            ("workflow_dispatch", "schedule"),
            ("schedule", "workflow_dispatch"),
        ):
            with self.subTest(current=current_event, prior=prior_event):
                current = workflow_run(
                    100,
                    event=current_event,
                    status="in_progress",
                    conclusion=None,
                )
                prior = workflow_run(99, event=prior_event)
                with self.assertRaisesRegex(GitHubHistoryError, "already consumed"):
                    verify_with([current, prior])

    def test_previous_moscow_date_and_nonproduction_event_do_not_consume(self) -> None:
        current = workflow_run(100, status="in_progress", conclusion=None)
        previous = workflow_run(99, started="2026-08-10T07:00:00Z")
        push = workflow_run(98, event="push")
        witness, _ = verify_with([current, previous, push])
        self.assertEqual(3, witness.checked_runs)

    def test_rerun_attempt_denies_before_metadata_or_history_api(self) -> None:
        transport = FakeTransport([workflow_run(100)])
        with self.assertRaisesRegex(GitHubHistoryError, "rerun attempt"):
            _verify_github_daily_history_for_test(
                replace(CONTEXT, run_attempt=2),
                RUN_DATE,
                transport=transport,
            )
        self.assertEqual([], transport.calls)

    def test_malformed_run_attempt_environment_fails_closed(self) -> None:
        for attempt in ("", "0", "01", "-1", "true", "two"):
            with self.subTest(attempt=attempt), patch.dict(
                os.environ,
                trusted_environment(GITHUB_RUN_ATTEMPT=attempt),
                clear=True,
            ):
                with self.assertRaises(GitHubHistoryError):
                    _load_github_context()

    def test_current_run_is_fully_witnessed_before_exact_id_exclusion(self) -> None:
        cases = {
            "absent": [workflow_run(99, started="2026-08-10T07:00:00Z")],
            "attempt": [workflow_run(100, run_attempt=2)],
            "event": [workflow_run(100, event="push")],
            "date": [workflow_run(100, started="2026-08-10T07:00:00Z")],
        }
        for name, runs in cases.items():
            with self.subTest(name=name):
                with self.assertRaisesRegex(
                    GitHubHistoryError, "current GitHub workflow run"
                ):
                    verify_with(runs)

    def test_api_unavailable_non_200_and_malformed_responses_fail_closed(self) -> None:
        current = workflow_run(100, status="in_progress", conclusion=None)
        cases = {
            "unavailable": FakeTransport(error=TimeoutError("hidden")),
            "runs_non_200": FakeTransport([current], runs_status=503),
            "runs_non_object": FakeTransport([current], runs_body=b"[]"),
            "runs_missing": FakeTransport([current], runs_body=b'{"total_count":1}'),
            "bool_workflow_id": FakeTransport(
                [workflow_run(100, workflow_id=True)]
            ),
            "bad_timestamp": FakeTransport(
                [workflow_run(100, started="2026-08-11 07:00:00")]
            ),
        }
        for name, transport in cases.items():
            with self.subTest(name=name):
                with self.assertRaises(GitHubHistoryError):
                    verify_with([current], transport=transport)

    def test_exhaustive_pagination_cannot_hide_consuming_run(self) -> None:
        current = workflow_run(100, status="in_progress", conclusion=None)
        harmless = [
            workflow_run(1000 + index, event="push", started="2026-08-10T07:00:00Z")
            for index in range(PER_PAGE - 1)
        ]
        consuming = workflow_run(9999, event="schedule")
        transport = FakeTransport(
            pages={1: [current, *harmless], 2: [consuming]},
            total_count=PER_PAGE + 1,
        )
        with self.assertRaisesRegex(GitHubHistoryError, "already consumed"):
            verify_with([], transport=transport)
        self.assertEqual(3, len(transport.calls))

    def test_incomplete_or_changing_pagination_fails_closed(self) -> None:
        current = workflow_run(100, status="in_progress", conclusion=None)
        first_page = [current] + [
            workflow_run(1000 + index, event="push", started="2026-08-10T07:00:00Z")
            for index in range(PER_PAGE - 1)
        ]
        truncated = FakeTransport(
            pages={1: first_page, 2: []},
            total_count=PER_PAGE + 1,
        )
        with self.assertRaisesRegex(GitHubHistoryError, "truncated"):
            verify_with([], transport=truncated)

        over_limit_pages = {
            page: [
                workflow_run(
                    page * 10000 + index,
                    event="push",
                    started="2026-08-10T07:00:00Z",
                )
                for index in range(PER_PAGE)
            ]
            for page in range(1, MAX_PAGES + 1)
        }
        over_limit_pages[1][0] = current
        too_many = FakeTransport(
            pages=over_limit_pages,
            total_count=MAX_PAGES * PER_PAGE + 1,
        )
        with self.assertRaisesRegex(GitHubHistoryError, "truncated"):
            verify_with([], transport=too_many)

    def test_public_witness_uses_environment_and_real_transport_boundary_only(self) -> None:
        current = workflow_run(100, status="in_progress", conclusion=None)
        transport = FakeTransport([current])
        with (
            patch.dict(os.environ, trusted_environment(), clear=True),
            patch("factory.github_history._github_transport", side_effect=transport),
        ):
            witness = verify_github_daily_history(RUN_DATE)
            with self.assertRaises(TypeError):
                verify_github_daily_history(RUN_DATE, context=CONTEXT)
        self.assertEqual(WORKFLOW_ID, witness.workflow_id)

    def test_production_witness_precedes_claim_and_failure_stops_before_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            events: list[str] = []

            def witness(_run_date: date) -> None:
                events.append("witness")

            def claim(*_args, **_kwargs) -> None:
                events.append("claim")

            with (
                patch("factory.daily_run.load_daily_config", return_value=object()),
                patch("factory.daily_run.load_registry", return_value=object()),
                patch("factory.daily_run.github_actions_enabled", return_value=True),
                patch("factory.daily_run.verify_github_daily_history", side_effect=witness),
                patch("factory.daily_run.claim_daily_run", side_effect=claim),
                patch("factory.daily_run.probe_repository", return_value=object()),
                patch("factory.daily_run.verify_integrity", return_value=()),
                patch(
                    "factory.daily_run._execute_daily_run_core",
                    side_effect=ConfigurationError("stop after ordering evidence"),
                ),
            ):
                with self.assertRaises(ConfigurationError):
                    execute_daily_run(root, owner_id="100:1", run_date=RUN_DATE)
            self.assertEqual(["witness", "claim"], events)

            with (
                patch("factory.daily_run.load_daily_config", return_value=object()),
                patch("factory.daily_run.load_registry", return_value=object()),
                patch("factory.daily_run.github_actions_enabled", return_value=True),
                patch(
                    "factory.daily_run.verify_github_daily_history",
                    side_effect=GitHubHistoryError("API unavailable"),
                ),
                patch("factory.daily_run.claim_daily_run") as local_claim,
            ):
                with self.assertRaises(GitHubHistoryError):
                    execute_daily_run(root, owner_id="100:1", run_date=RUN_DATE)
            local_claim.assert_not_called()


if __name__ == "__main__":
    unittest.main()
