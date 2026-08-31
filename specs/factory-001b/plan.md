# FACTORY-001B — implementation plan

## Architecture

Extend the existing standard-library `factory/` package with two cohesive
modules: a strict Work Unit contract/loader and a controlled execution
orchestrator. Reuse the current registry, integrity checks, Git probe, atomic
artifact writer, and persistent OS lock. Do not alter the daily scheduler or
create a second Factory registry.

## Milestones

1. Record the Owner authorization and final Work Unit/acceptance contract.
2. Validate Work Unit schema, authority, registry relation, dependencies,
   path scopes, budgets, context classes, and structured test commands.
3. Compile bounded context and keep FROZEN/SKIP semantics explicit.
4. Add provider-neutral writer/reviewer protocols, deterministic fakes, and
   the `NOT_CONFIGURED` default.
5. Orchestrate one locked writer, focused tests, minimal reviews, bounded
   corrections, path/diff enforcement, evidence, and Owner Report.
6. Prove all 26 acceptance cases and FACTORY-001A regressions.
7. Run independent security/code reviews and final repository gates.
8. Create the single authorized local commit and stop before delivery.

## Verification commands

```text
python -m unittest tests.test_factory_execution -v
python -m unittest tests.test_factory_daily_run tests.test_factory_freeze tests.test_factory_github_history tests.test_install_codex_config -v
python -m compileall -q factory/work_units.py factory/execution.py tests/test_factory_execution.py
git diff --check
ruff check factory/work_units.py factory/execution.py tests/test_factory_execution.py
python scripts/self_check.py
python -m unittest discover -s tests -v
```

If `ruff` is unavailable, record `BLOCKED_TOOL_UNAVAILABLE` for that optional
local lint command; do not install new dependencies or substitute an agent.

## Rollback

Revert only the FACTORY-001B commit after Owner inspection. Runtime failures
never invoke destructive Git recovery. Evidence and a candidate diff remain
inspectable until the Owner chooses a recovery action.
