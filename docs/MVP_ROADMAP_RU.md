# Практический MVP фабрики торговых ботов

Текущий статус: этап 1 `Offline signal-to-intent` реализован и прошёл
независимые проверки. Этап 2 `Исторический replay` реализован в draft PR #2,
но ожидает зелёный CI, независимый review и release gate.

## Текущая цель

Не строить универсальную платформу и не проектировать защиту реального
капитала до появления работающего прототипа. Сначала фабрика должна выпустить
один проверяемый вертикальный срез TB-001.

## Очерёдность

1. **Offline signal-to-intent.** Строгая fixture-грамматика, parser, первая
   risk-leg, simulated LIMIT intent, SQLite idempotency и replay.
2. **Исторический replay — IMPLEMENTED, GATE PENDING.** Локальные Telegram
   Desktop exports двух configured channels, связи сообщений и строгий
   event-time replay. Market-data timeline остаётся отдельной будущей работой.
3. **Paper execution.** Локальная модель заявок/fills, комиссии, funding,
   slippage, TP, breakeven и time stop — без биржевых ордеров.
4. **Live-stream paper.** Telethon reader и рыночные данные Bitget, но
   execution остаётся локальным.
5. **Ограниченный тестовый exchange-контур.** Только после отдельного решения
   владельца и подтверждённой защитной семантики.
6. **Реальный капитал.** Отдельный будущий проект допуска.

## Что не блокирует первые четыре этапа

- `PM-DEC-007`;
- hardware keys и отдельное устройство;
- CBOR/COSE/JCS и криптографические подписи;
- trust registry, recovery ceremony и production attestation;
- MOEX и универсальная multi-market архитектура.

Эти темы сохраняются как будущие требования перед реальным капиталом, но
исключены из критического пути MVP.

## Критерий успеха первого среза

Один входной JSONL-файл можно воспроизвести на чистой машине стандартным
Python 3.12. Результат детерминирован; дубликаты не создаются; неверный символ,
stop или конфигурация дают отказ; риск не превышает локальный cap; сетевого
пути и реальных ордеров в коде нет.

## Текущий release gate Slice 02

Slice 02 не переводит проект на следующий capital stage. До завершения
GitHub Actions, test/code/security/risk review и release verification он
остаётся реализованным, но не выпущенным offline-срезом.

Paper/live trading, Telegram API, Bitget API, fills, exchange submission и
реальные деньги остаются `BLOCKED`. Merge draft PR #2 требует отдельного
подтверждения владельца.
