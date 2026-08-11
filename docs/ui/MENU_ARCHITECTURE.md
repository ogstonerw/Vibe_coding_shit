# Menu Architecture — Bot Farm

Статус: **PROPOSED FOUNDATION FOR UI-022-002**

Область: navigation contract для cozy pixel-art World Canvas и
профессионального Operations Canvas. Документ не реализует новый shell, не
добавляет backend и не создаёт trading authority.

## 1. Проблема текущего прототипа

Текущий `AppShell` полезен как визуальная проверка, но его нельзя масштабировать
как production navigation:

- пять primary routes заданы массивом внутри `AppShell.tsx`;
- routes отдельно повторяются в `App.tsx`;
- bottom dock содержит ещё четыре прямые ссылки и декоративное действие;
- responsive CSS предполагает ровно пять primary items, а на малом экране
  скрывает dock items по позиции;
- нет domain groups, module registry, breadcrumbs, favorites, recent,
  bot-context navigation, global search или command palette;
- видимость пункта не связана с feature state, workspace, permission или
  authority.

До UI-022-002 текущий shell остаётся prototype. Массовая замена в этом slice
запрещена.

## 2. Принципы

1. **Одна registry — несколько представлений.** Route, side menu, command
   palette, breadcrumbs и dock читают одну module registry, но применяют разные
   presentation rules.
2. **Global ≠ domain ≠ bot context.** Каждый уровень отвечает на отдельный
   вопрос и не дублирует соседний.
3. **World Canvas и Operations Canvas равноправны.** Farm сохраняет характер и
   ориентацию; Operations предоставляет точность и плотность.
4. **Navigation не является authority.** Наличие route или command не открывает
   Merge, Pilot, Live либо финансовое действие.
5. **Blocked не маскируется.** Planned/blocked/locked modules показываются с
   причиной либо скрываются по ясной product rule; disabled item всегда имеет
   объяснение.
6. **Deep links устойчивы.** Workspace, bot, portfolio, filters, sort и view
   живут в URL/query model, а не только в React state.
7. **Keyboard first, pointer friendly.** Все уровни доступны без hover и без
   context-menu-only actions.
8. **Cozy не значит медленно.** Повторное действие доступно через recent,
   favorites, shortcuts и command palette.

## 3. Навигационная модель

```text
Global shell
├─ Brand / Home
├─ Workspace + environment
├─ Global truth strip: connectivity, freshness, critical blockers
├─ Search / Command palette
├─ Alerts / tasks
└─ Owner profile

Domain rail
├─ Farm
├─ Bots
├─ Research
├─ Validation
├─ Risk & Safety
├─ Delivery
├─ Trading (blocked/locked until separate Owner gate)
├─ Observability
└─ Platform

Module submenu
└─ Views/routes выбранного domain

Context rail/tabs
├─ Bot context
├─ Portfolio context
└─ Run/release/incident context

Quick access
├─ Favorites
├─ Recent
├─ Command palette
└─ Bottom dock
```

## 4. Global navigation

### 4.1 Верхняя панель

Постоянные элементы слева направо:

1. **Brand/Home** — возвращает к явно выбранному или сохранённому
   Farm/Operations view; если выбора нет, применяется fleet-size default из
   раздела 12.
2. **Workspace switcher** — v1 показывает один workspace, но route/data contract
   уже принимает `workspaceId`; отсутствие server-side authorization явно
   помечается.
3. **Environment chip** — `DEMO`, `OFFLINE`, future `PAPER`; `LIVE` не может
   появиться из client state.
4. **Truth strip** — обязательные cross-product facts: operating mode,
   evidence source + `asOf/freshness`, telemetry/connectivity, текущий Risk
   meta-state (включая `NOT_EVALUATED`), execution/capital lock и material
   blockers. Test count не заменяет operational health. Если gate относится к
   scope, Merge/Pilot/Live показываются отдельными facets.
5. **Global search / command palette trigger** — `Ctrl/Cmd+K`.
6. **Alerts/tasks** — severity + unread count; не декоративные farm news.
7. **Owner profile** — identity, workspace, preferences; permissions приходят
   только с server contract.

При ширине меньше 860 px Brand, environment, critical lock и palette trigger
остаются видимыми. Остальное уходит в accessible overflow drawer; критический
status нельзя скрыть только из-за ширины.

### 4.2 Breadcrumbs

Breadcrumb строится из registry и context:

```text
Farm / Crypto Coop / TB-001 / Replay / Run #R-1042
```

- каждый сегмент, кроме текущего, является ссылкой;
- collapsed middle segments доступны через menu;
- breadcrumb не заменяет bot-context tabs;
- back navigation сохраняет query/filter context.

## 5. Domain groups и submenus

| Domain | Primary modules | Правило |
|---|---|---|
| Farm | Dashboard, Farm View, Activity | Эмоциональный home и быстрый обзор. |
| Bots | Bot Park, Bot Detail context, Create, Builder, Versions | `Farm / Operations` — views одной выборки. |
| Research | Strategies, Journal, Marketplace | Не смешивать hypothesis с release evidence. |
| Validation | Test Lab, Backtests, Replay, Reports | Runs — повторяемые jobs с provenance. |
| Risk & Safety | Risk Center, Portfolio Risk, Bot Risk, Alerts, Incidents | Risk/freshness выше performance. |
| Delivery | Reviews, Releases, Build Archive | Evidence → review → Owner Merge, без capital inheritance. |
| Trading | Paper, Live Gate/Monitoring, Trades, Positions, Orders | Вся группа BLOCKED/LOCKED либо no-data до отдельных gates/contracts. |
| Observability | Monitoring, Logs, Notifications | Плотные professional surfaces; не путать с Bot Park Operations View. |
| Platform | Integrations, Connections, Secrets, Docs, Settings, Teams, Modules | Locked integrations не выглядят активными. |

Domain rail:

- группы collapsible и сохраняют состояние per workspace;
- active group всегда раскрыта;
- badge показывает только actionable count с определённой семантикой;
- порядок задаёт registry, не component source;
- module с `planned` доступен как roadmap preview без action;
- module с `blocked/locked` показывает blocker tooltip/popover;
- permission-hidden и feature-unavailable — разные состояния.

Module submenu живёт рядом с domain rail на широком экране, в drawer/accordion
на малом. Он не должен раздувать global header.

## 6. Bot-context menu

При выбранном bot ID появляется устойчивый контекст:

```text
Overview | Build | Tests | Backtests | Replay | Risk | Runs | Releases | Logs
```

Правила:

- bot identity, market, environment и freshness остаются видимыми;
- tabs показывают badge только для failure/warning/action required;
- недоступный view объясняет причину (`NO_DATA`, `NOT_IMPLEMENTED`,
  `AUTHORITY_BLOCKED`);
- смена tab не сбрасывает bot selection;
- смена bot сохраняет совместимый tab, иначе открывает Overview;
- next/previous bot и `G then B`/palette ускоряют fleet triage;
- mobile использует горизонтальный scroll + overflow menu, но critical tabs не
  прячутся без доступного overflow.

Bot-context menu не содержит one-click Paper/Live promotion. Будущая опасная
команда требует отдельного command contract и confirmation flow.

## 7. Command palette

### 7.1 Разрешённая область

- открыть module/view/bot/run/release/incident;
- переключить Farm/Operations и density;
- применить saved view/filter;
- открыть documentation/help;
- запустить только явно разрешённый offline job через отдельный preflight
  flow — не напрямую из fuzzy result.

### 7.2 Запрещённая область

- включить Live/Paper;
- отправить, изменить или отменить order;
- изменить risk policy/limits;
- подтвердить Owner gate;
- показать или копировать secret value.

### 7.3 Result anatomy

Каждый result содержит icon, primary label, domain path, entity/environment,
shortcut и state. Disabled result остаётся searchable, если объяснение blocker
полезно. Для destructive/future financial command palette может только открыть
полноценный scoped workflow; она не исполняет действие.

Keyboard contract: `Ctrl/Cmd+K` open, arrows navigate, Enter opens, Escape
closes/returns focus, Tab не запирается вне dialog semantics. Search results
virtualize при больших registries.

## 8. Bottom dock

Bottom dock — quick-access shelf, а не вторая primary navigation.

Рекомендуемый состав:

- до трёх user favorites;
- Recent/History;
- Alerts/Notifications;
- Help/Documentation;
- один harmless contextual delight action, если он не вытесняет operations.

Текущие Events, Notifications, Builds и Docs мигрируют в соответствующие
domains; пользователь может pin их обратно. «Полить ферму» остаётся только в
Farm View и всегда подписано как cosmetic/local.

На mobile dock содержит максимум четыре icon+label targets; остальные доступны
через `More`. Нельзя скрывать item через `nth-child`: visibility определяется
registry priority и user pins.

## 9. Context menus

| Target | Read-only actions сейчас | Future actions |
|---|---|---|
| Building | Open zone, filter bots, pin, inspect capacity | Add/reorder module после отдельного Builder contract. |
| NPC/Bot | Open passport, open in Operations, favorite, copy stable ID | Scoped operational commands только с authority. |
| Table row | Open, compare, pin column/view, copy link | Bulk actions только permission-aware и audited. |
| Evidence run | Open report, compare, copy artifact link | Rerun через preflight; никогда не переписывать evidence. |
| Alert/incident | Open context, mark `LOCAL_SEEN` without changing authoritative count | Server `ACKNOWLEDGED` и contain/reconcile через отдельный workflow. |

Context menu никогда не является единственным способом выполнить действие.
`Shift+F10`/Menu key, keyboard arrows, Enter/Space и Escape обязательны. Menu
закрывается при route change, возвращает focus trigger и не выходит за viewport.
Tooltips не содержат интерактивные controls; для сложного объяснения используется
popover.

## 10. Canonical ownership и future module registry

`Operations` без qualifier означает **Bot Park Operations View**: canonical
read-only roster по route `/operations`, domain `bots`, module `bot-park`.
Professional monitoring/logging принадлежит domain `observability`; route
namespace — `/observability/*`. Farm home — `/farm`; entity context —
`/bots/:botId/*`. Farm может встраивать bounded projection Bot Park, но не
регистрирует этот module второй раз.

Entry points из dock, `More`, palette или contextual links являются aliases к
одному `screenId`, а не дополнительными owners. Canonical domain IDs:

| `domainId` | Canonical modules | Route namespace |
|---|---|---|
| `farm` | dashboard, activity | `/farm/*` |
| `bots` | bot-park, bot-detail, create, builder, versions | `/operations`, `/bots/*` |
| `research` | strategies, journal, marketplace | `/research/*` |
| `validation` | tests, backtests, replay, reports | `/validation/*` |
| `trading` | paper, live-gate, live-monitoring, trades, positions, orders | `/trading/*` — blocked/locked/no-data |
| `risk-safety` | risk-center, portfolio-risk, bot-risk, alerts, incidents | `/risk/*` |
| `delivery` | reviews, releases, builds | `/delivery/*` |
| `observability` | monitoring, logs, notifications | `/observability/*` |
| `platform` | integrations, connections, secrets, docs, settings, profile, teams, modules | `/platform/*` |

Registry matrix row is normative and has exactly:

```text
screenId → domainId → moduleId → route → canvasMode → availability
```

`canvasMode` is `world | operations | document | none`; it never creates a
domain. Validator rejects duplicate `screenId`/route, ownership outside the
table, mismatched breadcrumb/menu owner, unknown alias and an active route for
blocked financial capability. `SCREEN_CATALOG.md` owns purpose/state details;
this table owns domain/route namespaces.

Canonical screen registrations (number corresponds to `SCREEN_CATALOG.md`):

| # | `screenId` | `domainId / moduleId` | Route | Canvas | Availability |
|---:|---|---|---|---|---|
| 01 | `farm.dashboard` | `farm / dashboard` | `/farm` | world | prototype |
| 02 | `bots.operations` | `bots / bot-park` | `/operations` | operations | planned |
| 03 | `bots.detail` | `bots / bot-detail` | `/bots/:botId` | document | prototype |
| 04 | `bots.create` | `bots / create` | `/bots/create` | document | planned |
| 05 | `bots.builder` | `bots / builder` | `/bots/:botId/builder` | operations | planned |
| 06 | `validation.tests` | `validation / tests` | `/validation/tests` | operations | prototype |
| 07 | `validation.backtests` | `validation / backtests` | `/validation/backtests` | operations | planned |
| 08 | `validation.backtest-report` | `validation / reports` | `/validation/backtests/:runId` | document | planned |
| 09 | `validation.replay` | `validation / replay` | `/validation/replay` | operations | planned |
| 10 | `validation.replay-report` | `validation / reports` | `/validation/replay/:runId` | document | planned |
| 11 | `trading.paper` | `trading / paper` | `/trading/paper` | operations | blocked |
| 12 | `trading.live-gate` | `trading / live-gate` | `/trading/live-gate` | document | locked |
| 13 | `trading.live-monitoring` | `trading / live-monitoring` | `/trading/live-monitoring` | operations | locked |
| 14 | `risk.center` | `risk-safety / risk-center` | `/risk` | operations | prototype |
| 15 | `risk.portfolio` | `risk-safety / portfolio-risk` | `/risk/portfolio` | operations | planned |
| 16 | `risk.bot` | `risk-safety / bot-risk` | `/bots/:botId/risk` | operations | prototype |
| 17 | `trading.trades` | `trading / trades` | `/trading/trades` | operations | no-data |
| 18 | `trading.positions` | `trading / positions` | `/trading/positions` | operations | no-data |
| 19 | `trading.orders` | `trading / orders` | `/trading/orders` | operations | no-data |
| 20 | `risk.alerts` | `risk-safety / alerts` | `/risk/alerts` | operations | planned |
| 21 | `risk.incidents` | `risk-safety / incidents` | `/risk/incidents` | operations | planned |
| 22 | `delivery.reviews` | `delivery / reviews` | `/delivery/reviews` | document | prototype |
| 23 | `delivery.releases` | `delivery / releases` | `/delivery/releases` | operations | prototype |
| 24 | `delivery.release-detail` | `delivery / releases` | `/delivery/releases/:releaseId` | document | planned |
| 25 | `bots.versions` | `bots / versions` | `/bots/:botId/versions` | operations | prototype |
| 26 | `observability.logs` | `observability / logs` | `/observability/logs` | operations | prototype |
| 27 | `research.journal` | `research / journal` | `/research/journal` | document | planned |
| 28 | `research.marketplace` | `research / marketplace` | `/research/marketplace` | operations | planned |
| 29 | `platform.integrations` | `platform / integrations` | `/platform/integrations` | operations | planned |
| 30 | `platform.connections` | `platform / connections` | `/platform/connections` | operations | blocked |
| 31 | `platform.secrets` | `platform / secrets` | `/platform/secrets` | operations | blocked |
| 32 | `observability.notifications` | `observability / notifications` | `/observability/notifications` | operations | prototype |
| 33 | `platform.docs` | `platform / docs` | `/platform/docs` | document | prototype |
| 34 | `platform.settings` | `platform / settings` | `/platform/settings` | document | planned |
| 35 | `platform.profile` | `platform / profile` | `/platform/profile` | document | prototype |
| 36 | `platform.teams` | `platform / teams` | `/platform/teams` | operations | planned |
| 37 | `platform.modules` | `platform / modules` | `/platform/modules` | operations | planned |

Screen 02 — paired capability, а не третий route: его Farm projection — screen
01 `/farm`, а dense projection — `/operations`; оба читают один Bot Park query
contract и сохраняют совместимые filters/selection.

### 10.1 Conceptual registration contract

Conceptual contract, не реализация этого slice:

```ts
interface ModuleRegistration {
  screenId: string;
  domainId: string;
  moduleId: string;
  route: string;
  label: string;
  shortLabel: string;
  iconId: string;
  order: number;
  availability: "prototype" | "planned" | "blocked" | "locked" | "no-data";
  canvasMode: "world" | "operations" | "document" | "none";
  surfaces: readonly ("farm" | "operations" | "mobile")[];
  contexts: readonly ("global" | "bot" | "portfolio" | "run")[];
  requiredCapabilities: readonly string[];
  badgeSource?: string;
  shortcut?: string;
}
```

Registry хранит presentation metadata, но не financial permission verdict.
Routes lazy-load по module boundary. Invalid duplicate ID/route, unknown domain,
missing icon/label или forbidden authority declaration должны fail validation.

## 11. Масштаб 5 / 20 / 50 modules

| Масштаб | Domain rail | Discovery | Dock | Rendering |
|---:|---|---|---|---|
| 5 | Все modules с полными labels; group headers можно не сворачивать. | Direct scan + shortcuts. | 3–4 utilities. | Eager допустим для prototype. |
| 20 | Collapsible domain groups, active group open, favorites/recent сверху. | Search/palette, breadcrumbs, saved views. | Только pins + alerts/help. | Route-level lazy loading. |
| 50 | Stable groups + searchable module directory; no flat list. | Palette-first, favorites, recent, role/capability filters. | 4 fixed slots + More. | Virtualized result lists, lazy metadata/panels, performance telemetry. |

Если modules больше 50, registry и information architecture пересматриваются;
нельзя просто добавлять scroll к бесконечному rail.

World Canvas следует отдельному bounded contract:

| Modules/buildings | Farm presentation |
|---:|---|
| 5 | Отдельные здания полностью видимы; direct spatial navigation. |
| 20 | District/sector clusters, выбранный sector и inspector; не 20 full-detail buildings одновременно. |
| 50 | Aggregate districts + search/jump/minimap; current scene bounded, полный registry доступен через directory/Operations. |

Добавление module не требует нового hardcoded coordinate. Layout strategy и
sector metadata приходят из registry; capacity не рендерится как N пустых
slots.

## 12. Масштаб bot fleet

| Fleet | Default presentation | Navigation behavior |
|---:|---|---|
| 1–5 | Farm View | Все NPC видимы; direct spatial navigation. |
| 6–20 | Last user choice; Operations рекомендуется для triage | Farm группирует по buildings; filters/query общие. |
| 21–100+ | Operations View | Virtualized rows, saved views, grouping, comparison, keyboard triage. Farm остаётся overview, не пытается показать каждого NPC одновременно. |

Precedence выбора canvas: explicit route/query → выбор пользователя в текущей
сессии → сохранённая preference → fleet-size default. Поэтому 21+ bots
предлагают/открывают Operations только при отсутствии явного выбора; Farm
остаётся доступна всегда.

## 13. Responsive и accessibility contract

- Desktop ≥1280: global header + domain rail + optional module/context rail.
- Tablet 861–1279: domain drawer/compact rail, context tabs, persistent truth
  strip.
- Mobile ≤860: one-column content, navigation drawer, bottom quick bar, palette;
  no hidden critical gate/risk status.
- Touch target минимум 44×44 CSS px; focus ring не обрезается.
- Active/current/blocked различаются текстом, формой/icon и цветом.
- Menu landmarks и accessible names уникальны; badge counts имеют spoken label.
- Opening/closing overlay restores focus and respects reduced motion.

## 14. UI-022-002 acceptance proposal

1. `AppShell` больше не содержит literal primary navigation array.
2. Routes/menu/palette/breadcrumbs получают metadata из validated registry.
3. Scenario fixtures доказывают поведение при 5/20/50 modules.
4. Bot Park сохраняет один query context при Farm ↔ Operations.
5. Bot-context menu работает keyboard-only и с deep links.
6. Dock не скрывает items через positional CSS.
7. Blocked/locked routes показывают причину и не создают authority.
8. Critical risk/freshness остаются видимыми на desktop/tablet/mobile.
9. Palette не исполняет financial actions.
10. Navigation performance проверяется на 50 modules и 500 bots: virtualized
    roster держит bounded DOM (не более 120 rows с overscan), сохраняет
    keyboard focus/selection/URL filters, а локальные filter/sort/navigation
    укладываются в p95 ≤100 ms на зафиксированном reference CI profile.
11. Registry validator проверяет canonical ownership matrix и route/menu/
    breadcrumb parity.
12. На каждом route обязательный Truth strip показывает Risk meta-state и
    provenance выше декора.
