# FACTORY-001A — implementation plan

## Architecture

The control plane is a standard-library Python package under `factory/`. Registry loading, integrity checks, state transitions, preflight, decomposition, planning, and report rendering remain separate deterministic modules. The CLI composes them but contains no agent, network, or trading adapter.

## Milestones

1. Freeze registry and configuration contracts.
2. Implement strict registry parsing and state transitions.
3. Implement fail-closed integrity, repository, budget, dependency, and Owner gates.
4. Generate an atomic JSON plan and Markdown Owner Report.
5. Add the 07:00 UTC scheduler and Owner documents.
6. Cover success and failure paths with focused tests.

## Verification commands

```bash
python3 -m unittest tests.test_factory_daily_run tests.test_factory_freeze tests.test_install_codex_config -v
python3 -m factory.daily_run --dry-run
python3 scripts/self_check.py
python3 -m unittest discover -s tests -v
python3 -m compileall -q factory tests/test_factory_daily_run.py tests/test_factory_freeze.py
ruff check factory tests/test_factory_daily_run.py tests/test_factory_freeze.py
```

## Rollback

Remove only FACTORY-001A package files, registry/config, workflow, focused tests, specification, and Owner documents. Preserve both frozen manifests and all trading/governance artifacts.
