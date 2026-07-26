# TB-001 MVP Slice 01 — final review evidence

Дата: 24.07.2026  
Stage: `OFFLINE_SIMULATION`  
Release authority: non-paper, non-live, non-capital

## Реализованный путь

`JSONL Telegram-like event → strict parser → validation → Decimal first-leg
sizing → simulated LIMIT intent → SQLite journal → deterministic replay`.

Реальные Telegram/Bitget подключения, биржевые заявки, fills и paper/live
стадии отсутствуют.

## Verification

```text
python3 -m unittest discover -s tests -p 'test_tradebot_mvp*.py' -v
29/29 PASS

python3 -m unittest discover -s tests -v
105/105 PASS

python3 scripts/self_check.py
PASS

python3 -m compileall -q tradebot_mvp tests
PASS
```

External Ruff не установлен в runtime; проект не добавляет внешние
dependencies, поэтому обязательные проверки этого среза используют stdlib
unittest, self-check и compileall.

## Независимые findings и исправления

- Decimal tick/sizing изолирован от ambient context и `DefaultContext.traps`.
- Config fingerprint проверяется до доступа к replay input.
- Identity integers имеют явную signed-64-bit границу.
- Повреждённый SQLite, deep JSON, surrogate strings и сложный TOML дают
  детерминированный отказ без traceback.
- Input и config читаются с фиксированными byte/line/record limits.
- Source связан с точным test channel allowlist и не может выбрать чужой
  allocation bucket.
- `#BTC` и неописанные формы grammar отклоняются.
- SQLite target не может быть symlink/non-regular; DB/WAL/SHM имеют mode
  `0600`.
- Raw channel ID, message text и полный payload не сохраняются в SQLite и не
  выводятся в stdout.
- Journal monetary values записываются canonical decimal text.

## Final verdicts

| Review | Verdict |
|---|---|
| Test engineer | PASS |
| Code review | PASS |
| Local input/privacy review | PASS |
| Risk review | PASS |
| Fresh institutional evidence review | PASS |
| Fresh quant evidence review | PASS |
| Fresh execution/microstructure evidence review | PASS |

Unresolved `MEDIUM+`: `NONE`.

## Acceptance traceability

- `MVP-AC-001`: closed/fingerprinted test-only config, allowlists and bounded
  parser.
- `MVP-AC-002…004`: strict BTC grammar, stop geometry and ignored source risk.
- `MVP-AC-005`: Decimal first-leg cap, tick/step/risk/margin boundaries.
- `MVP-AC-006`: one simulated LIMIT intent, zero network/exchange path.
- `MVP-AC-007`: atomic SQLite, duplicate/conflict/rollback and private journal.
- `MVP-AC-008`: five journal-local active setups maximum.
- `MVP-AC-009`: deterministic fresh replay, same-DB duplicates and input
  preflight.
- `MVP-AC-010`: deferred scope remains explicitly unimplemented.

## Remaining boundary

Этот verdict не закрывает parent TB-001. Он не является backtest, paper
trading или доказательством доходности. Все 12 parent tasks остаются open.
Следующий срез — исторический replay реальных Telegram-сообщений без сети и
без биржевых заявок.
