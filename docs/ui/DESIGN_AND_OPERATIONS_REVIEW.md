# Design and Operations Review

Статус: **READY FOR OWNER ARCHITECTURE REVIEW**

Режим: независимые read-only аудиты; торговая логика и gates не изменялись

## 1. Общий вердикт

Текущий frontend — выразительный и безопасно изолированный visual prototype
offline Slice 02. Как console для управления реальными ботами он **BLOCKED**:
нет authoritative API/telemetry, control plane, positions/orders/fills и
допуска капитала.

Объединённая рекомендация экспертов:

- оставить «Ферму ботов» главным эмоциональным миром;
- создать отдельный Operations Canvas для точных данных;
- разделить Trading Bot, Platform Module/Building и Agent/NPC;
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
- Один тип `Bot` одновременно для TB-001, будущего TB-002, Sandbox и
  Risk/Replay/Review-служб.
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
| Entity model | Боты, здания и NPC должны быть разными визуальными архетипами. | Иначе fleet count/health становятся ложными. | Отдельные `TradingBot`, `PlatformModule`, `Agent/NPC`. | Единый registry только с обязательным type discriminator и раздельными counts. |
| Lifecycle | Нужны maturity/activity/gates/incident axes. | Нужны отдельные software/evidence/capital/runtime machines. | Составной state contract; UI собирает понятное представление, не смешивая автоматы. | Упрощённая шкала только для onboarding, всегда с доступом к исходным axes. |
| Readiness | Процент допустим лишь по утверждённой формуле. | `100%` опасно читается как production-ready. | Сейчас убрать общий процент; показать evidence completeness и конкретные gates. | Несколько traceable progress bars: build/evidence/capital. |
| Offline risk | Декор должен отражать state, но не придумывать его. | Зелёный `NORMAL` без telemetry неверен. | `NOT_EVALUATED / OFFLINE / UNKNOWN`; NORMAL только из свежего authoritative source. | Показать policy reference отдельно, без active verdict. |
| Визуальная плотность | Мир должен жить во всех модулях. | В incidents/risk декор обязан уступать критическим данным. | Pixel-world в shell/context; professional surfaces для tables/charts/alerts. | User-selectable Cozy/Compact density при неизменной risk hierarchy. |
| Control plane | UI сначала должен получить truth/provenance layer. | Legacy execution нужно карантинировать; mutations — отдельный этап. | Сначала versioned read-only API; offline commands позже; trading controls только отдельным Owner-approved проектом. | Отдельный remediation slice legacy-кода до любой UI-интеграции. |

## 5. Вопросы Owner — требуется решение

1. Подтверждаем ли два равноправных режима Bot Park и правило default:
   **Farm для 1–5, Operations для 6+**, с ручным сохранённым выбором?
2. Подтверждаем ли строгую taxonomy: **торговые боты отдельно, здания/службы и
   NPC отдельно**, без общего счётчика «ботов»?
3. Подтверждаем ли составную state-модель и отказ от одной линейной шкалы как
   источника истины?
4. Убираем ли необоснованный readiness `%`, а offline `NORMAL` меняем на
   `NOT_EVALUATED/OFFLINE`, пока нет authoritative telemetry?
5. Подтверждаем ли три независимых Owner gate: **Merge/Release, Pilot и Live**,
   без автоматического наследования разрешений?
6. Для v1 проектируем UX под **solo Owner**, но сразу резервируем workspace,
   permissions и teams в URL/data/navigation contract?
7. Подтверждаем ли технический порядок: **legacy execution в карантине →
   versioned read-only API → Bot Park/Bot Detail → Test/Replay vertical slice**;
   никакого control plane и Live UI сейчас?

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

Designer verdict: `READY FOR OWNER ARCHITECTURE REVIEW`. Условие оценки — не
смешивать Trading Bot, Platform Module и NPC обратно в одну сущность.

Pro Trader verdict: архитектура концептуально готова к Owner review, но её
должны подтвердить screen specs и scenario testing на 5/20/100 ботах.

## 8. Stop gate

До ответа Owner подробные screen specs, design-system implementation и массовая
переработка React не начинаются. Текущий visual prototype может быть сохранён
как evidence направления, но не расширяется в operational control plane.
