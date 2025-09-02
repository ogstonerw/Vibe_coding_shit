Project test scripts and integration checks.

Run offline scripts manually; many are integration-style and may require environment variables.

Tests here are runnable scripts (not pure pytest units) kept for convenience.

Files:
- `test_watcher.py`, `test_watcher_detailed.py` — watcher smoke tests
- `test_simple_integration.py`, `test_integration_simple.py`, `test_full_integration.py` — integration-style checks
- `test_env.py` — environment variables validator
- `test_control_bot.py` — control bot smoke test
- `test_bitget_integration.py` — Bitget integration dry-run

Use `python tests/<file>.py` to run specific test scripts.
