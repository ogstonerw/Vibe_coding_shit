# FACTORY-001B — execution evidence and review

Date: 2026-08-31
Branch: `feature/factory-001b-controlled-execution`
Starting commit: `8021a85ec3a50b9048d31c5ade85ac35adae8f2c`
Scope: repository-local `PRODUCT_CHANGE_LEVEL_A`

## Verdict

`PASS / READY_FOR_LOCAL_COMMIT`, then `REVIEW / READY_FOR_CI` after the
authorized commit. FACTORY-001B is not accepted until fresh Ubuntu CI.

Production coding/model transport is explicitly `NOT_CONFIGURED`. No push,
pull request, merge, product approval, credential, trading/exchange, Paper,
Limited Live, Live, or capital authority was introduced.

## Specialist invocation evidence

The hard budget of three specialist invocations was fully consumed:

1. `system_architect`: unavailable because the configured specialist model is
   not supported on the current account; no retry or fallback agent.
2. `security_reviewer`: same unavailable result; no retry or fallback agent.
3. `code_reviewer`: same unavailable result; no retry or fallback agent.

Per the Owner contract, primary Codex performed each unavailable checklist
directly. Architecture, security, and code checklists are `PASS` with no
unresolved blocking findings. Two correction loops were used; no third loop
was performed.

## Architecture evidence

- Reuses the existing FACTORY registry, integrity probes, atomic writer, and
  persistent OS lock; the FACTORY-001A scheduler is unchanged.
- Keeps Product Graph bootstrap non-operational and links the Work Unit to the
  current canonical Epic/Task/dependency state.
- Separates authority decisions from provider-neutral writer/reviewer
  adapters. Adapters receive bounded data and return structured changes;
  control-plane code alone validates and applies writes.
- Default production adapter returns `NOT_CONFIGURED` without changing product
  files.
- Records phase history, elapsed time, tests, repeated focused reviews,
  corrections, diff statistics, blockers, authority, and durable evidence.

## Security checklist

`PASS` for the current repository-local authority boundary:

- repository-relative path normalization rejects traversal, drive/ADS syntax,
  control characters, reserved Windows names, sensitive scopes, forbidden
  overlaps, and symlink traversal;
- MANDATORY/RELEVANT context rejects credential-like paths; FROZEN is identity
  only; SKIP is never loaded; expansion count and byte budget are cumulative;
- coding adapters do not receive a repository path and cannot directly choose
  authority or apply writes through the interface;
- test commands use approved structured argv, fixed cwd/timeout, `shell=False`,
  sanitized environment, exit-code capture, and output digests;
- the OS lock covers canonical preflight through evidence; a second writer is
  denied;
- required review-role identity/status is validated, so one role cannot forge
  another role's PASS;
- evidence files are written atomically under the control-plane-owned artifact
  scope; raw context and raw command output are not persisted.

Residual risk: any future real adapter transport must preserve the structured
change/read-only review contracts and process isolation. No such transport is
configured or claimed here.

## Code checklist

`PASS`: the implementation is confined to one contract module and one
orchestrator module, reuses FACTORY-001A components, leaves daily scheduling
unchanged, has no trading imports, and traces the 26 acceptance cases through
focused tests. No duplicate Factory registry or Product Graph writer was
created.

## Exact local gates

- `python -m unittest tests.test_factory_execution -v` — `15 PASS`, `1 SKIP`.
  The skip is the Windows privilege restriction on creating the adversarial
  symlink fixture; the deterministic symlink rejection code remains active.
- `python -m unittest tests.test_factory_daily_run tests.test_factory_freeze tests.test_factory_github_history tests.test_install_codex_config -v`
  — `59 PASS`, `1 SKIP` (the existing POSIX-only lock replacement case).
- `python -m compileall -q factory/work_units.py factory/execution.py tests/test_factory_execution.py`
  — PASS.
- `git diff --check` — PASS.
- `ruff check factory/work_units.py factory/execution.py tests/test_factory_execution.py`
  — `BLOCKED_TOOL_UNAVAILABLE`; no dependency was installed.
- Active `docs/FROZEN_CORE_V12.sha256` and
  `docs/FROZEN_PM_DEC_007_HYBRID_V2.sha256` canonical verification — PASS with
  zero mismatched entries.

## Broader Windows diagnostics

`python scripts/self_check.py` reports the pre-existing raw-byte/CRLF mismatch
set for frozen portfolio snapshots and policies. None of the reported paths is
in this Work Unit diff; canonical FACTORY manifests and focused freeze tests
pass. The Work Unit did not alter or re-freeze those artifacts.

`python -m unittest discover -s tests -v` ran 238 tests and reported 13
failures, 14 errors, and 2 skips in unrelated legacy/Windows-sensitive areas:
raw-byte frozen snapshot comparisons, Windows symlink privilege, SQLite handle
cleanup, environment-dependent integration imports, and a Windows mode-bit
expectation. FACTORY-001B focused tests and FACTORY-001A regressions pass in
the same run. Per the Owner instruction, these known unrelated Windows
diagnostics did not expand this Work Unit.

Fresh Ubuntu CI is required after the local commit and is the authoritative
next gate.
