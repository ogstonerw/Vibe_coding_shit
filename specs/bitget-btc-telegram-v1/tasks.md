# TB-001 tasks

Текущая реализация ограничена задачами
[`mvp-slice-01/tasks.md`](mvp-slice-01/tasks.md). Чекбоксы полного TB-001 ниже
не закрываются автоматически результатом offline-среза.

- [ ] `TB-001-T01` Зафиксировать типизированные контракты SignalCandidate, Setup, OrderIntent, Fill и PortfolioSnapshot — AC-001, AC-004.
- [ ] `TB-001-T02` Импортировать историю двух Telegram-каналов с edits/replies/deletes и session-only auth — AC-004, AC-010.
- [ ] `TB-001-T03` Реализовать deterministic parser и corpus fixtures — AC-001, AC-003.
- [ ] `TB-001-T04` Реализовать decimal risk engine, две risk-legs и до трех limit orders — AC-002, AC-011.
- [ ] `TB-001-T05` Реализовать durable journal, idempotency и state transitions — AC-004, AC-008.
- [ ] `TB-001-T06` Реализовать Bitget adapter interface, fake и DRY_RUN network barrier — AC-005, AC-006.
- [ ] `TB-001-T07` Реализовать partial fills, TP ladder, fee-aware breakeven и time stop — AC-007.
- [ ] `TB-001-T08` Реализовать reconciliation, kill switch и restart recovery — AC-005, AC-008.
- [ ] `TB-001-T09` Реализовать replay/backtest без future leakage и с издержками — AC-010.
- [ ] `TB-001-T10` Реализовать приватные Telegram notifications, help и последние 10 сделок с пагинацией — AC-009.
- [ ] `TB-001-T11` Добавить secret scanning, redaction и deployment config validation — AC-012.
- [ ] `TB-001-T12` Провести paper-stage readiness review; live activation остается отдельной задачей владельца — все AC.
