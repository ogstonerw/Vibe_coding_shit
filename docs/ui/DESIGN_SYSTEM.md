# Design System — Cozy Operations

Статус: **PROPOSED FOUNDATION FOR UI-022-002**

Цель: сохранить узнаваемую cozy pixel-art ферму и одновременно дать строгий
язык для evidence, risk и профессиональных data surfaces. Текущий `app.css` и
inline SVG actors являются prototype evidence, а не production design system.

## 1. Слои системы

```text
Foundations
├─ pixel grid, color, type, spacing, elevation, motion
Semantic tokens
├─ surface, text, border, status, focus, data visualization
Components
├─ controls, navigation, overlays, feedback, data display
Patterns
├─ World Canvas, Operations Canvas, evidence, risk, gates
Assets
└─ icons, sprites, buildings, props, ambient scenery
```

Business state никогда не вычисляется из visual token. Компонент получает
typed state + provenance и только отображает его.

## 2. Pixel grid

### 2.1 Logical grid

- базовая UI spacing unit: `4px`;
- control/layout spacing: `4 / 8 / 12 / 16 / 24 / 32 / 48`;
- border: `2px` compact, `3–4px` world/parchment emphasis;
- icons: logical `16×16` или `24×24`;
- actors: source `32×40`, render только integer scale `2× / 3× / 4×`;
- props: source `16 / 32 / 64`;
- buildings: source `64 / 96 / 128` по complexity tier;
- pixel assets используют integer coordinates и `shape-rendering: crispEdges`;
- fractional scaling допустим для non-pixel layout, но не для sprite canvas.

### 2.2 Layout grid

- desktop Operations: 12 columns, min content 0, resizable side panels;
- tablet: 8 columns;
- mobile: 4 columns;
- World Canvas может использовать spatial map, но labels/controls привязаны к
  readable overlay grid;
- critical text не рисуется внутри bitmap/sprite.

## 3. Token architecture

### 3.1 Naming

```text
primitive.color.wood.900
semantic.surface.shell
semantic.text.primary
component.button.primary.bg.default
pattern.risk.critical.border
```

Компоненты не должны напрямую использовать primitive color, кроме ограниченных
art assets. Theme swap меняет semantic mapping, не JSX.

### 3.2 Material surfaces

| Surface | Назначение | Ограничения |
|---|---|---|
| `shell.wood` | Global header, domain rail, dock | Не использовать под dense table body. |
| `world.grass/water/soil` | Farm map и ambience | Только decorative/world context. |
| `paper.parchment` | Passport, guides, human-readable summaries | Контраст body text ≥ WCAG AA. |
| `operations.canvas` | Tables, charts, logs, monitoring | Спокойный neutral фон, минимум texture. |
| `overlay.popover` | Menus, tooltips, popovers | Чёткий edge/elevation, не сливаться с map. |
| `critical.surface` | Incident/emergency/locked decisions | Никакой декоративной конкуренции. |

Wood и parchment могут иметь subtle code-native texture, но repeated gradients
не должны ухудшать scrolling/paint или readability.

### 3.3 Semantic color

Текущая палитра (`wood`, `paper`, `grass`, `gold`, `red`, `blue`, `amber`) —
направление, не финальные значения. Перед implementation обязательны contrast
tests в light/dark/material contexts.

| Token | Значение |
|---|---|
| `status.success` | Доказанный PASS/released artifact, не runtime health. |
| `status.info` | Neutral information / active selection. |
| `status.processing` | Идущий job с authoritative run state. |
| `status.warning` | Требует внимания, но не emergency. |
| `status.highRisk` | Существенный риск/ограничение. |
| `status.critical` | Incident/emergency/unsafe condition. |
| `status.blocked` | Transition запрещён unmet prerequisite. |
| `status.locked` | Authority/capital gate закрыт. |
| `status.noTelemetry` | Telemetry `NO_DATA`, не environment/mode. |
| `status.disconnected` | Telemetry `DISCONNECTED`, не runtime state. |
| `status.unknown` | Нет свежего authoritative evidence. |

`NOT_EVALUATED` использует unknown/offline language, не success green. Цвет
никогда не является единственным carrier.

## 4. Typography

| Role | Style | Use |
|---|---|---|
| Display | Pixel-compatible/display family, 24–40 px | Brand, world signs, major headings; короткие labels. |
| Heading | Humanist sans, 18–28 px, 700–800 | Page/section hierarchy. |
| Body | Sans, 14–16 px, 400–600 | Instructions, descriptions, tables. |
| Metadata | Sans, 12–13 px | Provenance/freshness; не ниже 12 px в operations. |
| Data | Tabular mono, 12–16 px | IDs, timestamps, numeric values, hashes. |
| Micro label | Sans/mono, 11–12 px, uppercase sparingly | Badge labels; не длинный текст. |

`Courier New` и system fonts текущего prototype заменяются только после
лицензированного font decision и Cyrillic coverage check. Pixel font не
используется для paragraphs, dense tables или critical instructions.

## 5. Status language

### 5.1 Независимые axes и canonical vocabulary

| Axis | Canonical values | Нельзя подменять |
|---|---|---|
| Operating mode | `DEMO`, `OFFLINE_SIMULATION`, future `PAPER`, `LIVE` | Telemetry/runtime/authority. |
| Lifecycle | `IDEA`, `DEVELOPMENT`, `OFFLINE_RC`, `OFFLINE_RELEASED`, `ARCHIVED` | Runtime/risk. |
| Evidence job | `QUEUED`, `RUNNING`, `PASS`, `FAIL`, `BLOCKED`, `CANCELLED` | Owner decision или profitability. |
| Runtime | `NOT_DEPLOYED`, `STARTING`, `RUNNING`, `PAUSED`, `DEGRADED`, `STOPPED`, `UNKNOWN` | Capital admission. |
| Telemetry | `NO_DATA`, `CONNECTED`, `STALE`, `DISCONNECTED`, `UNKNOWN` | Operating mode/runtime health. |
| Risk | `NOT_EVALUATED`, `NORMAL`, `WATCH`, `DE_RISK`, `PROTECT`, `EMERGENCY`, `UNKNOWN` | Test status. |
| Execution/capital | `BLOCKED`, `LOCKED`, future `PAPER_ONLY`, `LIMITED_LIVE`, `UNKNOWN` | Runtime или connectivity. |
| Owner gates | Каждый из `MERGE`, `PILOT`, `LIVE`: `PENDING`, `ACCEPTED`, `REJECTED`, `BLOCKED`, `LOCKED`, `UNKNOWN` | Evidence PASS и другие gates. |

Каждый status component показывает label, semantic icon/shape, state и при
необходимости source + `asOf/freshness`. Не использовать общий readiness `%`.
Axis всегда присутствует в accessible name: `Evidence: PASS`, `Risk:
NOT_EVALUATED`, `Merge: ACCEPTED`. Bare `OFFLINE` и bare `PASS` запрещены.
Отсутствующее поле отображается как `UNKNOWN/NO_DATA`, а не исчезает.

### 5.2 SafetyStrip и CompositeState

`SafetyStrip` обязателен на каждом route выше декоративного content и содержит:

1. operating mode;
2. evidence source + `asOf` + freshness;
3. telemetry/connectivity;
4. Risk meta-state;
5. execution/capital state;
6. material blockers;
7. отдельные Merge/Pilot/Live facets, когда они относятся к текущему scope.

`CompositeState` для bot/module/release содержит stable ID/scope, lifecycle,
runtime, telemetry, risk, execution/capital, latest evidence, alerts и три
независимых Owner gates. Каждый facet имеет `state`, `source`, `asOf` и
optional `reason`; неизвестный facet остаётся видимым. Visual priority:
critical/blocker → risk/unknown/stale → authority → evidence → lifecycle.

### 5.3 Badge anatomy

- icon/shape;
- короткий canonical label;
- optional qualifier (`OFFLINE ONLY`, `STALE 14m`);
- accessible full label;
- tooltip только для определения, не для скрытия blocker.

## 6. Controls

### 6.1 Buttons

Variants:

- `primary` — одно главное безопасное действие области;
- `secondary` — navigation/supporting action;
- `quiet/ghost` — low-emphasis utility;
- `danger` — только scoped destructive workflow;
- `locked` — не action; объясняет authority blocker;
- `icon` — всегда accessible name + tooltip.

States: default, hover, pressed, focus-visible, disabled, loading, success
acknowledgement. Disabled control не получает tooltip-only reason: рядом есть
text/popover trigger. Minimum target 44×44; destructive button не соседствует
с primary без spacing/confirmation.

### 6.2 Inputs

- visible label, description/error slot, optional unit/suffix;
- hover/focus/error/disabled/read-only/loading states;
- numeric/financial inputs future-only, с typed unit и server validation;
- search поддерживает clear, shortcut hint и result count;
- filters используют chips только для applied values, не как decorative badges;
- placeholder не заменяет label.

### 6.3 Selection

Checkbox, radio, toggle, segmented control и tabs имеют разные semantics.
Toggle нельзя использовать для gate/promotion. Farm/Operations — segmented view
switch; environment/capital stage — не toggle.

## 7. Data display

### 7.1 Tables

Operations tables поддерживают:

- sticky header и optional pinned columns;
- sort с явным direction;
- filters/saved views в URL;
- density `Cozy / Compact`;
- row selection отдельно от row navigation;
- virtualization для 100+ bots/large logs;
- empty/loading/error/stale/partial states;
- column units, data source, `asOf` и freshness;
- keyboard row navigation без потери native table semantics;
- horizontal overflow с first/critical columns pinned.

Risk/freshness/blocker columns визуально опережают PnL/performance.

Canonical `OperationsRoster` не является произвольной table. Pinned row anatomy:

1. compact NPC/role marker + Bot ID/name;
2. market/building/module;
3. critical blocker;
4. Risk;
5. telemetry + runtime;
6. freshness + evidence source/latest evidence;
7. lifecycle and alerts;
8. separate Merge/Pilot/Live;
9. latest Test/Replay/Backtest run.

Default triage order: critical → material blocker → stale/unknown → Owner
action required → остальные. Search/filter/sort/density живут в URL. PnL или
performance не являются mandatory placeholder при отсутствии authoritative
data. Operations сохраняет compact NPC identity и contextual inspector, но
имеет zero continuous ambience.

### 7.2 Cards

Cards допустимы для identity, summary, world object и small bounded collection.
Нельзя превращать каждый datum в отдельную SaaS-card. Dense comparison,
monitoring, logs и fleet triage используют table/list/canvas patterns.

Card anatomy: heading, state, essential metadata, action area. Entire clickable
card не содержит nested interactive controls без ясной focus model.

### 7.3 Charts

Charts planned: title, metric definition, range, source, timezone, missing-data
encoding, accessible summary/table. Красный/зелёный не единственная encoding;
decorative sparkline не доказывает performance.

## 8. Overlays and menus

### Tooltip

- короткое non-interactive пояснение;
- pointer delay 400–600 ms, keyboard focus показывает сразу;
- не содержит critical blocker или единственный accessible label;
- закрывается Escape и не перекрывает target.

### Popover

- interactive detail: provenance, status definition, compact filter;
- focus management без modal trap;
- outside click + Escape, focus returns trigger.

### Context menu

- actions для конкретного object;
- доступен pointer и `Shift+F10`;
- destructive/authority items separated и обычно открывают full workflow.

### Dialog

- только task requiring interruption/confirmation;
- title, scope, expected effect, warnings, primary/secondary actions;
- modal focus trap, inert background, Escape policy;
- dangerous future action требует reason/typed confirmation according to its
  approved command contract.

Drawer используется для navigation/inspector на compact screens; dialog не
заменяет обычную page flow.

## 9. Navigation components

- Domain group / module item / bot-context tab / breadcrumb / palette result /
  dock pin — разные components поверх общей registry metadata.
- Active state использует marker + text weight + `aria-current`.
- Badge count не меняет width скачками: tabular numerals/reserved slot.
- World sign может выглядеть как wooden board, но остаётся semantic button/link.

## 10. World Canvas components

### Buildings

Building представляет market/module container, не runtime process. Required:
name, capacity/occupancy, aggregate evidence summary, explicit unknown state,
focus/selected markers и route target.

### NPC/BotAgent

Один NPC — один stable BotAgent ID. Sprite отражает identity/role, но stage,
risk и gate всегда имеют text badge/detail. Demo NPC явно маркирован. Idle
animation cosmetic и не означает «бот работает».

### Owner avatar

Owner movement меняет navigation/focus only. Position не является permission,
approval или operational state. D-pad и keyboard имеют одинаковый contract.

### Scenery

Trees, water, animals, weather и props декоративны, `aria-hidden`, не принимают
input и отключаются/упрощаются при reduced motion/performance pressure.

## 11. Sprite and icon rules

Текущие JSX SVG sprites с одной общей body geometry — prototype. Target:

- versioned sprite/icon manifest;
- stable IDs, source size, integer scales и role/state variants;
- distinct silhouette/accessory for agent kind, не только palette swap;
- 1× source + generated 2×/3×/4× assets либо crisp vector pipeline;
- no remote runtime assets without integrity/version contract;
- no Unicode/emoji as the only meaningful icon;
- decorative assets `aria-hidden`; semantic icons pair with text/accessible name;
- critical iconography consistent across Farm and Operations;
- seasonal skins cannot change status meaning or hit targets.

## 12. Focus, accessibility and localization

- WCAG AA contrast for text/controls; AAA considered for critical data;
- global `:focus-visible` token with at least 2 px clearance;
- skip link, landmarks, heading order, live regions and focus restoration;
- 200% zoom without clipped controls or lost status;
- no hover-only content/actions;
- Cyrillic/Latin/numeric glyph coverage;
- labels allow 30–50% expansion; avoid fixed-width text containers;
- screen reader announces canonical state, source/freshness and blocker;
- reduced motion and forced-colors/high-contrast strategy documented/tested.

## 13. Responsive and density

| Mode | Use | Behavior |
|---|---|---|
| World | Farm orientation | Map may reflow by zones; status remains textual. |
| Cozy operations | Default desktop | Comfortable rows/cards, world accents. |
| Compact operations | Power user / 100+ bots | Dense tables, minimal textures, persistent filters. |
| Mobile | Review/triage | Single column, drawers, critical status first; no dense editing. |

Density changes spacing/row height only. It cannot hide columns carrying risk,
freshness, connectivity or blockers.

## 14. Current gaps to resolve in UI-022-002+

- `app.css` содержит около 1968 lines и сотни selectors с прямыми colors,
  shadows, timings и layout values;
- token set покрывает только часть colors и один shadow;
- Unicode glyphs используются как prototype icons;
- sprites не имеют asset manifest/variant system;
- component APIs смешивают visual tone с domain state;
- mobile rules скрывают content positional selectors и часть passport metadata;
- нет operations table primitives, form controls, overlay primitives или
  contrast/visual regression tests.

## 15. UI-022-002 acceptance proposal

1. Token packages разделяют primitive/semantic/component values.
2. Минимальный component inventory имеет documented variants/states.
3. Status matrix покрывает все accepted axes без readiness shortcut.
4. Farm и Operations используют общие semantic state components.
5. Prototype glyphs/sprites получают manifest и replacement plan.
6. Contrast, keyboard, 200% zoom, reduced motion и responsive fixtures входят в
   deterministic/visual checks.
7. 100+ bot table scenario не деградирует в card grid.
8. Critical risk/evidence не скрываются theme, density или game decoration.
9. `SafetyStrip` и `CompositeState` snapshot/a11y tests проверяют все axes,
   qualified labels и видимый `Risk: NOT_EVALUATED`.
10. `OperationsRoster` проверяется на canonical columns/order, compact identity,
    bounded virtualization и отсутствие card-grid fallback.
