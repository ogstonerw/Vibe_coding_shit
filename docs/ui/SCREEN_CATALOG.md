# Screen Catalog — Bot Farm

Статус: **PROPOSED FOUNDATION FOR UI-022-002**

Этот каталог развивает coverage из `PRODUCT_UX_ARCHITECTURE.md` до уровня
screen contract. Он описывает информационную и interaction-модель, но не
реализует новый shell, backend, trading connectivity или финансовые действия.
Текущий frontend остаётся prototype, а поля `planned`, `future`, `BLOCKED` и
`LOCKED` не являются обещанием доступной функции.

## 1. Общий контракт экранов

Каждый экран обязан:

- показывать workspace/environment, route context и freshness источника;
- показывать над декором обязательный `SafetyStrip`: operating mode, evidence
  source + `asOf/freshness`, telemetry, Risk meta-state, execution/capital,
  material blockers и отдельные Merge/Pilot/Live facets для текущего scope;
- не сводить `evidence`, `runtime`, `risk`, `execution`, `Merge`, `Pilot` и
  `Live` к одному readiness status;
- иметь явные `loading`, `empty`, `partial`, `stale`, `error`, `blocked`,
  `locked` и `no authority` states там, где они применимы;
- давать keyboard path ко всем действиям; tooltip дополняет label, но не
  является единственным способом понять control;
- сохранять фильтры, сортировку, density и выбранный entity в URL/query model;
- отделять cosmetic/game feedback от authoritative evidence;
- на малых экранах менять composition, а не скрывать критический state;
- для длинных наборов использовать aggregation, search, cursor pagination или
  virtualization вместо рендера всех карточек/NPC.

Общий порядок контента: **critical blockers → current scoped state → primary
work → evidence/provenance → history/help**. Неподдерживаемая операция не
появляется как активная кнопка.

## 2. Farm и bot lifecycle

В колонке «Menus / tooltips» перечислены screen-local menus; global navigation,
command palette и bottom dock определены в `MENU_ARCHITECTURE.md`.

| # / экран / статус | Purpose и primary action | Navigation и content hierarchy | States | Menus и tooltips | Microinteractions, animation и scaling |
|---|---|---|---|---|---|
| **01 Farm / Dashboard** — mock prototype | За секунды понять состояние фермы; открыть приоритетный blocker, building или bot. | Home/Farm; truth strip → aggregated modules/bots → map → recent evidence/activity. | Loading skeleton, empty workspace, partial module error, stale snapshot, critical blocker, offline/demo. | Building/NPC context menus; tooltip объясняет status facet, capacity и freshness. | Hover/selection и короткое перемещение Owner; ambience только здесь. 5 modules — individual buildings; 20 — districts/selected inspector; 50 — aggregate districts + search/jump. 5 bots — NPC; 20 — capped representatives + `+N`; 100+ — aggregates/Operations. |
| **02 Bot Park: Farm + Operations** — Farm prototype, Operations planned | Найти, сравнить и открыть bot; переключить spatial и dense view без потери query context. | Bots; shared search/filter/grouping → Farm/Operations switch → selection inspector. | No results, stale/partial rows, unknown facets, archived/blocked bots. | Saved views, columns, density, group; row/NPC menu с Open, Compare, Favorite, Copy ID. | Selection синхронизируется между views, без celebratory motion. Virtualized roster и aggregate Farm обязательны для 100+. |
| **03 Bot Detail / Passport** — mock prototype | Увидеть identity, lifecycle, composite state и evidence; открыть разрешённый workflow. | Bot context; composite state above fold → blockers → lifecycle → evidence/risk → runs/releases/logs. | Not evaluated, no data, stale, partial API, archived, blocked action, missing evidence. | Bot-context tabs/menu; tooltip для каждого gate, source, age и authority boundary. | Tab/inspector transitions 180 ms; state change краткий и не подразумевает live. Long history paginated; narrow screen складывает secondary panels ниже. |
| **04 Create Bot** — absent/planned | Создать authority-free draft из mandate/template; primary action — Save draft. | Bots → Create; identity → module/template → mandate inputs → review summary. | Blank, validation error, incompatible template, draft saved, no permission; execution options absent. | Template picker, help popovers, Cancel/Save draft dialog. | Inline validation без shaking; step transition reduced to instant under reduced motion. Large registries searchable and grouped. |
| **05 Builder** — absent/planned | Настроить typed contracts, strategy inputs и version; primary action — Validate draft. | Bot → Build; structure tree → editor/form → validation/evidence panel → version diff. | Dirty, validating, pass/fail, schema mismatch, conflict, read-only. | File/section context, compare version, diagnostics; tooltips explain contracts, not financial advice. | Changed-field highlight and deterministic validation progress only. Split panes collapse to tabs on mobile; large configs use tree virtualization. |

## 3. Validation, Replay и research

| # / экран / статус | Purpose и primary action | Navigation и content hierarchy | States | Menus и tooltips | Microinteractions, animation и scaling |
|---|---|---|---|---|---|
| **06 Test Lab** — mock prototype | Запустить и разобрать local deterministic suites; primary action — configure/run permitted suite. | Validation → Tests; preflight → suites → failures first → logs/artifacts → history. | Idle, queued/local-running, pass, fail, cancelled, stale artifact, configuration error. | Suite/run menus, filter failed, copy command/artifact; tooltip раскрывает scope и last run. | Progress отражает реальный runner, не таймер UI; fail row reveal. Thousands of assertions virtualized/grouped. |
| **07 Backtests** — absent/planned | Управлять datasets, runs и comparisons без trading authority. | Validation → Backtests; dataset/version filters → run table → compare tray. | No dataset, draft preflight, running, complete, failed, non-comparable, stale. | Run, duplicate config, compare, archive metadata; tooltips для dataset bounds/cost assumptions. | Selection/compare feedback only; charts static by default. Cursor pagination and saved views at scale. |
| **08 Backtest Report** — absent/planned | Проверить результаты, costs, bias и reproducibility; primary action — inspect/compare evidence. | Backtest run; verdict caveats → inputs → metrics → timeline/trades → bias/cost checks → artifacts. | Complete, partial, invalidated, incomparable, missing artifact, stale code/config. | Compare baseline, copy provenance, export permitted report; metric definitions in popovers. | Linked chart/table hover, no profit celebration. Dense desktop; mobile exposes metric groups and horizontally scrollable data tables with labels. |
| **09 Replay** — core CLI exists, UI absent | Настроить bounded deterministic historical replay; primary action — run after preflight. | Validation → Replay; version/dataset bounds → preflight → conflict policy → run. | Ready, invalid bounds, missing input, running, complete, failed, cancelled. | Recent configurations, copy CLI, dataset details; tooltip explains deterministic boundary and offline scope. | Step/progress comes from runner events; no fake 900 ms animation. Large datasets never rendered as raw rows before request. |
| **10 Replay Report** — core summary exists, UI absent | Разобрать decisions, skips/conflicts и reproducibility; primary action — inspect anomaly/evidence. | Replay run; scoped verdict → counts → decision timeline → skips/conflicts → artifacts/provenance. | Complete, partial, invalid, stale, conflict-heavy, artifact missing. | Filter by outcome/reason, jump to event, compare run, copy stable reference. | Timeline selection links details; critical anomalies one-shot highlight. Virtualized events and aggregate-first mobile view. |

## 4. Trading и capital lane — недоступные поверхности

Эти экраны описаны только как future information architecture. Они не
разблокируют Paper/Live, не создают connectivity и не дают торговых команд.

| # / экран / статус | Purpose и primary action | Navigation и content hierarchy | States | Menus и tooltips | Microinteractions, animation и scaling |
|---|---|---|---|---|---|
| **11 Paper Trading** — **BLOCKED / future** | После отдельного gate наблюдать paper execution; сейчас primary action — изучить unmet prerequisites. | Trading → Paper; blocker banner → required evidence/gates → future session summary. | Blocked, not configured, no authority; future states visually labelled conceptual. | Prerequisite details and docs only; disabled controls explain exact blocker. | No simulated live pulse. At future scale, sessions/bots use filterable roster, not card wall. |
| **12 Live Gate** — **LOCKED / future** | Проверить independent evidence и запросить explicit Owner decision; сейчас только locked explanation. | Capital lane; irreversible-warning context → separate prerequisites → decision audit. | Locked, incomplete, expired evidence, future `PENDING/ACCEPTED/REJECTED`; never inherited from Merge. | Evidence inspection; no command palette approval. Tooltips distinguish Merge, Pilot and Live. | Gate transition one-shot and textual; no confetti. Multi-bot decisions remain per scope with batch review, never batch authority by ambiguity. |
| **13 Live Monitoring** — **LOCKED / future** | Будущий контроль live health, risk и containment; сейчас показать недоступность. | Trading → Monitoring; critical state → exposure/health → alerts → positions/orders → audit. | Locked, disconnected, stale, degraded, critical, contained; authoritative telemetry required. | Future incident/containment menus require explicit authority; definitions and timestamps in tooltips. | Operations-calm, no ambient motion; only verified new critical event gets one-shot cue. Virtualized tables and fixed critical strip. |

## 5. Risk, execution evidence и incidents

| # / экран / статус | Purpose и primary action | Navigation и content hierarchy | States | Menus и tooltips | Microinteractions, animation и scaling |
|---|---|---|---|---|---|
| **14 Risk Center** — read-only mock | Увидеть policy state и приоритетные exceptions; primary action — inspect source/blocker. | Risk & Safety; current meta-state → policy provenance → exceptions → history. | NOT_EVALUATED current, no policy, stale, partial, evaluated normal/warn/critical. | Filter scope/severity, open bot/portfolio risk, copy evidence. Tooltip объясняет, почему ladder не означает current. | No green pulse for unknown/offline. Exception table virtualized; mobile keeps meta-state and provenance above list. |
| **15 Portfolio Risk** — absent/future | Будущий обзор exposure, concentration, correlation и limits; сейчас no authoritative data. | Risk → Portfolio; freshness → limits/breaches → exposures → concentration/correlation → evidence. | No data, NOT_EVALUATED, stale, partial, breach, reconciled. | Group/measure/period selectors; metric definitions and source age. | Linked charts/tables with reduced motion; large portfolios aggregate then drill down. |
| **16 Bot Risk** — partial mock | Разобрать risk budget, assumptions и breaches конкретного bot. | Bot → Risk; current meta-state → limits/usage → breaches → evidence/history. | NOT_EVALUATED, no data, stale, within limit, warning, breach. | Scope/version/run filters, open policy/artifact. Tooltip separates configured limit from observed value. | Threshold focus is static, not flashing. Many measures use grouped table and pinning. |
| **17 Trades** — no authoritative data | В будущем анализировать executed trades и attribution; сейчас честный no-data boundary. | Trading → Trades; source/freshness → filters → aggregate → trade rows → attribution. | Unavailable, no data, stale, partial, reconciled/unreconciled. | Columns, saved filter, open order/bot/run; definitions for fees/slippage/source. | Row selection/linked inspector only. Virtualized, server-filterable roster for large history. |
| **18 Positions** — no authoritative data | В будущем видеть positions, exposure и reconciliation; сейчас источник отсутствует. | Trading → Positions; critical exceptions → totals → position rows → reconciliation evidence. | Unavailable, no data, stale, partial, mismatch, reconciled. | Group by bot/instrument/account; open orders/trades; tooltip for timestamp and valuation basis. | No price-tick theatre without feed. Pinned totals, virtualized rows, compact density. |
| **19 Orders** — no authoritative data | В будущем проверить lifecycle, rejects и pending uncertainty; сейчас no-data boundary. | Trading → Orders; rejects/uncertain first → filters → lifecycle rows → raw evidence. | Unavailable, pending, partial fill, filled, rejected, cancelled, unknown/stale. | Filter state, open lifecycle/trades, copy correlation ID; tooltip for venue/source age. | Verified transition may one-shot highlight, never continuous blink. Virtualized event-heavy table. |
| **20 Alerts** — absent/planned | Приоритизировать actionable abnormal conditions; primary action — inspect/ack only with authority. | Risk & Safety → Alerts; severity/freshness → unacknowledged → owned → history. | Empty healthy-with-scope, stale feed, warning, critical, acknowledged, suppressed/expired. | Assign/ack/snooze only when supported; open bot/run/incident. Tooltips explain rule, source and age. | New verified critical alert gets one cue then static. Badge derived from data; grouping and virtualization for alert storms. |
| **21 Incidents** — absent/planned | Вести containment, timeline, ownership и resolution evidence. | Risk & Safety → Incidents; active critical → containment state → timeline → affected entities → evidence/postmortem. | Open, contained, monitoring, resolved, stale/partial timeline, no owner. | Assign, link alert/evidence, permitted containment; destructive actions require confirm and authority. | Timeline inserts are calm and announced accessibly. Large incidents collapse repeated events and paginate. |

## 6. Reviews, delivery и operational history

| # / экран / статус | Purpose и primary action | Navigation и content hierarchy | States | Menus и tooltips | Microinteractions, animation и scaling |
|---|---|---|---|---|---|
| **22 Agent Reviews** — mock prototype | Сопоставить independent verdict с immutable evidence; primary action — inspect finding. | Delivery/Validation → Reviews; unresolved material findings → verdicts → evidence links → history. | Pending, pass, fail, conditional, stale evidence, disagreement, unavailable reviewer. | Filter reviewer/scope/verdict, compare, open artifact. Tooltip показывает reviewer role и reviewed commit. | Diff/finding reveal only; no automatic resolution animation. Many reviews group by release/run and virtualize findings. |
| **23 Releases** — mock prototype | Видеть candidates, independent gates и release history; primary action — open candidate. | Delivery → Releases; blockers → candidate table → separate gates → history. | Draft, evidence incomplete, review pending/fail/pass, Merge pending/accepted, capital separately blocked. | Compare candidates, open manifest/reviews/artifacts; no hidden merge/live command. | Gate change one-shot, textual and audited. Multi-bot portfolios filter/group; no single global PASS plaque. |
| **24 Release Detail** — absent/planned | Проверить manifest, reviews, artifacts и authority boundary. | Release context; scope/commit → blockers → manifest → checks/reviews → Owner decision audit. | Draft, stale/missing artifact, disagreement, ready for Owner review, accepted/rejected; capital unchanged. | Copy artifact/hash, compare version, permitted Owner action in dedicated confirmation. | Diff expansion and focus return; no success confetti. Large manifests searchable with lazy sections. |
| **25 Versions** — partial build utility mock | Compare, promote or rollback typed versions within granted authority; primary action — compare. | Bot/Delivery → Versions; current/draft → diff → validation/evidence → history. | Draft, validated, failed, released, archived, incompatible, rollback unavailable. | Compare, tag/archive, open evidence; promotion/rollback explains authority and consequences. | Diff highlighting only. Large histories paginated and branchable without horizontal card strip. |
| **26 Logs / Events** — utility mock | Искать structured events с bot/run correlation; primary action — filter/open event. | Observability → Logs; query/freshness → event stream → contextual inspector. | Empty, streaming future-only, paused, stale, partial source, parse error. | Saved queries, columns, copy correlation ID, open bot/run/incident. Tooltips define source/retention. | No decorative ticker; new rows do not steal focus. Virtualization, pause/follow controls, compact density. |
| **27 Strategy Journal** — absent/planned | Зафиксировать hypothesis, decision и outcome без изменения mandate. | Research → Journal; recent/open hypotheses → entry → linked evidence/outcomes. | Draft, reviewed, superseded, outcome pending/known, missing link. | New draft, link run/release, compare hypotheses; tooltips distinguish note from evidence. | Autosave indicator only, no game reward. Long journals searchable/tagged and paginated. |

## 7. Platform, settings и extensibility

| # / экран / статус | Purpose и primary action | Navigation и content hierarchy | States | Menus и tooltips | Microinteractions, animation и scaling |
|---|---|---|---|---|---|
| **28 Marketplace** — future | Найти templates/modules без скрытой authority; сейчас conceptual catalog. | Research → Marketplace; trust/compatibility → search/categories → item detail/evidence. | Future, unavailable, incompatible, deprecated, verified/unverified source. | Inspect metadata, preview, future install preflight; tooltip для publisher/version/capabilities. | Card hover допустим, install не празднуется до verification. Hundreds of items use search/filter/pagination. |
| **29 Integrations** — absent/planned | Управлять typed adapters и видеть health/capabilities, не торговый допуск. | Platform → Integrations; blocker/health → adapters → capability detail → audit. | Not configured, disabled, healthy-with-freshness, degraded, stale, error. | Configure/test only when supported; docs/logs/capabilities. Tooltips отделяют connectivity от Live authority. | Verified connectivity result one-shot. Grid becomes filterable table above ~12 adapters. |
| **30 Exchange Connections** — **BLOCKED / future** | Будущая проверка connectivity, scopes и freshness; сейчас prerequisites only. | Platform → Connections; blocked banner → required governance → conceptual connection inventory. | Blocked, no credentials, future disconnected/degraded/stale; never `Live enabled`. | Inspect requirements/docs only; disabled add/test explains blocker. | No green heartbeat without telemetry. Many accounts group by venue/workspace with dense rows. |
| **31 Secrets / API Keys** — **BLOCKED / future** | Будущий безопасный credential lifecycle без показа secret value; сейчас locked explanation. | Platform → Secrets; security boundary → metadata inventory → rotation/audit. | Blocked, absent, future active/expiring/revoked/error; secret value never returned. | Future add/rotate/revoke require re-auth/confirmation; copy secret forbidden after creation boundary. | No cosmetic motion; sensitive actions keep focus/audit. Large inventories searchable by owner/scope/expiry. |
| **32 Notifications** — mock utility | Настроить delivery, severity и acknowledgement; primary action — inspect preference/delivery state. | Observability → Notifications; global `More` лишь shortcut; critical delivery failures → channels → rules → history. | Disabled, configured, degraded, test pending/pass/fail, stale. | Channel/rule menus, permitted test, open linked alert. `LOCAL_SEEN` не меняет authoritative `ACKNOWLEDGED`; tooltip separates delivery from alert truth. | Test feedback one-shot; badge reflects only authoritative unacknowledged items. Rules use table at scale. |
| **33 Documentation** — prototype | Дать contextual contracts, runbooks и definitions; primary action — search/open topic. | Platform → Docs; global `More`/context help лишь shortcuts; search → runbooks → contracts → history/version. | Empty index, offline bundled docs, stale link, unavailable external doc. | Copy deep link, open source, report mismatch; tooltip shows version/commit. | Search highlight only. Tree/search scales independently; mobile uses single-pane drilldown. |
| **34 Settings** — absent/planned | Управлять workspace/UI preferences; risk/trading authority остаётся отдельно. | Platform → Settings; global `More` лишь shortcut; profile/workspace → appearance/accessibility → defaults → audit where needed. | Clean, dirty, validation error, saved, conflict, read-only. | Reset section, save/cancel dialog; tooltip states local vs shared setting. | Theme/density preview; save state not celebratory. Settings tree searchable for 20–50 modules. |
| **35 User / Profile** — static Owner card | Показать identity, preferences и security context; primary action — inspect/edit permitted preference. | Profile menu; identity → role/permissions summary → security/session → preferences. | Signed in/out future, stale identity, restricted, local Owner prototype. | Profile/settings/sign-out future; tooltips explain role without implying authority. | Menu/popover transitions only. Compact card on small screens; full security data on dedicated route. |
| **36 Permissions / Teams** — future | Будущий least privilege, approvals и separation of duties; сейчас conceptual/locked. | Platform → Access; security summary → people/roles → approvals → audit. | Future, no provider, read-only, pending invite, conflict, revoked. | Future inspect/assign/revoke with explicit confirmation; tooltip lists exact capabilities. | No role-change celebration. Large teams use searchable table and diffable permission sets. |
| **37 Future Modules / Registry** — concept | Зарегистрировать/discover module slots без переделки shell; primary action сейчас — inspect registry contract. | Platform → Modules; compatibility/blockers → installed/available → module detail → audit. | Empty, available, disabled, incompatible, loading failure, deprecated. | Enable/configure only in future authority model; inspect routes/capabilities/version. | Module appearance uses stable icon fallback, not silent workshop sprite. 5 modules may show flat list; 20 grouped; 50 searchable/collapsible with favorites/recent. |

## 8. System screens и shared overlays

Они не заменяют 37 product screens, но обязательны для shell:

- route-level loading с сохранённым shell и понятным scope;
- 404/unknown module с search, recent и безопасным возвратом;
- access denied с причиной и без disabled mystery control;
- offline/stale/partial-data banner, который не перекрывает critical content;
- global command palette, entity switcher, alerts tray и help drawer;
- confirmation dialog только для действительно consequential allowed action;
- unsaved-changes dialog с точным перечислением затронутого scope.

## 9. Приоритет для UI-022-002

Следующий slice не реализует все 37 screens. Минимальная vertical foundation:

1. typed module/screen registry и route-menu parity;
2. новый destination `Operations` рядом с сохранённым `Farm`;
3. read-only Operations roster с search, filters, composite state, provenance и
   building deep link;
4. explicit `More` вместо скрытия mobile destinations;
5. общие `SafetyStrip`, `CompositeState`, `EvidenceStamp`, `Freshness` и
   empty/loading/error/stale states;
6. fixtures/checks для 5/20/50 modules и 5/20/100+ bots;
7. никакого backend, connectivity, Paper/Live или финансового действия.

### 9.1 Read-only data seam

UI-022-002 не подключает backend, но обязан использовать injected repository,
а mock adapter — реализовывать тот же contract:

```ts
interface BotFarmReadRepository {
  listBots(query: BotListQuery, cursor?: string): Promise<BotListPage>;
  listModules(query: ModuleListQuery, cursor?: string): Promise<ModuleListPage>;
  getBot(botId: string): Promise<BotSnapshot>;
  getSafetySnapshot(scope: ScopeRef): Promise<SafetySnapshot>;
}
```

Каждая page/snapshot несёт `source`, `asOf`, freshness и scoped
`partialErrors`; list response имеет bounded `limit` и `nextCursor`. Search,
filters, sort, density и selected building живут в URL. Direct bot route вызывает
`getBot`, а не загружает весь fleet. Mutation methods, optimistic gates,
client-side authority и обязательная all-in-one snapshot загрузка запрещены.

### 9.2 Normative scale evidence

- fixtures: 5/20/50 modules и 5/20/100/500 bots;
- 20 modules: districts/clusters + selected inspector; 50: aggregate districts
  + search/jump, без 50 detailed buildings в DOM;
- Farm не рендерит capacity как N empty slots и ограничивает representative NPC
  с явным `+N`;
- Operations имеет не более 120 rendered rows с overscan на fixture 500,
  сохраняет keyboard focus/selection и URL query;
- 360 px, 200% zoom, keyboard-only, screen-reader composite state,
  forced-colors/AA, 44 px targets и explicit mobile `More` проверяются отдельно;
- zero ambient loops в Operations и reduced-motion.

До отдельного Owner gate `Paper Trading`, `Live Gate`, `Live Monitoring`,
`Exchange Connections` и `Secrets / API Keys` остаются **BLOCKED/LOCKED**.
