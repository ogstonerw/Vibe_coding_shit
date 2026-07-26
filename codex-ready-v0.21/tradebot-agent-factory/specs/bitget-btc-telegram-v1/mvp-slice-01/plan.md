# TB-001 MVP Slice 01 — implementation plan

## Architecture

Python 3.12, только стандартная библиотека:

- `tradebot_mvp/contracts.py` — frozen dataclasses и enums;
- `tradebot_mvp/config.py` — closed TOML loader и policy-bound validation;
- `tradebot_mvp/parser.py` — строгий parser фиксированной грамматики;
- `tradebot_mvp/sizing.py` — Decimal sizing первой risk-leg;
- `tradebot_mvp/journal.py` — SQLite schema и атомарная идемпотентность;
- `tradebot_mvp/service.py` — orchestration одного события;
- `tradebot_mvp/replay.py` — deterministic JSONL replay;
- `tradebot_mvp/__main__.py` — CLI.

Сетевые библиотеки, exchange adapters и secret handling отсутствуют.

## Milestones

1. Зафиксировать contracts, reason codes и closed configuration.
2. Реализовать strict parser и validation.
3. Реализовать Decimal sizing и post-rounding caps.
4. Реализовать journal transaction и event conflict semantics.
5. Реализовать service/replay/CLI.
6. Добавить unit, journal, integration и deterministic replay tests.

## Verification commands

```bash
python3 scripts/self_check.py
python3 -m unittest discover -s tests -v
python3 -m compileall -q tradebot_mvp tests
python3 -m tradebot_mvp replay \
  --input tests/fixtures/mvp_signals.jsonl \
  --config config/mvp-offline-demo.toml \
  --db /tmp/tradebot-mvp-demo.sqlite3
```

## Rollback

Новый код изолирован в `tradebot_mvp/`, новый contract — в
`mvp-slice-01/`. Frozen parent core v11 и frozen PM-DEC-007 addendum не
изменяются. Откат среза не требует изменения governance или portfolio mandate.
