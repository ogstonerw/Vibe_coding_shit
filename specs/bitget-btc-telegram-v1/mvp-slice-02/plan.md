# TB-001 MVP Slice 02 — implementation plan

## Architecture

Slice 01 remains byte-frozen. Slice 02 adds one standard-library module:

- `tradebot_mvp/telegram_import.py` — bounded Telegram Desktop JSON loader,
  fixed two-source merge, normalization, replayable/skipped metadata journal,
  global event-time watermark, atomic historical replay and standalone CLI.

The importer calls the existing `OfflineSignalService`; parser, sizing,
journal and intent implementation are not copied or changed.

## Milestones

1. Record the actual Telegram Desktop JSON shapes and limitations.
2. Implement bounded single/full-export parsing and ordered text flattening.
3. Define event-time, persistent watermark, revision and conflict semantics.
4. Add pseudonymized replayable/skipped metadata and whole-batch atomicity.
5. Add controlled CLI errors and a private export location.
6. Add anonymized fixtures, failure-mode tests and documentation.

## Verification commands

```bash
python3 scripts/self_check.py
python3 -m unittest discover -s tests -v
python3 -m compileall -q tradebot_mvp tests
ruff check tradebot_mvp/telegram_import.py tests/test_telegram_import.py
python3 -m tradebot_mvp.telegram_import \
  --input tests/fixtures/telegram_desktop_result.json \
  --source scalping \
  --config config/mvp-historical-demo.toml \
  --db /tmp/tradebot-mvp-slice-02.sqlite3
```

## Rollback

Remove only the new Slice 02 module, tests, fixture, config, spec and
documentation, plus the private-directory ignore rule. No frozen Slice 01,
governance, PM-DEC-007 or financial configuration file needs modification.
