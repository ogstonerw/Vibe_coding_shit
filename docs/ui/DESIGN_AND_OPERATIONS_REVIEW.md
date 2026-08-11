# Design and Operations Review

Статус: **OWNER DIRECTION ACCEPTED — DECISIONS 1–7 RECORDED**

Режим: независимые read-only аудиты; торговая логика и gates не изменялись

## 1. Общий вердикт

Текущий frontend — выразительный и безопасно изолированный visual prototype
offline Slice 02. Как console для управления реальными ботами он **BLOCKED**:
нет authoritative API/telemetry, control plane, positions/orders/fills и
допуска капитала.

Объединённая рекомендация экспертов:

- оставить «Ферму ботов» главным эмоциональным миром;
- создать отдельный Operations Canvas для точных данных;
- считать NPC визуальным представлением конкретного `BotAgent`, а здания —
  отдельными market/module-контейнерами;
- дать Bot Park два вида одной выборки: Farm и Operations;
- разделить lifecycle, evidence gates, runtime, health, risk и connectivity;
- ввести provenance/freshness до подключения реальных данных;
- начинать интеграцию только с read-only API; legacy execution оставить в
  карантине;
- Paper/Live и реальные деньги оставить **BLOCKED**.

## 2. Независимая позиция Designer / Game UX Director

### Что сохранять

- Оригинальный характер: деревянный shell, parchment surfaces, свои
  code-native персонажи и разные зоны мира.
- Глобально заметные Owner Pending, Live Locked и Real Capital Locked.
- Хорошую основу accessibility: landmarks, focus, skip link, ARIA и reduced
  motion.
- Repository seam между React и mock data.

### Что нельзя масштабировать как есть

- Literal union из шести ID и монолитный `FarmSnapshot`.
- Плоскую hardcoded-навигацию из пяти пунктов плюс нижний dock.
- Один тип агента без discriminator одновременно для trading, sandbox,
  Risk/Replay/Review-ролей.
- Необоснованные `readiness 96–100%`, `130/130` и `NORMAL` без commit, run ID,
  timestamp, source и freshness.
- Один CSS-файл с большим количеством прямых значений, Unicode/emoji icons и
  произвольными sprite scales/durations как production design system.

### Design foundation

1. **World Canvas** — карта, здания, персонажи, ambience и понятная spatial
   metaphor.
2. **Operations Canvas** — таблицы, reports, charts, alerts и risk numbers без
   декоративной конкуренции.
3. Semantic states `healthy/success/info/processing/warning/high-risk/critical/
   blocked/offline/unknown` кодируются цветом, формой, icon и текстом.
4. Pixel grammar: icons `16×16`, actors `32×40`, props `32/64`, buildings
   `64/96`; только целочисленный scale `2×/3×/4×`.
5. Display font используется для заголовков; body — 14–16 px, metadata — не
   ниже 11–12 px, operational numbers — tabular mono.
6. Motion tokens: press 80 ms, hover/focus 120 ms, panel/tab 180 ms,
   modal/drawer 240–280 ms, ambient 2.4–10 s. Reduced Motion отключает ambience,
   но сохраняет status meaning.
7. Sound только opt-in/muted by default и никогда не является единственным
   каналом критического события.

## 3. Независимая позиция Pro Trader / Bot Operations Expert

### Operational truth

- TB-001: только `OFFLINE_SIMULATION` и simulated intent.
- Slice 02: software `OFFLINE_GATES_PASS / OWNER_MERGE_PENDING`.
- Capital/runtime: `OFFLINE_SIMULATION`, `NOT_DEPLOYED / N/A`.
- Paper, Live, fills, positions, authoritative PnL и real execution отсутствуют.
- Legacy Telethon/Bitget/Aiogram paths не входят в доказанный Slice 02 и не
  должны подключаться к UI без отдельного remediation/security/risk review.

### Требуемые независимые автоматы

1. Software release: `IDEA → SPEC → BUILDING → OFFLINE_RC → OFFLINE_GATES_PASS
   → OWNER_MERGE_PENDING → OFFLINE_RELEASED`.
2. Evidence job: `QUEUED → RUNNING → PASS | FAIL | BLOCKED | CANCELLED`.
3. Capital admission, только future: `PAPER_CANDIDATE → PAPER_RUNNING →
   PAPER_EVIDENCE_READY → OWNER_PILOT_GATE → LIMITED_LIVE → OWNER_LIVE_GATE →
   LIVE`.
4. Runtime, только future: `NOT_DEPLOYED → STARTING → RUNNING ↔ DEGRADED →
   PAUSING → PAUSED → STOPPED`, с `RECONCILING/PROTECT/EMERGENCY/ROLLBACK`.

Backtest, Replay, Test и Review — повторяемые evidence jobs, а не одноразовые
ступени линейного lifecycle. Изменение code/config/data инвалидирует evidence.

### Daily workflow

Утренний порядок чтения: environment/account и freshness → critical alerts →
unknown/reconciling → portfolio risk (future) → degraded/paused → overnight
changes → performance. Performance никогда не должен визуально опережать risk
и свежесть данных.

Command palette может открывать страницы и запускать разрешённые offline jobs,
но финансовое действие не исполняется одним fuzzy-select. Опасная future-команда
требует scope, expected effect, permission, typed confirmation, reason,
idempotency и audit trail.

## 4. Дискуссия и рекомендуемые решения

| Развилка | Designer | Pro Trader | Рекомендация | Осмысленная альтернатива |
|---|---|---|---|---|
| Bot Park | Dual Farm/Operations сохраняет эмоцию и масштаб. | Operations становится default при росте fleet. | Два вида одной query model; Farm default до 5, Operations — при большем парке или по выбору. | Всегда Operations для строгого профессионального режима. |
| Entity model | NPC должен быть узнаваемым воплощением бота, а здания — рынковыми зонами. | Fleet count обязан считать агентов, а не здания или декор. | Один `BotAgent` на одного NPC, отдельный `FarmBuilding`, обязательный `agentKind`. | Operations View может скрывать игровой образ, сохраняя тот же agent ID. |
| Lifecycle | Нужны maturity/activity/gates/incident axes. | Нужны отдельные software/evidence/capital/runtime machines. | Составной state contract; UI собирает понятное представление, не смешивая автоматы. | Упрощённая шкала только для onboarding, всегда с доступом к исходным axes. |
| Readiness | Процент допустим лишь по утверждённой формуле. | `100%` опасно читается как production-ready. | Сейчас убрать общий процент; показать evidence completeness и конкретные gates. | Несколько traceable progress bars: build/evidence/capital. |
| Offline risk | Декор должен отражать state, но не придумывать его. | Зелёный `NORMAL` без telemetry неверен. | `NOT_EVALUATED / OFFLINE / UNKNOWN`; NORMAL только из свежего authoritative source. | Показать policy reference отдельно, без active verdict. |
| Визуальная плотность | Мир должен жить во всех модулях. | В incidents/risk декор обязан уступать критическим данным. | Pixel-world в shell/context; professional surfaces для tables/charts/alerts. | User-selectable Cozy/Compact density при неизменной risk hierarchy. |
| Control plane | UI сначала должен получить truth/provenance layer. | Legacy execution нужно карантинировать; mutations — отдельный этап. | Сначала versioned read-only API; offline commands позже; trading controls только отдельным Owner-approved проектом. | Отдельный remediation slice legacy-кода до любой UI-интеграции. |

## 5. Решения Owner

Полный журнал: [OWNER_DECISIONS.md](OWNER_DECISIONS.md).

- Farm View расширяется через здания/секторы; Operations View остаётся будущим
  масштабируемым представлением.
- Каждый NPC представляет конкретного бота/агента. Crypto, MOEX и другие здания
  группируют NPC по рынку или функции, но сами ботами не считаются.
- Необоснованный readiness `%` удалён; offline risk без telemetry —
  `NOT_EVALUATED`, а не зелёный `NORMAL`.
- Owner Merge, Owner Pilot и Owner Live независимы.
- v1 — solo Owner с будущими seams для teams/permissions.
- Legacy execution остаётся в карантине; сначала допускается только versioned
  read-only API.
- Составная state-модель **ACCEPTED**: development, runtime, gates и risk
  остаются независимыми source-of-truth axes, а Farm показывает краткую сводку.

## 6. Оценка текущего прототипа

Низкие оценки относятся к аудируемому mock, а не маскируются как готовность к
production.

| Designer | Балл | Pro Trader | Балл |
|---|---:|---|---:|
| Visual Quality | 7/10 | Decision Speed | 4/10 |
| Hierarchy | 7/10 | Risk Clarity | 6/10 |
| Character | 8/10 | Data Density | 3/10 |
| Consistency | 6/10 | Daily Usability | 4/10 |
| Motion | 5/10 | Safety | 7/10 |
| Scalability | 4/10 | Scalability | 3/10 |

Итог: visual prototype — `PASS WITH CONDITIONS`; real operations console —
`BLOCKED`.

## 7. Оценка целевого предложения

После объединения dual view, entity taxonomy, provenance, составного lifecycle,
grouped navigation и design/motion foundation критических оценок ниже 8 нет.

| Designer | Балл | Pro Trader | Балл |
|---|---:|---|---:|
| Visual Quality | 8/10 | Decision Speed | 8.5/10 |
| Hierarchy | 9/10 | Risk Clarity | 9/10 |
| Character | 9/10 | Data Density | 8.5/10 |
| Consistency | 8/10 | Daily Usability | 8.5/10 |
| Motion | 8/10 | Safety | 9.5/10 |
| Scalability | 9/10 | Scalability | 9/10 |

Designer verdict: `OWNER DIRECTION IMPLEMENTED IN PROTOTYPE`. Условие оценки —
сохранять стабильную связь «один BotAgent — один NPC», отдельные здания и
обязательный `agentKind`.

Pro Trader verdict: архитектура концептуально готова к Owner review, но её
должны подтвердить screen specs и scenario testing на 5/20/100 ботах.

## 8. Stop gate

Разрешено развивать только безопасный read-only visual prototype в границах
зафиксированных решений. Backend integration, control plane, Paper/Live и
реальные торговые действия не начинаются без отдельного Owner-approved проекта.

## 9. UI-022-001 — Designer + Pro Trader foundation review

Дата: **2026-08-11**

Статус: **PASS — FOUNDATION ONLY**

Scope review ограничен текущим `apps/bot-farm-ui/` и четырьмя foundation docs.
Торговая стратегия, frozen portfolio mandate и PM-DEC-007 не переоценивались;
Owner decisions 1–7 не переоткрывались.

### 9.1 Независимый аудит текущего frontend

Designer verdict: `CONDITIONAL PASS — strong prototype identity; BLOCKED for
scalable product UI`.

| Designer area | Score |
|---|---:|
| Visual quality | 8.4/10 |
| Hierarchy | 7.0/10 |
| Character | 9.3/10 |
| Consistency | 7.1/10 |
| Motion | 6.6/10 |
| Accessibility | 6.0/10 |
| Responsive | 5.8/10 |
| Scalability | 2.8/10 |

Pro Trader verdict: `PASS as Farm orientation/safety prototype; NOT ACCEPTABLE
as daily operator surface`.

| Pro Trader area | Score |
|---|---:|
| Decision speed | 4/10 |
| Risk clarity | 7/10 |
| Data density | 3/10 |
| Daily usability | 4/10 |
| Workflow completeness | 3/10 |
| Safety | 8/10 |
| Scalability | 2/10 |

Общие material findings:

- `AppShell`, routes, documentation links и bottom dock — расходящиеся
  hardcoded sources; Operations View нельзя подключить системно;
- literal `BotId`/`FarmBuildingId`, fixed 2×2 map, Owner coordinates и рендер
  всех bots/free slots не масштабируются до 20–50 modules и 100+ bots;
- текущие SVG sprites и ~1968-line CSS — сильный prototype direction, но не
  versioned asset/design system;
- Farm имеет узнаваемый bespoke cozy character, тогда как внутренние страницы
  местами дрейфуют к generic SaaS card grids;
- professional surfaces требуют крупнее auxiliary text, устойчивого contrast,
  provenance/freshness и отдельных lifecycle/runtime/risk/evidence/gate axes;
- Test Lab progress, farm news и decorative badges не являются runner evidence,
  alerts или monitoring telemetry.

### 9.2 Foundation и закрытые findings

Совместно подготовлены `MENU_ARCHITECTURE.md`, `DESIGN_SYSTEM.md`,
`MOTION_SYSTEM.md` и `SCREEN_CATALOG.md`. Первый независимый docs review нашёл
четыре contract gaps; до финального verdict они закрыты:

1. canonical domains/routes и 37 screen registrations;
2. axis-qualified vocabulary и обязательные `SafetyStrip`/`CompositeState`;
3. canonical Operations roster anatomy, triage order и adaptive precedence;
4. bounded World Canvas для 5/20/50 modules, 5/20/100/500-bot evidence и
   injected read-only cursor/partial/direct-get repository seam.

Дополнительно разделены `LOCAL_SEEN` и authoritative `ACKNOWLEDGED`, Evidence
FAIL оставлен static/no-shake, а Operations имеет zero ambient loops.

### 9.3 Финальные независимые оценки foundation

Designer final verdict: **PASS**, remaining blockers: **NONE**.

| Designer area | Score |
|---|---:|
| Requirements coverage | 9.8/10 |
| IA clarity | 9.6/10 |
| Design system | 9.6/10 |
| Motion system | 9.7/10 |
| Screen catalog | 9.5/10 |
| Accessibility | 9.5/10 |
| Operational truth | 9.8/10 |
| Scalability | 9.6/10 |
| **Overall foundation** | **9.6/10** |

Pro Trader final verdict: **PASS**, remaining blockers: **NONE**.

| Pro Trader area | Score |
|---|---:|
| Decision speed | 9/10 |
| Risk/state clarity | 10/10 |
| Data density contract | 9/10 |
| Daily operator usability | 9/10 |
| Workflow completeness | 9/10 |
| Safety / no trading authority | 10/10 |
| Scalability and testability | 10/10 |
| Cross-document coherence | 9/10 |

### 9.4 Disagreements

**Material disagreements: NONE.** Owner escalation не требуется.

Рабочие tensions разрешены нормативно:

- Farm сохраняется как identity/orientation layer; Operations становится daily
  control surface и adaptive default при 21+ bots без отмены explicit choice;
- Operations остаётся плотным и спокойным, но сохраняет compact NPC/role marker
  и contextual inspector, поэтому не превращается в безликий терминал;
- ambience/watering живут только на Farm; risk/evidence/alerts получают
  статические профессиональные surfaces;
- Evidence PASS, Risk NOT_EVALUATED и Merge/Pilot/Live остаются независимыми
  qualified facets.

### 9.5 Proposed UI-022-002

Следующий bounded slice: typed screen/module registry + route/menu parity,
`/operations` read-only virtualized BotAgent roster, shared SafetyStrip/
CompositeState/provenance primitives, explicit mobile `More`, injected mock read
repository и scale/a11y/performance fixtures. Farm shell сохраняется; массовый
redesign, backend connection и mutation endpoints в slice не входят.

Paper/Live, Telegram/Bitget API, exchange connections, orders/fills, credentials
и реальные деньги остаются **BLOCKED/LOCKED**. UI-022-002 начинается только
после отдельного Owner подтверждения.
