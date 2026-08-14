# FACTORY-001A — implementation plan

## Architecture

The control plane is a standard-library Python package under `factory/`. Registry loading, GitHub workflow-history witnessing, integrity checks, state transitions, preflight, decomposition, planning, and report rendering remain separate modules. The CLI contains no agent or trading adapter; its only network boundary is the bounded read-only GitHub Actions history witness.

## Milestones

1. Freeze registry and configuration contracts.
2. Implement strict registry parsing and state transitions.
3. Implement fail-closed integrity, repository, budget, dependency, and Owner gates.
4. Generate an atomic JSON plan and Markdown Owner Report.
5. Add the 07:00 UTC scheduler and Owner documents.
6. Cover success and failure paths with focused tests.
7. Harden cross-platform lock ownership with a persistent path and continuously held nonblocking POSIX/Windows OS handle lock owned by the public production entry across canonical claim and selection; expose alternate lock/claim namespaces only through private test seams.
8. Persist a strict immutable Moscow-date claim for local processes and require an environment-derived GitHub workflow-history witness before GitHub claim/selection; keep cache as optional transport only.
9. Enforce `READY` Epic/capability/dependency/contract/evidence authority in registry validation and preflight, including both exact paths of NUL-delimited rename/copy records.
10. Remove public and standalone-CLI registry/config/output/probe-evidence injection, enforce the exact singleton dirty allowlist and canonical artifact namespace at every public layer, and keep deterministic substitution behind private test-only boundaries.
11. Pin all workflow actions to reviewed full SHAs and disable checkout credential persistence.

## Verification commands

```bash
python3 -m unittest tests.test_factory_daily_run tests.test_factory_freeze tests.test_factory_github_history tests.test_install_codex_config -v
python3 -m factory.daily_run --dry-run --owner-id local-verification
python3 scripts/self_check.py
python3 -m unittest discover -s tests -v
python3 -m compileall -q factory/configuration.py factory/daily_run.py factory/github_history.py factory/preflight.py factory/registry.py factory/repository.py factory/run_history.py tests/test_factory_daily_run.py tests/test_factory_freeze.py tests/test_factory_github_history.py
ruff check factory/configuration.py factory/daily_run.py factory/github_history.py factory/preflight.py factory/registry.py factory/repository.py factory/run_history.py tests/test_factory_daily_run.py tests/test_factory_freeze.py tests/test_factory_github_history.py
```

The daily workflow verification asserts exact cache restore, then the production runner's API witness/local claim/selection critical section, followed only afterward by optional cache save. The witness cross-checks trusted branch/environment identity, resolves canonical active workflow metadata to a numeric workflow ID, queries runs only by that ID and encoded short branch, ignores candidate path, exhausts bounded pagination, and fails closed on any contradiction; cache state is never an authority input.

## Rollback

Remove only FACTORY-001A package files, registry/config, workflow, focused tests, specification, and Owner documents. Preserve both frozen manifests and all trading/governance artifacts.

Rollback does not delete or rewrite an already-published daily claim. Claim recovery is an Owner operation outside FACTORY-001A.
