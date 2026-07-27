# TB-001 MVP Slice 02 — review evidence

Дата: 27.07.2026
Stage: `OFFLINE_SIMULATION`
Статус: `OFFLINE GATES PASS — OWNER MERGE GATE PENDING`
Draft PR: `#2 feat: add historical Telegram replay slice`

## Проверенный baseline

- repository: `ogstonerw/Vibe_coding_shit`;
- branch: `feature/offline-mvp-v0.21`;
- исходный HEAD: `7fb4a2f3818ce7d8311b9da9bc718bfbb95b640a`;
- рабочее дерево до CI-fix: clean;
- Slice 01, financial policy и торговая логика в рамках CI-fix не менялись.

## Воспроизведение GitHub Actions failure

Исходный run `quality-gates`:

- run ID: `30245765558`;
- job ID: `89912356988`;
- `Validate factory configuration`: `PASS`;
- `Run tests`: `FAIL`;
- итог runner: `Ran 138 tests`, `FAILED (errors=8)`.

В логе зафиксированы import errors:

- `httpx` — Bitget/watcher test modules;
- `aiogram` — control-bot test module;
- `dotenv` — environment/integration test modules.

Workflow на исходном HEAD выполнял `setup-python`, self-check и unittest, но
не устанавливал `requirements.txt`.

Причина отдельно воспроизведена на изолированном Python 3.12 без
dependencies: focused discovery для `test_env.py`, `test_control_bot.py` и
`test_bitget_integration.py` завершился с теми же тремя
`ModuleNotFoundError`.

## CI-fix

В `.github/workflows/quality-gates.yml`:

1. добавлен `python3 -m pip install -r requirements.txt` до проверок;
2. только шаг unittest получает явные не-секретные CI-only значения
   `API_ID`, `API_HASH`, `TGBOT_TOKEN`, `TG_OWNER_ID` и `DRY_RUN=true`.

Второй пункт нужен потому, что после установки dependencies старый
`test_full_integration.py` доходит до import-time `Settings()` и без
фиктивной test-конфигурации падает до discovery. `unittest discover` не
исполняет свободные pytest-style network functions; реальные Telegram/Bitget
credentials и сетевые тесты не добавлены.

## GitHub Actions candidate

Исправленный draft PR candidate:

- head: `af1575408eb011bf553c0985be888ea1df480f31`;
- merge ref: `99b4459e4c934ed4fd21fb856faea42c96a0e168`;
- run ID: `30267689130`;
- job ID: `89982242620`;
- runner: Ubuntu 24.04, Python 3.12.13;
- `Install dependencies`: `PASS`;
- `Validate factory configuration`: `PASS`;
- `Run tests`: `Ran 130 tests in 1.074s`, `OK`;
- итог job/run: `SUCCESS`.

## Локальная verification evidence

Среда: Windows PowerShell, Python 3.14.5. Системный Git имеет
`core.autocrlf=true`; проверенные frozen-файлы имеют `i/lf w/crlf`.

```text
python3 scripts/self_check.py
FAIL: 26 byte/hash findings
```

Это Windows worktree EOL mismatch: тот же исходный HEAD прошёл self-check на
Ubuntu GitHub runner. Frozen manifests, governance и PM-DEC artifacts ради
локального запуска не изменялись.

```text
python3 -m unittest discover -s tests -v
Ran 131 tests in 6.523s
FAILED (failures=12, errors=14)
```

После эквивалентных workflow CI-only env:

```text
python3 -m unittest discover -s tests -v
Ran 130 tests in 6.294s
FAILED (failures=12, errors=13)
```

Import errors `httpx`, `aiogram` и `dotenv`, а также import-time Settings
error устранены. Оставшиеся локальные результаты относятся к несовпадению
среды с Ubuntu/Python 3.12: CRLF byte hashes, Windows SQLite file locks,
отсутствующее symlink privilege, POSIX mode assertions и Python 3.14
datetime behavior. Они не исправлялись изменением frozen или Slice 02 кода;
authoritative candidate result должен дать GitHub Actions на Ubuntu.

```text
python3 -m compileall -q tradebot_mvp tests
PASS

ruff 0.16.0 check tradebot_mvp/telegram_import.py tests/test_telegram_import.py
PASS — All checks passed
```

Массовый `ruff --fix` не запускался.

## Независимые reviews

- Test engineer: `PASS`; dependency/Settings import blockers устранены,
  high-confidence findings отсутствуют.
- Code review: `PASS`; blocking correctness/regression findings отсутствуют.
- Security review: `PASS`; blocking findings отсутствуют.
- Risk review: `PASS`; order/capital paths и financial invariants не
  изменены.
- Release verifier: `PASS` только для `OFFLINE_SIMULATION`; verdict не
  авторизует merge или следующий capital stage.

Security reviewer зафиксировал один non-blocking `MEDIUM`: новый CI step
исполняет существующий `requirements.txt`, где большинство direct и
transitive dependencies не закреплены hashes. Отдельный follow-up должен
добавить exact CI lock file и `pip --require-hashes`; это не расширяется в
текущий минимальный CI repair.

Unresolved `BLOCKER/HIGH`: `NONE`.

## Acceptance и safety boundary

- `MVP-02-AC-001…007`: реализация Slice 02 уже присутствует на исходном HEAD;
- CI-fix не меняет parser, sizing, journal, replay или execution semantics;
- реальные exports, channel IDs, secrets и message text не добавлены;
- Telegram API, Bitget API и exchange submission не вызываются;
- paper/live trading, fills и реальные деньги остаются `BLOCKED`.

## Final verification

| Gate | Verdict |
|---|---|
| GitHub Actions candidate | PASS |
| Test engineer | PASS |
| Code review | PASS |
| Security review | PASS — one non-blocking MEDIUM follow-up |
| Risk review | PASS |
| Release verifier | PASS — OFFLINE_SIMULATION only |

Merge и любой переход к paper/live/real-capital stage не авторизованы.
