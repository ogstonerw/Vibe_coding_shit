# Handoff в новый диалог — практический MVP фабрики торговых ботов

Дата состояния: 24.07.2026  
Release candidate: `tradebot-agent-factory-v0.21.zip`

## Главное изменение

Проект возвращён от преждевременного trust/security-контура к практической
разработке. Первый работающий вертикальный срез TB-001 реализован:

`Telegram-like JSONL → strict parser → first-leg risk → simulated LIMIT
intent → SQLite journal → replay`.

Это только `OFFLINE_SIMULATION`. Реальные Telegram/Bitget API, exchange
orders, fills, полноценный backtest, paper trading, live и real capital
отсутствуют.

## Что работает

- BTCUSDT LONG/SHORT на строгой RU/EN fixture grammar;
- одна явная entry и один окончательный stop;
- `стоп под/над` отклоняется как `STOP_PROFILE_UNRESOLVED`;
- risk из текста сигнала игнорируется;
- channel-bound allocation `15% scalping / 85% intraday`;
- только первая risk-leg `1.5%` от channel bucket;
- Decimal tick/step/risk/margin sizing;
- максимум 5 journal-local active setup;
- одна simulated LIMIT intent;
- exact duplicate, identity conflict, rollback и config-bound replay;
- SQLite journal без raw channel ID/message text, mode `0600`;
- deterministic CLI и bounded input/config parsing;
- сетевой/exchange submission path отсутствует.

## Проверки

- focused MVP: `29/29 PASS`;
- full repository: `105/105 PASS`;
- self-check: `PASS`;
- compileall: `PASS`;
- test engineer: `PASS`;
- code/input/risk reviews: `PASS`;
- fresh institutional/quant/execution evidence reviews: `PASS`;
- unresolved `MEDIUM+`: `NONE`.

Подробности:
`specs/bitget-btc-telegram-v1/mvp-slice-01/review.md`.

## Старые freeze-наборы

Frozen parent core v11 и frozen PM-DEC-007 hybrid addendum v1 не изменены.
Их завершённые reviews не повторять при совпадении:

- `docs/FROZEN_CORE_V11.sha256` — `10/10`;
- `docs/FROZEN_PM_DEC_007_HYBRID_V1.sha256` — `9/9`.

`PM-DEC-007`, hardware keys и криптографические подписи сохранены как будущая
работа перед реальным капиталом, но не являются зависимостями offline,
historical replay или live-stream paper этапов.

## Что остаётся открытым

- все 12 parent tasks TB-001;
- импорт реальной истории двух Telegram-каналов;
- edits/replies/deletes и event-time replay;
- market-data timeline;
- вторая risk-leg, ranges/DCA;
- stop-offset profile;
- fills, fees, funding, slippage, TP, breakeven и time stop;
- Telegram UI;
- Bitget adapter и reconciliation;
- paper/live evidence и любые реальные средства.

## Следующий шаг

Slice 02: принять локальную выгрузку реальных сообщений Telegram и привести её
к текущему JSONL envelope. Реализовать historical replay с edits/replies и
строгим event-time порядком. Не подключать сеть или Bitget и не менять
финансовые лимиты.

Перед продолжением проверить новый MVP manifest. Если hashes совпадают, не
повторять старые reviews и не возвращаться к `PM-DEC-007`.
