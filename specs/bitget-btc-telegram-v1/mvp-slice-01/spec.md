# TB-001 MVP Slice 01 — Offline Signal-to-Intent

Status: IMPLEMENTATION_SCOPE  
Parent work item: `TB-001`  
Target stage: `OFFLINE_SIMULATION`  
Real Telegram, Bitget, paper trading and live trading: not included

## 1. Purpose

Этот срез должен доказать минимальную работоспособность фабрики на одном
сквозном сценарии:

`JSONL Telegram-like event → deterministic parser → validation → first-leg
risk sizing → simulated LIMIT intent → SQLite journal → deterministic replay`.

Срез не является полноценным paper trading, не обращается к Telegram или
Bitget и не создаёт торговых полномочий. `PM-DEC-007` и криптографический
trust-контур не являются зависимостями этого среза.

## 2. Input contract

CLI принимает UTF-8 JSONL. Каждая строка является закрытым объектом:

```json
{
  "source": "scalping",
  "channel_id": "-1000000000001",
  "message_id": 101,
  "revision": 0,
  "timestamp": "2026-07-24T12:00:00Z",
  "text": "BTCUSDT LONG\nENTRY 94700\nSTOP 92900\nRISK 0.5%"
}
```

Разрешённые `source`: `scalping`, `intraday`. `channel_id` — непустая
Unicode-scalar строка длиной не более 128 символов и обязан точно совпадать с
test allowlist для выбранного source. `message_id` и `revision` —
неотрицательные целые числа, не превышающие `9223372036854775807`;
`timestamp` — UTC в форме `YYYY-MM-DDTHH:MM:SSZ`; `text` — непустая
Unicode-scalar строка длиной не более 20 000 символов. Неизвестные,
отсутствующие или выходящие за границы поля дают детерминированный отказ.

Один replay-файл ограничен 8 MiB, 10 000 строками и 64 KiB на строку.
Preflight проверяет byte/record/line limits и UTF-8 всего файла до обработки
первой строки. Input path обязан быть regular non-symlink file. Превышение
или небезопасный target даёт `INPUT_LIMIT_EXCEEDED` без частичного replay.

JSON decode и closed-envelope validation выполняются до journal transaction.
Если невозможно получить полную event identity, CLI возвращает
`disposition=rejected`, `reason=INVALID_EVENT_ENVELOPE`, `journaled=false` и
не создаёт строк: неполное событие нельзя безопасно дедуплицировать. Этот
outcome увеличивает run-counter `rejected`. После успешной envelope validation
применяется транзакционная семантика раздела 7.

## 3. Strict text grammar

Первая версия поддерживает только один инструмент, одно направление, одну
цену входа и один окончательный stop:

- символ: `BTCUSDT` или `BTC`;
- направление: `LONG` / `ЛОНГ` либо `SHORT` / `ШОРТ`;
- вход: отдельная строка `ENTRY <decimal>` или `ВХОД <decimal>`;
- stop: отдельная строка `STOP <decimal>` или `СТОП <decimal>`;
- строки с `RISK` / `РИСК`, включая `0.5%`, `1%`, `1/2` и `1/3`,
  игнорируются и не меняют локальный риск.

Диапазон входа, несколько входов, цели, re-entry и свободная грамматика пока
не поддерживаются. Формы `стоп под X`, `стоп над X`, `stop under X` и
`stop above X` отклоняются с `STOP_PROFILE_UNRESOLVED`: общий алгоритм
technical offset ещё не утверждён.

## 4. Test-only configuration

Все числовые значения передаются в отдельном versioned TOML и не являются
реальными торговыми настройками:

- `mode` обязан быть `OFFLINE_SIMULATION`;
- `account_equity`, `quantity_step`, `price_tick` и
  `adverse_cost_per_unit` задаются decimal-строками;
- `scalping_channel_id` и `intraday_channel_id` задают два различных точных
  test allowlist ID; cross-mapping и неизвестный ID отклоняются до sizing;
- `leverage` задаётся явно и обязан находиться в owner-locked диапазоне
  `10..25`;
- allocation фиксируется политикой: `0.15` для `scalping`, `0.85` для
  `intraday`;
- в срезе разрешена только первая risk-leg `0.015`;
- максимум активных setup — `5`.

Любое неизвестное поле, несовпадение policy-bound значений или невалидное
число блокирует запуск. Реальные tick/lot/fee параметры Bitget не заявляются:
конфигурация имеет маркировку `TEST_FIXTURE_ONLY`.

TOML ограничен 64 KiB и плоскими scalar-полями без tables, arrays или inline
objects; reader читает не более 64 KiB + 1 byte из regular non-symlink file.
Parse/decode/complexity failures детерминированно дают
`CONFIG_READ_OR_PARSE_FAILED`.

Decimal-строки не содержат exponent или знак `+`, имеют не более 18 цифр до
точки и 8 после неё. `account_equity`, `quantity_step` и `price_tick` строго
положительны; `adverse_cost_per_unit` неотрицателен. Parser применяет те же
ограничения к entry/stop.

После closed parsing значения конфигурации переводятся в normalized object:
decimal-поля представлены canonical decimal text, ключи фиксированы схемой.
`config_fingerprint` равен SHA-256 от compact JSON этого объекта с
лексикографической сортировкой ключей. Новая база привязывается к одному
fingerprint; запуск существующей базы с другим fingerprint даёт
`CONFIG_FINGERPRINT_MISMATCH` до обработки input и не меняет базу.

## 5. Validation and sizing

Допускается только `BTCUSDT`. Для `LONG` требуется `stop < entry`, для
`SHORT` — `stop > entry`. Entry и stop обязаны быть точными кратными
`price_tick`; срез не округляет цену и отклоняет off-tick значение с
`PRICE_OFF_TICK`.

Расчёты выполняются только через `Decimal` в локальном context с precision
`50` и `ROUND_FLOOR`; ambient process context не используется. Чтобы
повторяющееся деление не могло увеличить quantity около step-boundary,
алгоритм сначала считает целое число quantity steps:

```text
bucket = account_equity * channel_allocation
risk_budget = bucket * 0.015
unit_loss = abs(entry - stop) + adverse_cost_per_unit
risk_steps = floor(risk_budget / (unit_loss * quantity_step))
margin_steps = floor((bucket * leverage) / (entry * quantity_step))
quantity = min(risk_steps, margin_steps) * quantity_step
```

После округления повторно проверяются:

```text
quantity * unit_loss <= risk_budget
quantity * entry <= bucket * leverage
```

Нулевое количество, не-finite/неположительные числа и нарушение любой
границы дают отказ без intent. Leverage не может увеличить количество,
полученное из risk sizing.

## 6. Output contract

На валидное новое событие создаётся ровно один `SimulatedLimitIntent`:

- `symbol = BTCUSDT`;
- `order_type = LIMIT`;
- `stage = OFFLINE_SIMULATION`;
- `simulated = true`;
- quantity, entry, stop и рассчитанный риск представлены decimal-строками;
- идентификаторы setup и intent детерминированно выводятся из event identity,
  нормализованного сигнала и `config_fingerprint`.

В проекте отсутствуют exchange adapter, HTTP client и функция отправки
ордера. Любая формулировка результата как `paper`, `live`, `submitted`,
`acknowledged` или `filled` запрещена.

Default output не содержит исходный `channel_id` или текст сообщения.
Публичный event reference является SHA-256 pseudonym от локальной identity.

## 7. Journal and idempotency

На каждое envelope-valid событие открывается одна SQLite-транзакция
`BEGIN IMMEDIATE`.

Транзакция атомарно сохраняет:

1. pseudonymous channel key, message/revision/timestamp и hash payload;
2. принятое или отклонённое решение с reason code;
3. setup и один simulated intent для принятого события;
4. упорядоченные journal events.

Сырой `channel_id`, исходный текст и полный payload в SQLite не сохраняются.

Event identity: `(source, channel_id, message_id, revision)`.

- Первая обработка возвращает envelope с `disposition=accepted|rejected` и
  сохраняет решение.
- Точная повторная доставка возвращает новый envelope
  `disposition=duplicate`, включает `original_disposition` и сохранённый
  reason code, но не создаёт ни одной строки.
- Та же identity с другим payload даёт `EVENT_IDENTITY_CONFLICT`.
- Conflict возвращает `disposition=conflict` и не создаёт ни одной строки.
- Шестой активный setup даёт `MAX_ACTIVE_SETUPS_REACHED` до создания intent.
- Ошибка записи откатывает всё решение.

Активность в этом срезе является только локальным journal-состоянием:
каждый принятый setup получает `local_status=ACTIVE` и остаётся активным,
поскольку lifecycle/close ещё не реализован. Venue orders, fills и positions
не существуют и не участвуют в подсчёте.

SQLite настраивается с `foreign_keys=ON`, `journal_mode=WAL` и
`synchronous=FULL`. Денежные значения сохраняются как canonical decimal text,
не как `REAL`. Database target не может быть symlink или non-regular file;
основной файл и существующие WAL/SHM sidecars получают owner-only mode `0600`.

## 8. Replay and CLI

Команда:

```bash
python3 -m tradebot_mvp replay \
  --input tests/fixtures/mvp_signals.jsonl \
  --config config/mvp-offline-demo.toml \
  --db /tmp/tradebot-mvp.sqlite3
```

CLI обрабатывает строки строго по порядку и печатает один JSON-объект с
`accepted`, `rejected`, `duplicates`, `conflicts`, `setups`, `intents` и
ordered `outcomes`. `accepted` считает впервые сохранённые accepted decisions.
`rejected` считает все новые rejected outcomes, включая
`INVALID_EVENT_ENVELOPE` с `journaled=false`; он не считает exact replay.
`duplicates` и `conflicts` считают соответствующие несохраняемые envelopes.
JSON формируется с сортировкой ключей.

Два запуска одного input/config в две новые базы обязаны дать byte-identical
stdout. При envelope-valid input повтор в ту же базу обязан дать только
duplicate outcomes без новых setup/intents. Нежурналируемый
`INVALID_EVENT_ENVELOPE` при каждом запуске снова даёт новый rejected outcome;
mixed input поэтому содержит recurring rejection плюс duplicates валидных
строк. Запуск той же базы с другим `config_fingerprint` обязан завершиться до
replay с `CONFIG_FINGERPRINT_MISMATCH`.

## 9. Explicitly deferred

- Telethon session, реальные channel IDs, edits/replies/deletes;
- Bitget API, credentials, network submission и reconciliation;
- вторая risk-leg, диапазоны, DCA и три заявки;
- fills, TP ladder, breakeven, time stop и re-entry;
- Telegram UI и уведомления;
- market-data replay, funding, slippage model и полноценный backtest;
- paper-stage duration, limited live, live и real capital;
- `PM-DEC-007`, hardware keys, криптографические подписи и trust registry.

Эти пункты не блокируют `OFFLINE_SIMULATION`, но ни один из них не может
считаться реализованным по результатам этого среза.
