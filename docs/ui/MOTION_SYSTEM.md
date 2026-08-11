# Motion System — Bot Farm

Статус: **PROPOSED FOUNDATION FOR UI-022-002**

Motion объясняет interaction/state и поддерживает уют мира. Он не создаёт
telemetry, evidence, runtime health, gate verdict или trading authority.

## 1. Принципы

1. **Meaning before delight.** Functional feedback приоритетнее ambience.
2. **Animation never proves state.** PASS/FAIL/risk/gate всегда выражены текстом,
   icon/shape и provenance.
3. **World can breathe; Operations stays calm.** Continuous ambience живёт на
   Farm; tables, alerts, incidents и gates не превращаются в игровую сцену.
4. **Short and interruptible.** Navigation/control motion можно прервать новым
   input без очереди анимаций.
5. **Transform/opacity first.** Избегать layout, paint-heavy shadows/filters и
   large-area gradients в цикле.
6. **Reduced motion is first-class.** Meaning и focus order сохраняются при
   полном отключении движения.
7. **No alarm fatigue.** Critical state привлекает внимание кратко, затем
   остаётся сильным статическим сигналом.

## 2. Motion tokens

### 2.1 Duration

| Token | Duration | Use |
|---|---:|---|
| `instant` | 0 ms | Reduced motion, direct state swap. |
| `press` | 80 ms | Button/control depression. |
| `hover` | 120 ms | Hover/focus affordance. |
| `selection` | 150 ms | Selected row/tab/building marker. |
| `panel` | 180 ms | Tabs, small panels, inline disclosure. |
| `popover` | 220 ms | Menu/popover/drawer. |
| `dialog` | 260–280 ms | Dialog enter/exit. |
| `ownerMove` | 360 ms steps(6) | Farm navigation only. |
| `ambientShort` | 2.4–4 s | Small animal/plant idle. |
| `ambientLong` | 6–10 s | Water/wheel/weather; sparse. |

### 2.2 Easing

- `standard`: `cubic-bezier(.2, 0, 0, 1)`;
- `enter`: `cubic-bezier(0, 0, .2, 1)`;
- `exit`: `cubic-bezier(.4, 0, 1, 1)`;
- `press`: `cubic-bezier(.3, 0, .7, 1)`;
- `pixelStep`: `steps(2|4|6, end)` только для pixel actor/prop;
- critical/error не используют playful bounce.

## 3. Interaction motion

### Hover

- control поднимается/подсвечивается максимум на 1–2 px;
- world object может получить outline/glow/sign wobble, но label остаётся
  readable;
- dense table row использует background/border, не transform, чтобы columns не
  двигались;
- hover не раскрывает единственное действие или critical data.

### Press

- 1–2 px downward translate/short shadow reduction;
- feedback начинается немедленно и завершается ≤80 ms;
- disabled/locked не проигрывает press; показывает blocker explanation.

### Focus

- focus ring появляется без delay и без animated travel;
- focus не зависит от hover state;
- при keyboard navigation выбранное building/row может получить 120–150 ms
  static-to-highlight transition, но ring остаётся мгновенным.

### Selection

- selected tab/row/building меняет marker и background;
- route/state меняется до/одновременно с motion, не после декоративной задержки;
- `aria-selected/aria-current/aria-pressed` обновляется сразу.

## 4. Open / close

| Component | Enter | Exit | Focus rule |
|---|---|---|---|
| Tooltip | opacity 120 ms; no scale bounce | 80 ms | Focus stays trigger. |
| Context menu | opacity + translate 4 px, 160–180 ms | 120 ms | First/selected item; return trigger. |
| Popover | opacity + translate 6 px, 180–220 ms | 140 ms | Logical first control, no modal trap. |
| Drawer | translate edge + scrim, 220–260 ms | 180 ms | Trap only when modal; return trigger. |
| Dialog | opacity + scale .98→1, 240–280 ms | 180 ms | Modal trap, title announced. |
| Accordion | content reveal ≤180 ms | ≤150 ms | Trigger retains focus. |

Height `auto` animation не используется на large/virtualized content. При
route transition старый content не задерживает новый status/evidence.

## 5. Navigation motion

### Owner movement

- keyboard/D-pad меняет active building и focus сразу;
- avatar проходит короткий stepped transition `360 ms steps(6)`;
- повторный input прерывает предыдущий path и идёт к последней valid target;
- движение не запускает fetch/job/gate и не означает runtime activity;
- screen reader получает одно polite announcement destination;
- reduced motion переносит avatar мгновенно.

### Farm ↔ Operations

View switch сохраняет query/filter. Допустим crossfade/position continuity
≤180 ms; запрещён cinematic transition, скрывающий data. При large DOM
Operations появляется сразу, а Farm снимается с render до ambience restart.

### Route changes

- focus переходит к main heading/content landmark;
- scroll restoration предсказуем;
- breadcrumbs/context обновляются сразу;
- critical truth strip не анимируется заново при каждом route.

## 6. NPC motion states

NPC animation разделяется на decorative identity и authoritative job feedback.

| State | Motion | Источник истины |
|---|---|---|
| `idleDecorative` | редкий 1–3 px step/breath/turn | Local cosmetic; не runtime. |
| `selected` | один короткий greeting/outline | UI selection. |
| `jobRunning` | tool/work loop + explicit RUNNING label | Authoritative evidence job only. |
| `jobPassed` | одноразовый acknowledgement | Completed immutable job result. |
| `attention` | один short cue, затем static badge | Typed alert/warning. |
| `blocked/locked` | static pose + blocker sign | Gate/authority state. |
| `offline/unknown` | neutral static/slow cosmetic idle | Connectivity/evidence state; never green pulse. |

Current global `sprite-idle` loop is prototype. At scale, actors receive
randomized phase only for cosmetic motion; deterministic tests disable/random
seed it. For 100+ bots Farm shows representatives/aggregates, not 100 animated
NPCs.

## 7. Ambient scenery

Allowed on Farm:

- water ripple/wheel;
- duck/chicken/plant idle;
- subtle cloud/light/weather;
- seasonal particles only under strict budget.

Rules:

- decorative and `aria-hidden`;
- paused when tab hidden, component offscreen or Operations active;
- no ambience under critical modal/incident focus if distracting;
- no large continuous filter, blur, box-shadow or background-position animation;
- mobile uses reduced count/complexity even without OS reduced-motion setting;
- weather/season never encodes risk/runtime.

## 8. Feedback motion

### Success

- one 180–300 ms stamp/check reveal;
- no confetti for routine test PASS;
- show scope, source and timestamp with the success;
- UI demo completion uses `DEMO`, never PASS styling.

### Warning

- one amber edge/highlight cue;
- persistent static icon+label after cue;
- repeated pulse only for genuinely changing time-bound state and maximum low
  frequency.

### Critical

- one strong 200–300 ms reveal, optional two-cycle border pulse;
- after ≤2 cycles remain static high-contrast;
- no playful shake/bounce;
- sound optional/muted and never sole channel;
- critical state appears above performance/ambient content.

## 9. Gate pass / fail

| Event | Motion | Required text |
|---|---|---|
| Evidence PASS | single check/stamp | Scope + run/artifact + capturedAt. |
| Evidence FAIL | direct static edge/reveal; no shake on professional surfaces | Failing check + open details. |
| Owner Merge decision | deliberate seal/reveal after server-confirmed result | MERGE only. |
| Pilot/Live blocked | no success motion; static lock/barrier | Independent blocker/reason. |
| Gate revoked/expired | warning→critical transition once | Previous/current state + timestamp. |

Passing Merge never animates Pilot/Live. Client animation cannot optimistically
show gate success before authoritative response.

## 10. Test / Replay / Backtest motion

- progress determinate only when total units are known; otherwise calm
  indeterminate bar with RUNNING label;
- long runs show elapsed time and cancellation state, not decorative speed;
- completion links to immutable result/report;
- compare transition highlights changed rows once, without moving columns;
- replay timeline scrub has immediate response and no easing that changes
  perceived event time;
- current 900 ms local Test Lab animation remains explicitly `UI DEMO ONLY`.

## 11. Reduced motion

`prefers-reduced-motion: reduce` behavior:

| Category | Reduced behavior |
|---|---|
| Hover/press/focus | Instant state; focus ring preserved. |
| Menu/popover/dialog | Instant or opacity ≤50 ms. |
| Owner move | Instant destination + announcement. |
| NPC idle | Disabled. |
| Ambient scenery | Disabled/static frame. |
| Success/warning/critical | Instant static icon+text; no pulse/shake. |
| Progress | Static/determinate update; indeterminate uses text/elapsed time. |

Текущий global CSS override — хорошая prototype safety net, но UI-022-002
должен добавить component tests и не полагаться только на duration `0.01ms`.

## 12. Performance limits

### Budgets

- target 60 FPS for interaction; no required interaction ниже 30 FPS;
- desktop Farm: ≤12 simultaneous ambient animated elements;
- mobile Farm: ≤4;
- Operations: 0 continuous ambient animations, ≤1 processing indicator per
  visible active job group;
- ≤1 attention loop per viewport; critical cues stop after two cycles;
- no animation of all rows in virtualized table;
- sprite atlas/assets have versioned size budget established in UI-022-002.

### Implementation constraints

- animate transform/opacity; measure before animating width/height;
- pause on `visibilitychange`/offscreen;
- avoid per-NPC timers; use CSS/shared clock where cosmetic;
- cleanup timers/listeners on unmount;
- route/view switch tears down inactive ambience;
- performance profile scenarios: low-end laptop, 4× DPR, 500-bot fixture,
  50-module navigation, mobile 360 px.

## 13. Deterministic and visual checks

1. Reduced-motion fixture produces no looping animations.
2. Arrow/D-pad movement produces zero network/mutation calls.
3. UI demo completion never renders PASS/evidence success.
4. Gate animation changes only the addressed gate.
5. Offline/unknown/NOT_EVALUATED never receives healthy green pulse.
6. Focus returns correctly after menu/popover/dialog close.
7. Animation timers/listeners are cleaned on unmount.
8. Farm and Operations meet motion budgets under 5/20/100+ bot fixtures.
9. Screenshot/visual tests cover default, hover, pressed, focus, warning,
   critical, locked and reduced-motion states.
