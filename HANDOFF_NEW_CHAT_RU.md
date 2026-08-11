# Handoff в новый диалог — практический MVP фабрики торговых ботов

Дата состояния: 10.08.2026
Release candidate: `tradebot-agent-factory-v0.21.zip`

## Главное изменение

Проект возвращён от преждевременного trust/security-контура к практической
разработке. Первый работающий вертикальный срез TB-001 реализован:

`Telegram-like JSONL → strict parser → first-leg risk → simulated LIMIT
intent → SQLite journal → replay`.

Slice 02 также реализован в ветке `feature/offline-mvp-v0.21` и draft PR #2:

`local Telegram Desktop JSON → bounded normalization → deterministic global
event-time replay → unchanged Slice 01 offline pipeline`.

Статус Slice 02: `IMPLEMENTED`; GitHub Actions, независимые
test/code/security/risk reviews и release verifier прошли для
`OFFLINE_SIMULATION`. Отдельный owner merge gate остаётся открытым.
Исправление `quality-gates` устанавливает `requirements.txt` перед unittest;
реальные credentials в workflow не добавляются.

Это только `OFFLINE_SIMULATION`. Реальные Telegram/Bitget API, exchange
orders, fills, полноценный backtest, paper trading, live и real capital
отсутствуют.

Параллельный read-only Bot Farm prototype теперь строится из расширяемых
market-зданий: каждый NPC связан с конкретным ботом/агентом, а персонаж Owner
ходит между зданиями стрелками только для навигации. Необоснованный readiness
удалён, offline risk без telemetry показывает `NOT_EVALUATED`, Owner
Merge/Pilot/Live разделены. Решения Owner зафиксированы в
`docs/ui/OWNER_DECISIONS.md`; составная state-модель подтверждена Owner
11.08.2026.

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

Результаты Slice 02 и текущего CI-fix:
`specs/bitget-btc-telegram-v1/mvp-slice-02/review.md`.

GitHub Actions: self-check `PASS`, unittest `130/130 PASS`. Release verifier:
`PASS` только для `OFFLINE_SIMULATION`. Merge всё ещё требует отдельного
подтверждения владельца.

Завершённые результаты Slice 01:

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

Сохранить draft PR #2 без merge до отдельного подтверждения владельца.

Для UI продолжать безопасные read-only slices: расширение Farm View и будущий
Operations View. Backend начинать только с versioned read-only API; legacy
execution не подключать.

Не возвращаться к `PM-DEC-007` и не повторять тяжёлое исследование стратегии.
Paper/live trading, Telegram API, Bitget API, fills, exchange submission и
реальные деньги остаются `BLOCKED`.
