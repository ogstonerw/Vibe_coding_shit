# TB-001 implementation plan

## Current implementation slice

Разработка начинается не со всего TB-001, а с отдельного
`mvp-slice-01/`: offline signal-to-intent без Telegram/Bitget networking,
exchange fills и paper/live claims. Этот срез проверяет parser, первую
risk-leg, simulated intent, SQLite idempotency и replay. Полные milestones
ниже остаются roadmap и не считаются закрытыми результатом MVP Slice 01.

## Architecture

Начать с модульного монолита: `telegram_ingest`, `signal_parser`, `risk`, `execution`, `bitget_adapter`, `portfolio`, `journal`, `notifications`, `replay` и `app`. Между модулями — типизированные команды/события; SQLite допустим для первого однопроцессного этапа, но order journal и idempotency должны быть транзакционными.

Order-critical путь не использует LLM. Python удобен для Telegram/research-контура; если execution core будет вынесен в Go, контракт событий и decimal semantics сначала фиксируются общими fixtures.

## Milestones

1. Контракты, конфигурация и fixtures.
2. Telegram archive reader и deterministic parser.
3. Risk engine с property tests.
4. Durable journal, state machines и reconciliation.
5. Bitget fake adapter и жесткая DRY_RUN boundary.
6. Replay/backtest с реалистичными издержками.
7. Приватный Telegram control plane и статистика.
8. Paper trading и эксплуатационные runbooks.

## Verification commands

Пока код бота не создан, обязательны фабричные проверки:

```bash
python3 scripts/self_check.py
python3 -m unittest discover -s tests -v
```

При создании реализации агент обязан добавить в этот раздел точные команды formatter, linter, type checker, unit, integration, replay и backtest для выбранного стека.

## Rollback

Каждый milestone поставляется отдельно. Любая ошибка execution/risk отключает создание новых intents, сохраняет журнал и переводит систему в `HALTED` или `RECONCILING`. Откат схемы данных допускается только через проверенную обратимую миграцию или восстановление из тестовой копии.
