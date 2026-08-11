# Product UX Architecture — Bot Farm

Статус: **OWNER DIRECTION ACCEPTED — DECISIONS 1–7 RECORDED**

Область: repository audit, product map и черновая Information Architecture

Не является: реализацией торгового контура, разрешением на Paper/Live или
заменой действующих governance-файлов

## 1. Результат аудита

Текущий подтверждённый продукт — не действующая торговая ферма, а строго
ограниченный offline-контур TB-001. Он принимает локальные данные,
детерминированно формирует симулированный intent и хранит evidence. Slice 02
добавляет импорт Telegram Desktop JSON и исторический replay через тот же
Slice 01 pipeline.

Новый `apps/bot-farm-ui` — отдельный визуальный прототип на
React/TypeScript/Vite. Он читает только типизированный mock snapshot, не имеет
backend API и не обращается к Telegram, Bitget, SQLite или реальному капиталу.
Это хорошая проверка визуальной метафоры, но не operational console и не
источник истины.

### 1.1 Иерархия доказательств

При конфликте интерфейс обязан следовать этому порядку:

1. `governance/*.toml`, acceptance/spec и Owner gates;
2. проверяемое состояние `tradebot_mvp`, journal/replay и release evidence;
3. архитектурные и operating-model документы;
4. typed API snapshot будущего backend;
5. UI mock и декоративные состояния.

Mock, анимация, персонаж или legacy runtime никогда не могут повысить stage,
открыть gate или подтвердить финансовое состояние.

### 1.2 Что реально существует

| Область | Подтверждённое состояние |
|---|---|
| Offline core | Строгий JSONL/Telegram export input, parser, first risk leg, simulated LIMIT intent, SQLite journal и deterministic replay. |
| Historical Telegram replay | Локальный Telegram Desktop JSON, bounded normalization, глобальная event-time сортировка, dedup/conflict handling и atomic batch. |
| Тестовый контур | Python self-check/tests в Ubuntu CI; frontend typecheck, Vitest и production build локально. |
| Risk/governance | Limit-only policy, fail-closed проверки, owner-only gates; `live.enabled = false`. |
| Frontend | Расширяемая Farm View со зданиями, NPC-ботами и навигацией Owner; Bot Detail, Test Lab, Risk Center, Releases, Reviews и utility pages на typed mock repository. |
| UI data boundary | `BotFarmRepository` позволяет позже заменить mock адаптером API без переноса торговой логики в React. |

### 1.3 Что присутствует, но не является проверенным продуктом

За пределами `tradebot_mvp` есть legacy-код с Telethon, Aiogram и Bitget,
включая сетевые и потенциально реальные execution paths при отключении
`DRY_RUN`. Он не интегрирован с новым frontend, не является доверенным API для
Slice 02 и не получает новую authority от этого документа.

До отдельного security/authority проекта UI не должен:

- импортировать состояние из legacy-скриптов как факт;
- показывать action, способный выключить `DRY_RUN` или обойти gate;
- отправлять Telegram/Bitget-команды;
- трактовать наличие API-ключа как готовность к торговле.

### 1.4 Что отсутствует

- доверенный read-only application API и версионированный UI snapshot;
- runtime authentication, roles/permissions и workspace isolation;
- Operations View для 20–100+ ботов;
- global search, command palette, favorites, recent и breadcrumbs;
- полноценные Builder, Backtest/Replay reports, alerts/incidents и monitoring;
- paper fills, fees, funding, slippage, TP/BE/time-stop и reconciliation;
- разрешённые Paper, Limited Live или Live execution paths;
- authoritative PnL, drawdown, VaR, exposure, positions, orders и fills.

## 2. Карта продукта

### CURRENT PRODUCT

- TB-001 Offline Signal-to-Intent.
- Historical Telegram Replay Slice 02.
- Governance, evidence, review и release gates.
- Bot Farm visual prototype с market-зданиями, шестью NPC-агентами и read-only mock pages.

### PLANNED PRODUCT

- Полный Telegram signal contract и две risk legs / три LIMIT entry orders.
- Durable position/order state, paper fills и execution lifecycle.
- Live-stream paper, reconciliation, kill/restart и richer replay/backtest.
- Private owner interface, secret handling и paper-readiness verification.
- Portfolio/risk books и evidence-driven bot lifecycle.

Пункты этой группы — target baseline из roadmap/spec/concept, а не обещание
готовой функции.

### DESIGN OPPORTUNITIES

- Разделить эмоциональную Farm View и плотную Operations View.
- Сделать lifecycle, gate, run state, health, connectivity и risk разными
  измерениями вместо одного неоднозначного «статуса».
- Дать bot-context navigation и единый evidence trail от теста до release.
- Проектировать alerts/incidents/risk для решения за секунды.
- Вынести mock в явно маркированный Demo workspace и подключить typed,
  read-only API snapshot, когда backend contract будет утверждён.

### FUTURE

- 20–50 модулей через registry/plugin slots.
- 100+ ботов, virtualization, saved views и bulk operations с authorization.
- Несколько workspaces, portfolios, рынков, бирж и bot engines.
- AI agents как отдельные субъекты с ограниченной authority и audit trail.
- Teams/permissions, marketplace и расширяемая design system.

## 3. Черновая Information Architecture

```text
PRODUCT
├─ Farm
│  ├─ Command Center / Dashboard
│  ├─ Farm View
│  └─ Activity / News
├─ Bots
│  ├─ Bot Park: Farm | Operations
│  ├─ Bot Detail
│  ├─ Create Bot
│  ├─ Builder
│  └─ Versions
├─ Research
│  ├─ Strategies
│  ├─ Strategy Journal
│  └─ Marketplace
├─ Testing
│  ├─ Test Lab
│  ├─ Backtests / Report
│  └─ Replay / Report
├─ Trading
│  ├─ Paper Trading
│  ├─ Live Gate
│  ├─ Live Monitoring
│  ├─ Trades
│  ├─ Positions
│  └─ Orders
├─ Risk & Safety
│  ├─ Risk Center
│  ├─ Portfolio Risk
│  ├─ Bot Risk
│  ├─ Alerts
│  └─ Incidents
├─ Delivery
│  ├─ Agent Reviews
│  ├─ Releases / Release Detail
│  └─ Build Archive
├─ Operations
│  ├─ Monitoring
│  ├─ Logs / Events
│  └─ Notifications
└─ Platform
   ├─ Integrations
   ├─ Exchange Connections
   ├─ Secrets / API Keys
   ├─ Documentation
   ├─ Settings
   ├─ User / Profile
   ├─ Permissions / Teams
   └─ Future Modules
```

### 3.1 Навигационные контексты

| Контекст | Назначение | Масштабирование |
|---|---|---|
| Global shell | Workspace switcher, search, alerts, command palette, profile. | Стабилен при добавлении модулей. |
| Domain navigation | Сворачиваемые группы Farm/Bots/Testing/Risk и т.д. | Scroll, registry, permission visibility, plugin slots. |
| Module navigation | Локальные views/tabs конкретного раздела. | Не раздувает global menu. |
| Bot context | Overview, Build, Tests, Replay, Risk, Runs, Releases, Logs. | Один устойчивый workspace для любого bot engine. |
| Portfolio context | Portfolio, venue, market, strategy и saved view. | Позволяет работать с 100+ сущностями. |
| Quick context | Favorites, Recent, breadcrumbs, Ctrl/Cmd+K. | Ускоряет повторные действия без дублирования меню. |

На малом окне domain navigation сворачивается в drawer; bot context остаётся
доступен как горизонтальный/выпадающий switcher. Критические gate/risk badges
не скрываются только из-за ширины.

## 4. Bot Park: два равноправных режима

### Farm View

Эмоциональная карта мира для ориентации, обучения и ежедневного обзора.
Участок, персонаж и окружение отражают проверенное состояние, но всегда
сопровождаются текстовым badge. Декор не кодирует единственный критический
сигнал.

Здание — отдельная market/module-зона с вместимостью и связями на карте. Каждый
NPC представляет ровно одного `BotAgent`; `agentKind` различает trading,
replay, risk и review-агентов. Персонаж Owner ходит между зданиями стрелками,
но его движение только меняет фокус и никогда не запускает side effect.

### Operations View

Основной профессиональный режим при 20–100+ ботах: виртуализированный список
или таблица, сортировка, grouping, pin columns, density modes, saved filters и
permission-aware bulk actions. Базовые фильтры: portfolio, market, exchange,
strategy, lifecycle, run state, health, risk, release, owner и data freshness.

Переключение Farm/Operations сохраняет один query/filter context. Это два
представления одной выборки, а не две разные модели данных.

## 5. Предлагаемый lifecycle

Линейная шкала недостаточна: development/release stage нельзя смешивать с
runtime health, connectivity, risk и gate verdict. Составное состояние принято
Owner как долгосрочный source-of-truth contract:

- `lifecycle_stage` — где находится версия бота;
- `gate_verdicts` — какие независимые проверки пройдены;
- `run_state` — idle/running/paused/halted/reconciling;
- `health_state` — healthy/degraded/critical/unknown;
- `risk_state` — normal/watch/de-risk/protect/emergency;
- `connectivity_state` — offline/connected/stale/disconnected;
- `evidence_freshness` — время и источник snapshot.

### 5.1 Release lane

```text
IDEA
  → DEVELOPMENT / SANDBOX
  → OFFLINE_TEST
  → HISTORICAL_REPLAY
  → INDEPENDENT_REVIEW
  → OWNER_RELEASE_GATE
  → RELEASED_OFFLINE
```

TB-001 сейчас находится у `OWNER_RELEASE_GATE`: offline evidence и review
пройдены, merge/release решение Owner ожидается. Это не открывает Paper или
Live.

### 5.2 Capital lane (только будущая архитектура)

```text
PAPER_CANDIDATE
  → PAPER
  → LIVE_STREAM_PAPER
  → PILOT_CANDIDATE
  → OWNER_LIVE_GATE
  → LIMITED_LIVE
  → LIVE_CANDIDATE
  → OWNER_LIVE_GATE
  → LIVE
  → MONITORING
```

Каждый переход требует отдельного evidence bundle и explicit authority.
Release gate, Paper gate и Live gate не взаимозаменяемы и не наследуются
автоматически.

Side states: `PAUSED`, `HALTED`, `RECONCILING`, `INCIDENT`, `ROLLBACK`,
`RETIRED`. Для каждого будущая state spec обязана определить icon, label,
цвет+форму, допустимые действия, blockers, actor/authority, audit event и
recovery transition. Анимация — только дополнительный сигнал.

## 6. Основные UX flows

1. **Утренний обзор:** открыть Operations View → увидеть stale/critical/risk
   first → отфильтровать проблемные → открыть evidence/incident.
2. **Создать бота:** Create Bot → mandate/template → Builder → local validation
   → offline test; никаких capital stages по умолчанию.
3. **Разобрать тест:** Test Lab → failed suite → failing assertion/input →
   linked version/change → rerun → evidence.
4. **Historical replay:** выбрать version + bounded local dataset → preflight →
   run → deterministic report → compare → attach to release evidence.
5. **Выпустить offline-версию:** evidence completeness → independent reviews →
   Owner Release Gate → immutable release record.
6. **Остановить проблему:** alert → bot/portfolio context → verify authority →
   pause/halt/kill action → confirmation → audit event → reconciliation.
7. **Разобрать инцидент:** timeline → affected bots/orders/data → containment →
   reconciliation → postmortem → rollback/release link.
8. **Paper → Live:** пока только будущий flow; должен быть невозможен без
   отдельного Owner Live Gate, freshness checks и reconciliation proof.

## 7. Каталог основных экранов

Это coverage-каталог этапа IA, не подробные screen specs. Поля layouts,
empty/loading/error/success/warning/critical, context menu, tooltips, shortcuts,
motion и small-window behavior проектируются после решения Owner.

| # | Экран | Состояние сейчас | Главная задача |
|---:|---|---|---|
| 01 | Farm / Dashboard | Mock prototype | За секунды понять общее состояние фермы и blockers. |
| 02 | Bot Park | Farm prototype; Operations отсутствует | Найти, сравнить и открыть бота. |
| 03 | Bot Detail | Mock prototype | Увидеть identity, stage, evidence, risk и разрешённые действия. |
| 04 | Create Bot | Отсутствует | Создать draft из mandate/template без authority. |
| 05 | Builder | Отсутствует | Настроить contracts/strategy/version с validation. |
| 06 | Test Lab | Mock prototype | Запускать и разбирать локальные suites. |
| 07 | Backtests | Отсутствует; planned | Управлять datasets/runs/comparisons. |
| 08 | Backtest Report | Отсутствует; planned | Проверять результаты, costs, bias и evidence. |
| 09 | Replay | Core CLI существует; UI отсутствует | Запустить bounded deterministic replay. |
| 10 | Replay Report | Core summary существует; UI отсутствует | Изучить decisions, skips/conflicts и reproducibility. |
| 11 | Paper Trading | BLOCKED / future | Наблюдать paper execution после отдельного gate. |
| 12 | Live Gate | LOCKED / future | Проверить evidence и получить explicit Owner decision. |
| 13 | Live Monitoring | LOCKED / future | Контролировать live health, risk и containment. |
| 14 | Risk Center | Read-only mock prototype | Увидеть policy state и приоритетные risk exceptions. |
| 15 | Portfolio Risk | Отсутствует; future | Exposure, concentration, correlation и limits. |
| 16 | Bot Risk | Частично в Bot Detail mock | Разобрать risk budget и breaches конкретного бота. |
| 17 | Trades | Нет authoritative data | Анализировать executed trades и attribution. |
| 18 | Positions | Нет authoritative data | Видеть positions, exposure и reconciliation state. |
| 19 | Orders | Нет authoritative data | Проверять lifecycle, rejects и pending uncertainty. |
| 20 | Alerts | Отсутствует | Приоритизировать actionable abnormal conditions. |
| 21 | Incidents | Отсутствует | Containment, timeline, ownership и resolution. |
| 22 | Agent Reviews | Mock prototype | Сопоставить verdict с immutable evidence. |
| 23 | Releases | Mock prototype | Видеть candidates, gates и release history. |
| 24 | Release Detail | Отсутствует | Проверить manifest, reviews, artifacts и authority. |
| 25 | Versions | Частично build utility mock | Compare, promote, rollback и trace changes. |
| 26 | Logs | Events utility mock | Искать structured events с bot/run correlation. |
| 27 | Strategy Journal | Отсутствует; planned | Фиксировать hypothesis, decision и outcome. |
| 28 | Marketplace | Future | Находить templates/modules без скрытой authority. |
| 29 | Integrations | Отсутствует | Управлять typed adapters и их health/capabilities. |
| 30 | Exchange Connections | BLOCKED / future | Connectivity, scopes, freshness; не «включить Live». |
| 31 | Secrets / API Keys | BLOCKED / future | Безопасное credential lifecycle без показа secret value. |
| 32 | Notifications | Mock utility | Настроить delivery, severity и acknowledgement. |
| 33 | Documentation | Prototype | Контекстная документация, contracts и runbooks. |
| 34 | Settings | Отсутствует | Workspace/UI settings; risk authority отдельно. |
| 35 | User / Profile | Статичный Owner card | Identity, preferences и security context. |
| 36 | Permissions / Teams | Future | Least privilege, approvals и separation of duties. |
| 37 | Future Modules | Концепт | Registry/plugin slots без переделки shell. |

## 8. Технические ограничения для будущей реализации

- React получает только версионированный, provenance-bearing snapshot; UI не
  вычисляет gate verdict и не хранит торговую authority.
- Все financial values несут `as_of`, source, currency/unit и freshness.
- Demo/mock workspace визуально и семантически не похож на Live.
- Commands используют отдельный command contract, idempotency, confirmation,
  actor/permission, audit и fail-closed response.
- Таблицы готовы к virtualization; фильтры/saved views живут в URL/query model.
- Critical state кодируется текстом, формой/icon и цветом; reduced motion
  обязателен.
- Farm animation не влияет на state machine, не блокирует interaction и не
  запускает side effects.
- Пока API/authority contract отсутствует, frontend остаётся read-only mock.

## 9. Предлагаемый порядок проектирования

1. **Data/authority foundation:** UI snapshot, state taxonomy, provenance,
   permissions и command safety contract.
2. **Design foundation + shell:** tokens, typography, status language,
   responsive global/domain/bot navigation и command palette model.
3. **Bot Park:** одна query model, Farm View и Operations View.
4. **Bot Detail:** lifecycle, gates, evidence, versions, risk и audit trail.
5. **Test Lab + Replay + reports:** самый близкий к текущему core вертикальный
   slice.
6. **Risk + Alerts + Incidents:** decision-first operations workflows.
7. **Reviews + Releases + Versions:** сквозной evidence/release flow.
8. **Trading screens:** только после реализации и допуска Paper domain;
   Live — отдельный будущий Owner-approved проект.
9. **Platform/Future modules:** integrations, teams, marketplace и registry.

## 10. Граница текущей итерации

Направление Farm View подтверждено Owner и реализуется безопасными read-only
slices. Backend-интеграция и торговые изменения не начинаются. Paper/Live
trading, Telegram API, Bitget API, fills и реальные деньги остаются **BLOCKED**.
