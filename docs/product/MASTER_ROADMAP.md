# AI Trading Operating System — Living Master Roadmap

Status: **AUTHORITATIVE SEQUENCING V1 — DOCUMENTATION ONLY**

Companion semantics: `docs/product/PRODUCT_MASTER_SPEC.md`

Machine bootstrap: `docs/product/PRODUCT_GRAPH_BOOTSTRAP.toml` (**non-operational**)

Current capital state: **Paper / Limited Live / Live = LOCKED; `capital_authority = false`**

This roadmap sequences product value and control growth. It does not schedule work, activate a factory stage, create a runtime registry, or grant authority. Dates and capacity are not promises; dependencies, evidence and Owner decisions govern movement.

## 1. Roadmap rules

1. Build a useful consumer before generalized infrastructure for hypothetical consumers.
2. Increase security and operational control before, but proportionally to, authority.
3. Keep one active epic and one writer in any future autonomous Software Factory cadence.
4. Do not advance a dependency after FAIL; stop affected progress at `NEEDS_OWNER`.
5. Derive DONE from referenced evidence, never an estimate or percentage.
6. Preserve the three pipelines and their typed handoffs.
7. Maintain one future canonical Product Graph. Markdown, UI and the bootstrap are projections or migration inputs.
8. A Wave opens capability; it never implicitly opens the next authority level.

## 2. Current, next, future and locked

| Horizon | State |
|---|---|
| **CURRENT** | W0 development foundation; FACTORY-001A is accepted at `bd0027c316087a11193ca6662c27861adc87030f` by current Owner direction. Existing registry/scheduler behavior remains unchanged. |
| **NEXT** | W1 Product OS: migrate the bootstrap toward one canonical Product Graph, Living Roadmap, Owner HQ contract/read model, core domain model and controlled Software Factory interfaces. |
| **FUTURE** | W2–W6 offline knowledge, bot, research, proving, risk and release value; W7–W12 remain dependency- and authority-gated. |
| **LOCKED** | FACTORY-001B–001E, Paper, Limited Live, Live, credentials, exchange/broker activation, orders and capital authority. |

`docs/owner/CURRENT_STATE.md` and `factory/registry.toml` retain an older `REVIEW` snapshot for FACTORY-001A. This roadmap records the later Owner-accepted baseline but does not modify those runtime artifacts.

## 3. Wave dependency summary

```text
W0 DEVELOPMENT FOUNDATION
└─ W1 PRODUCT OS
   ├─ W2 KNOWLEDGE PLATFORM
   │  └─ W3 BOT & STRATEGY CORE
   │     └─ W4 RESEARCH INTELLIGENCE
   │        └─ W5 PROVING GROUND
   │           └─ W6 RISK & RELEASE + bounded operations-safety prerequisite
   │              └─ W7 PAPER TRADING (Owner-gated, locked)
   │                 └─ W8 LIMITED LIVE (Owner-gated, locked)
   │                    └─ W9 PORTFOLIO OS (shadow/advisory first)
   │                       └─ W10 OPERATIONS CENTER (scaled unification)
   │                          └─ W11 EVOLUTION ENGINE
   │                             └─ W12 SELF-IMPROVING TRADING ORGANIZATION
   └─ UNKNOWN FRONTIER feeds proposals/experiments into governed waves
```

Some capabilities have earlier enabling slices: W6 MUST establish bounded runtime-safety observation before W7. W10 is the scaled, fleet-wide professional Operations Center, not the first observability capability.

## 4. Wave contracts

### W0 — DEVELOPMENT FOUNDATION

- **Status:** `DONE / CURRENT`.
- **Goal:** establish the versioned repository, governance, tests, CI and accepted deterministic FACTORY-001A planning baseline.
- **Major capabilities:** existing repository and CI; governance/approval/risk contracts; deterministic registry validation, preflight, task selection, plan/report and current daily scheduler; accepted UI product-direction concepts.
- **Dependencies:** none inside this roadmap.
- **Definition of DONE:** current Owner direction accepts FACTORY-001A at exact HEAD `bd0027c316087a11193ca6662c27861adc87030f`; focused tests, independent review, security review and governed Ubuntu quality gates are reported passed; current authority remains bounded.
- **Authority impact:** none beyond accepted FACTORY-001A deterministic planning behavior. No writer, Git delivery or trading authority.
- **Major risks:** stale snapshot language being mistaken for current Owner direction; reopening frozen historical work; treating the UI prototype as operational truth.
- **Explicit non-goals:** redesign FACTORY-001A; V13/PM V3/external trust-root work; FACTORY-001B; trading execution.
- **What becomes possible afterward:** authoritative product semantics and a Living Roadmap can be designed on a stable baseline.

### W1 — PRODUCT OS

- **Status:** `NEXT / PLANNED`; implementation requires approved W1 work items.
- **Goal:** create the minimum product operating model that lets one Owner see, decide and trace product evolution.
- **Major capabilities:** canonical Product Graph contract and migration from the bootstrap/current factory registry; Living Roadmap projection; core domain IDs/version semantics; Owner HQ read model and 30-second attention hierarchy; World/Operations shared query model; controlled Software Factory interfaces; Product Change classification; typed decision/blocker/proposal/evidence links.
- **Dependencies:** W0.
- **Definition of DONE:** one canonical graph is designated; bootstrap migration/reconciliation is complete and duplicate writable truth is prohibited; all node/dependency validations pass; Owner HQ scenarios expose running/building/blocked/decisions/bots/versions/risk/evidence/research/experiments/evolution/alerts from source-linked state; dual views share IDs, filters, timestamps and authority; no control exceeds approved offline product authority.
- **Authority impact:** product-change coordination remains within approved Tasks/WUs. FACTORY-001B–001E and capital stay locked.
- **Major risks:** Product Graph, Markdown, factory registry and UI diverge; HQ invents aggregate truth; premature generalized control plane.
- **Explicit non-goals:** coding-agent execution, three-WU cadence activation, backend trading controls, capital-grade signing and domain platform implementation.
- **What becomes possible afterward:** every later capability can be planned, traced, displayed and governed without a second roadmap truth.

### W2 — KNOWLEDGE PLATFORM

- **Status:** `PLANNED`.
- **Goal:** make diverse knowledge and historical signals safely admissible, provenance-bearing, versioned and assignable per bot.
- **Major capabilities:** Knowledge Universe/Agent Academy; source/item/pack/profile versions; `KnowledgeSourceAdapter` and `SignalSourceAdapter`; raw/normalized/derived lineage; licensing/consent/retention/quarantine/revocation/conflict controls; temporal dataset manifests; Telegram TEACH FROM SIGNALS; open-ended source registry; Knowledge Graph indexing.
- **Dependencies:** W1 canonical IDs/graph and read-model rules.
- **Definition of DONE:** at least one non-Telegram and one Telegram historical source can produce deterministic, versioned, provenance-complete offline artifacts; raw Telegram history and extracted `ENTRY/STOP/TP/TIME/DIRECTION/RESULT/CONTEXT` remain traceable; bot-specific profile versions can be defined independently; assignment never claims learned/profitable/authorized behavior; FOLLOW SIGNALS remains locked.
- **Authority impact:** offline knowledge admission/curation only. New sensitive source classes can require Product Change Level C; no runtime signal or broker authority.
- **Major risks:** poisoning, copyright/licensing/consent gaps, source conflict, revision/look-ahead leakage, Telegram becoming universal architecture, assigned knowledge being shown as “trained”.
- **Explicit non-goals:** complete BotVersion binding (W3), strategy creation, fine-tuning by default, runtime Telegram following, credentials or execution.
- **What becomes possible afterward:** exact provenance-bearing knowledge profiles and datasets can feed bot/strategy construction and research.

### W3 — BOT & STRATEGY CORE

- **Status:** `PLANNED`.
- **Goal:** define durable bot identity and immutable composition of strategy, knowledge, risk, execution, model, evidence requirements and experience.
- **Major capabilities:** `TradingBot`, `BotVersion`, `Strategy`/`StrategyVersion`, exact `AgentKnowledgeProfileVersion` binding, a bounded Risk Tower mandate-authoring slice that derives `RiskMandateVersion` only from approved Owner/governance policy, `ExecutionPolicyVersion`, `EvidenceRequirementSetVersion`, optional model binding, experience cutoff, candidate-assembly manifest/compatibility, bot development organization and Bot Park inventory.
- **Dependencies:** W1 and W2.
- **Definition of DONE:** a candidate bot can be assembled with exact never-latest component references and an exact evidence-requirement set; component ownership and compatibility are validated; W3 mandate authoring grants no verdict or authority; behavioral change creates a new version/change-impact record; Bot Park shows canonical version bindings and independent state axes; cognitive workers cannot mutate released structure.
- **Authority impact:** offline candidate authoring only. A new market, venue, risk philosophy or authority remains Level C and locked.
- **Major risks:** mutable latest references; bot/worker identity collision; implicit retrieval/model drift; strategy and execution policy coupling; metaphors becoming ambiguous schemas.
- **Explicit non-goals:** proving engine, Paper, portfolio allocation, permanent LLM committees inside bots or live runtime.
- **What becomes possible afterward:** research can target explicit bot/strategy objects and proving can bind exact candidates.

### W4 — RESEARCH INTELLIGENCE

- **Status:** `PLANNED`.
- **Goal:** turn knowledge, market data and experience questions into reproducible, falsifiable research and strategy proposals.
- **Major capabilities:** Research Campus; typed question/brief/protocol/dataset/finding/hypothesis/experiment/result/proposal; complete experiment registry including null results; preregistration; point-in-time/availability-time data; sealed holdout and walk-forward roles; benchmark/uncertainty/multiple-testing/effective-sample controls; reproducibility bundles.
- **Dependencies:** W2 knowledge/data provenance and W3 target identities/version semantics.
- **Definition of DONE:** research output is versioned and reproducible within declared limits; data roles and temporal lineage are explicit; negative experiments remain visible; no holdout optimization; a `StrategyProposal` requires evidence and review and cannot auto-create a `StrategyVersion`.
- **Authority impact:** offline research only; AI researchers propose but cannot promote.
- **Major risks:** look-ahead, survivorship/selection/publication bias, HARKing, correlated samples, unregistered parameter searches, provider/model non-reproducibility and performance claims.
- **Explicit non-goals:** declaring profitability, live-equivalent evidence, strategy promotion or broad generalized ML infrastructure without a consumer.
- **What becomes possible afterward:** exact candidates can enter non-substitutable proving with defensible methodology.

### W5 — PROVING GROUND

- **Status:** `PLANNED`.
- **Goal:** produce distinct historical, temporal, synthetic/adversarial and methodology evidence for exact candidates.
- **Major capabilities:** Backtest Lab; Replay Hangar; Simulation Arena; independent robustness/methodology review; versioned venue/instrument/session profiles; execution assumption/fill-cost models; conservative/base/adverse scenarios; evidence applicability, comparability and reproducibility; impact-based re-proving.
- **Dependencies:** W3 immutable candidates and W4 research/evaluation contracts.
- **Definition of DONE:** each proving layer emits a typed version-bound report with inputs, assumptions, costs, uncertainty, limitations and reproduction data; no layer substitutes for another; failed/unknown material assumptions block affected claims; evidence invalidation works after behavior-relevant changes; reviewers have no unresolved BLOCKER/HIGH findings for an eligible candidate.
- **Authority impact:** offline evidence generation only; no result grants Paper or Live.
- **Major risks:** optimistic fills/costs, touched-limit-as-fill, double-counted costs, venue abstraction leakage, overfitting and “proved” being read as guaranteed return.
- **Explicit non-goals:** production-grade exchange runtime, credentials, order submission, Paper fills or live profitability claims.
- **What becomes possible afterward:** independent Risk Tower and Release HQ can make exact scope-bound eligibility decisions.

### W6 — RISK & RELEASE

- **Status:** `PLANNED`.
- **Goal:** promote exact offline candidates through non-waivable evidence/risk/review/Owner gates, with rollback and bounded safety observation ready before any Paper proposal.
- **Major capabilities:** the independent Risk Tower evaluation slice across strategy/bot/portfolio/execution/operational/capital scopes, consuming the exact W3 mandate and candidate; `ALLOW/LIMIT/BLOCK/REQUEST_OWNER`; Release HQ; release evidence/manifest; review/risk/Owner verdicts; evidence expiry/supersession/invalidation; rollback; bounded operations-safety read model for future Paper (runtime state, data/clock freshness, simulator reconciliation, alerts, incidents, audit, protection and rollback visibility).
- **Dependencies:** W5 and governance.
- **Definition of DONE:** an exact candidate can be promoted only to `RELEASED_OFFLINE` with complete valid evidence, independent reviews, risk verdict, explicit Owner decision and tested rollback compatibility; automation cannot raise limits; missing/stale/incompatible evidence fails closed; bounded safety observation is proven with offline fixtures; capital locks remain visible and effective.
- **Authority impact:** offline release only. Paper, Limited Live, Live and capital remain locked.
- **Major risks:** Owner approval being treated as a waiver; release scope inheriting capital authority; rollback omitting component compatibility; fake risk NORMAL without telemetry; future Paper proposed without observation/reconciliation.
- **Explicit non-goals:** Paper activation, real connections/positions/orders, capital allocation and broad fleet Operations Center.
- **What becomes possible afterward:** the Owner may separately evaluate a bounded Paper stage with prerequisites already observable.

### W7 — PAPER TRADING

- **Status:** `LOCKED / FUTURE OWNER GATE`.
- **Goal:** observe exact released candidates in a no-real-capital Paper environment under independent admission, risk and operations controls.
- **Major capabilities:** Paper-specific admission; simulator/broker contract; idempotent order-intent path; bounded retries; reconciliation; paper orders/fills/positions; fees/funding/slippage/latency assumptions; alerts/incidents/kill/rollback; unseen forward evidence; drift and calibration reports.
- **Dependencies:** W6, explicit Owner approval, Paper acceptance contract, security/risk review and proven bounded operations-safety observation.
- **Definition of DONE:** to be set by a future Owner-approved acceptance contract before activation; it MUST include deterministic safety failures, reconciliation, data freshness, monitoring, rollback, evidence retention and an adequate observation period. Paper evidence remains non-live-equivalent.
- **Authority impact:** currently none. Future Paper authority is environment-scoped and does not grant Limited Live or Live.
- **Major risks:** simulator optimism, credential/endpoint confusion, unobserved reconciliation failures, Paper results being treated as expected live return and automatic promotion pressure.
- **Explicit non-goals:** real-capital orders, Limited Live, Live or general multi-venue production infrastructure.
- **What becomes possible afterward:** only after future evidence and Owner decisions, a separate Limited Live candidate may be considered.

### W8 — LIMITED LIVE

- **Status:** `LOCKED / FUTURE OWNER LIVE GATE`.
- **Goal:** if separately approved, validate tightly bounded real-market operation with minimal authority and immediate protection/rollback.
- **Major capabilities:** owner-approved venue/account/credential model; hard capital/position/loss/exposure bounds; kill/reconcile/rollback; production observability; separation of duties; Paper-to-Pilot calibration; incident and recovery evidence.
- **Dependencies:** W7 PASS under a future contract, explicit Owner Live Gate, capital/security/risk architecture appropriate to actual authority, and no unresolved high findings.
- **Definition of DONE:** intentionally undefined until the Owner approves scope, market, venue, mandate and measurable acceptance. It cannot be inferred from this roadmap.
- **Authority impact:** currently zero. Any future bounded capital authority is Level C, explicit, revocable and non-inheriting.
- **Major risks:** capital loss, venue/account uncertainty, credential compromise, limit drift, reconciliation gaps, liquidity/capacity mismatch and false confidence from Paper.
- **Explicit non-goals:** automatic Live promotion, broad symbol/venue expansion or self-increasing limits.
- **What becomes possible afterward:** evidence may support a future Live candidate and joint multi-bot analysis; it does not guarantee either.

### W9 — PORTFOLIO OS

- **Status:** `LOCKED / PLANNED SHADOW-FIRST`.
- **Goal:** coordinate multiple independently proven bot versions under one explicit capital-pool model, beginning with advisory/shadow evidence.
- **Major capabilities:** CapitalPool/CapitalBook boundaries; manual/deterministic mandates and corridors; version-bound admission/suspension/removal/rollback; gross/net/contingent exposure; correlation/concentration/drawdown/risk contribution; shared capacity/liquidity; conflict/netting policy; joint replay/simulation and simultaneous-exit stress; shadow allocation proposals.
- **Dependencies:** multiple proven bots, W6 release/risk, W7/W8 evidence as applicable, Market & Data Hub, and minimum reconciled operational state. The mandated sequence places W9 after W8, but capital-bearing allocation remains independently gated.
- **Definition of DONE:** multiple exact versions have joint portfolio evidence; physical/logical capital boundaries are explicit; aggregates trace to reconciled sources and freshness; conflicts/capacity are visible; initial output is advisory/`SHADOW_ONLY`; no optimizer or UI implies capital authority.
- **Authority impact:** none in initial W9. Capital-bearing allocation requires a separate Level C Owner decision and operational prerequisites.
- **Major risks:** correlation convergence, cross-margin contagion, double-counted collateral/capacity, stale exposure, hidden gross risk, self-trading/conflicts, pro-cyclical allocator feedback.
- **Explicit non-goals:** premature portfolio optimization, invented numerical caps, silent netting or treating current BTC policy allocation as a multi-bot mandate.
- **What becomes possible afterward:** fleet-wide risk/attribution and scaled operations can use a coherent portfolio context.

### W10 — OPERATIONS CENTER

- **Status:** `LOCKED / FUTURE`.
- **Goal:** unify and scale professional runtime operations across bots, versions, portfolios, markets and incidents.
- **Major capabilities:** dense Operations View; fleet search/grouping/saved views; authoritative runtime/market/data freshness; exact versions; future positions/orders/PNL; pending/unknown/partial order states; reconciliation; alerts/incidents; acknowledgement authority; degradation/protection/rollback; execution quality; operational timeline and postmortems.
- **Dependencies:** W6 bounded safety primitives and the active environment capabilities from W7–W9.
- **Definition of DONE:** the Owner can triage critical/freshness/risk/authority/run/evidence state at fleet scale with complete aggregate-to-detail lineage; alert storms, incidents, reconciliation and rollback are scenario-tested; critical facets remain accessible at 5/20/100/500-bot scale; performance never outranks safety.
- **Authority impact:** observation/control authority is environment- and policy-scoped; this Wave itself does not grant Paper/Live/capital.
- **Major risks:** stale data appearing healthy, alert fatigue, unauthorized bulk actions, decorative UX delaying response, UI becoming a second truth and over-coupling to one venue.
- **Explicit non-goals:** granting new markets/capital, changing risk philosophy or replacing canonical domain owners with a dashboard database.
- **What becomes possible afterward:** trustworthy operational experience can feed a governed Evolution Engine.

### W11 — EVOLUTION ENGINE

- **Status:** `LOCKED / FUTURE`.
- **Goal:** convert product and bot experience into cited analyses, hypotheses, experiments and rollback-capable candidate versions.
- **Major capabilities:** experience datasets/cutoffs; drift and incident analysis; proposal registry; change-impact/evidence-compatibility; candidate construction routing; bounded adaptation-envelope proposal/evidence; before/after comparison and rollback linkage.
- **Dependencies:** W4–W6 evidence discipline and W10 trustworthy operational observations; W7+ when operational learning is used.
- **Definition of DONE:** every proposal traces from observation through experience and analysis; endogenous/policy-selected data is labeled; structural changes always return to candidate/proving/release; invalidated evidence is visible; runtime adaptation, if ever allowed, remains inside an approved proven envelope.
- **Authority impact:** proposal/experiment authority only by default. No unrestricted self-modification or automatic promotion.
- **Major risks:** self-confirming feedback, data leakage, chasing noise/regimes, provider drift, evidence reuse and adaptation escaping its envelope.
- **Explicit non-goals:** live code rewriting, self-granted limits, continuous fine-tuning by default or direct experience-to-release promotion.
- **What becomes possible afterward:** the organization can learn continuously while keeping evidence, gates and rollback intact.

### W12 — SELF-IMPROVING TRADING ORGANIZATION

- **Status:** `LOCKED / LONG-TERM`.
- **Goal:** integrate controlled organizational learning across product, knowledge, research, bots, proving, operations and evolution under one Owner.
- **Major capabilities:** portfolio of specialized cognitive workers; knowledge/research/evidence reuse with contamination controls; cross-bot and product learning; organization-level proposals; resource/budget routing; health of the development/research/release system; continuous but gated improvement loops.
- **Dependencies:** W1–W11 proven in their actual authority scopes and explicit Owner approval for any new authority.
- **Definition of DONE:** to be defined by future Owner-approved contracts; at minimum the full North Star cycle is traceable, governed, reversible and independently reviewed, with no direct path from AI proposal to capital authority.
- **Authority impact:** none automatically. Organizational autonomy, product writes and capital authority remain separate gates.
- **Major risks:** correlated agent errors, goal drift, hidden shared context, circular self-evaluation, cost sprawl, concentrated provider dependence, automation bias and authority creep.
- **Explicit non-goals:** an unconstrained autonomous organization, permanent LLM committees in bots, self-approval, self-funding or removal of the Owner.
- **What becomes possible afterward:** further evolution proceeds through explicit frontier proposals rather than a presumed final architecture.

### UNKNOWN FRONTIER

- **Status:** `UNKNOWN_FRONTIER`.
- **Goal:** make uncertainty visible, traceable and researchable.
- **Major capabilities:** frontier items with provenance, impact, trigger, owner, proposed discovery/experiment and promotion path.
- **Dependencies:** none for recording; promotion depends on evidence and Product Change classification.
- **Definition of DONE:** not applicable as a whole. Each frontier item can be superseded, rejected, promoted to proposal/experiment, or remain unknown with history.
- **Authority impact:** none.
- **Major risks:** speculative scope presented as commitment; unknown regulatory/data/licensing constraints; premature platform work.
- **Explicit non-goals:** filling the frontier with dates, fake precision or implementation promises.
- **What becomes possible afterward:** the architecture absorbs new methods, providers, sources, markets and constraints without rewriting its core truth/authority model.

Initial frontier categories include new markets/venues/brokers/asset classes; causal/off-policy evaluation; synthetic-data validity; model/provider portability; fine-tuning economics; bounded runtime adaptation; teams/workspaces/separation of duties; regulatory/tax/retention obligations; multi-venue routing; portfolio optimization; factor/clone detection; and future plugin/module compatibility.

## 5. Software Factory autonomy roadmap

| Stage | Meaning | State |
|---|---|---|
| FACTORY-001A | deterministic planning baseline | `CURRENT / ACCEPTED` |
| FACTORY-001B | controlled coding-agent execution | `LOCKED / NEEDS_OWNER` |
| FACTORY-001C | three controlled Work Units/day | `LOCKED` |
| FACTORY-001D | controlled Git delivery | `LOCKED` |
| FACTORY-001E | real-time Owner UI | `LOCKED` |

Future intended cadence, **specification only**:

- timezone `Europe/Moscow`;
- Mon–Thu: Work Units at 10:00, 14:00 and 18:00;
- Friday: 1–2 Work Units plus architecture/integration review and weekly report;
- weekend paused;
- `max_active_epics = 1`;
- `max_work_units_per_day = 3`;
- `max_parallel_writers = 1`;
- `max_correction_loops_per_unit = 2`;
- sequential execution; dependent WU starts only after previous PASS;
- FAIL blocks dependants; `NEEDS_OWNER` stops affected autonomy;
- no artificial work for an unused slot.

This does not modify the current one-task FACTORY-001A scheduler.

## 6. Prioritization guardrails

- Do not build capital-grade cryptographic authorization during W2 knowledge work.
- Do not build a portfolio optimizer before multiple proven bots and joint evidence exist.
- Do not build Live infrastructure before Paper is separately approved and proved.
- Do not make full Operations Center scale a prerequisite for offline research; do build the bounded observation/reconciliation consumer before Paper.
- Do not generalize an adapter until at least one concrete consumer and native-semantics escape hatch exist.
- Do not create a domain, lifecycle stage, market, exchange/broker, credential model, risk philosophy, global UX paradigm or capital stage without a Product Change Level C Owner Gate.

## 7. Living-roadmap maintenance contract

Until W1 designates the canonical Product Graph, changes to this roadmap and the bootstrap are documentation work under an approved Work Unit and MUST remain consistent. After migration, canonical state changes occur only in the Product Graph; this Markdown becomes a reviewed, versioned narrative projection. Every status change references evidence or a decision, every dependency resolves, and every superseded object remains auditable.

No duplicate independently writable roadmap truth is permitted.
