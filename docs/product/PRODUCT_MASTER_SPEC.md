# AI Trading Operating System — Product Master Spec

Status: **AUTHORITATIVE PRODUCT SEMANTICS V1 — DOCUMENTATION ONLY**

Stage: **4/5 — Product Master Spec + Living Roadmap**

Owner model: **one Owner**

Baseline: **FACTORY-001A accepted at `bd0027c316087a11193ca6662c27861adc87030f` by the current Owner direction**

Capital state: **Paper = LOCKED; Limited Live = LOCKED; Live = LOCKED; `capital_authority = false`**

This document defines the product architecture of the AI Trading Operating System. It does not implement a product domain, alter `factory/registry.toml`, change FACTORY-001A scheduling, grant a credential, connect an exchange, submit an order, or grant capital authority. The older `docs/owner/CURRENT_STATE.md` and `factory/registry.toml` snapshots still say FACTORY-001A is in `REVIEW`; the current Owner direction is later and declares the baseline accepted for this stage. This document records that fact without changing the existing runtime registry or its vocabulary.

## 1. Contract and interpretation

The words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative. Examples and metaphors explain intent but are not storage schemas or authority grants. A future implementation MUST use versioned acceptance contracts and evidence; this Master Spec does not invent numerical trading, performance, portfolio, or operational thresholds.

Source precedence for this product stage is:

1. current Owner direction;
2. this Product Master Spec;
3. governance and approved contracts;
4. the future canonical Product Graph;
5. approved Task and Work Unit contracts;
6. verified implementation and evidence;
7. ordinary documents and historical comments.

Where repository-wide governance has higher safety authority, it remains binding. A conflict MUST stop the affected work and become a `NEEDS_OWNER` decision; no agent may choose the financially riskier interpretation.

### 1.1 Normative requirement map

| ID | Requirement |
|---|---|
| `PMS-REQ-001` | Preserve the exact North Star and the complete product cycle. |
| `PMS-REQ-002` | Keep Software Factory, Trading Agent Factory, and Trading Operations separate, with typed handoffs. |
| `PMS-REQ-003` | Define the complete Product Galaxy and ownership of canonical entities. |
| `PMS-REQ-004` | Let one Owner understand material system state in about 30 seconds. |
| `PMS-REQ-005` | Provide World and Operations views over one canonical truth. |
| `PMS-REQ-006` | Separate temporary cognitive AI workers from persistent trading bots. |
| `PMS-REQ-007` | Route provider-neutral models through constrained, auditable roles. |
| `PMS-REQ-008` | Support open-ended, provenance-bearing, per-bot knowledge. |
| `PMS-REQ-009` | Keep TEACH FROM SIGNALS separate from FOLLOW SIGNALS. |
| `PMS-REQ-010` | Support multiple learning and memory modes without defaulting to fine-tuning. |
| `PMS-REQ-011` | Make bot, strategy, knowledge, risk, execution, model, evidence, and experience bindings explicit and versioned. |
| `PMS-REQ-012` | Use an evidence-gated lifecycle and independent state axes. |
| `PMS-REQ-013` | Derive truth-changing state from typed evidence with lineage, validity, and invalidation. |
| `PMS-REQ-014` | Separate research, hypotheses, experiments, strategies, and strategy versions. |
| `PMS-REQ-015` | Keep Backtest, Replay, Simulation, and independent review non-substitutable and microstructure-aware. |
| `PMS-REQ-016` | Separate strategy, bot, portfolio, execution, operational risk, release, and capital authority. |
| `PMS-REQ-017` | Permit controlled evolution only through observable, rollback-capable candidate versions. |
| `PMS-REQ-018` | Define one traceable Product Graph and a non-operational bootstrap migration path. |
| `PMS-REQ-019` | Keep product-change authority distinct from capital authority and specify the future factory cadence without activating it. |
| `PMS-REQ-020` | Preserve all current locks and proportional security. |

## 2. North Star and core loop

> “AI Trading Operating System, в которой один Owner управляет
> виртуальной организацией ИИ-агентов, самостоятельно исследующей рынки,
> принимающей знания из разных источников, создающей и обучающей
> индивидуальных торговых агентов, разрабатывающей стратегии,
> доказывающей их качество, выпускающей контролируемые версии,
> эксплуатирующей их под жёсткими risk/authority gates и непрерывно
> предлагающей эволюцию продукта и стратегий.”

The core conceptual loop is:

```text
OWNER INTENT
→ KNOWLEDGE
→ RESEARCH
→ HYPOTHESIS
→ STRATEGY
→ BOT
→ PROVE
→ RELEASE
→ OPERATE
→ OBSERVE
→ LEARN
→ EVOLVE
↺
```

The loop is not an automatic promotion conveyor. Every arrow is a typed handoff; evidence, policy, and Owner gates can stop it. Observation may create a hypothesis, but it may not silently mutate a released bot.

## 3. Product principles

1. **One Owner, legible control.** The Owner sees truth, exceptions, decisions, evidence, and authority without reading raw logs for ordinary understanding.
2. **State changes require evidence.** UI gestures, AI confidence, decoration, schedules, or an Owner wish cannot manufacture technical or epistemic PASS evidence.
3. **One truth, many projections.** Canonical domain objects have one owner. HQs, maps, graphs, indexes, dashboards, and read models project them.
4. **Immutable version binding.** A released version never means “latest”. Behavior-relevant inputs are pinned.
5. **Fail closed.** Malformed or stale inputs, unsupported capabilities, unknown account state, missing protection, incomplete responses, duplicate events, uncertain reconciliation, or invalid evidence cannot create new authority or orders.
6. **Security proportional to authority.** Controls grow before authority grows, not years before a consumer exists.
7. **Product value before speculative infrastructure.** Build the knowledge, research, bot, and proving consumers before capital-grade control infrastructure or portfolio optimization.
8. **AI proposes; governed workflows decide.** LLMs may perform cognitive work but do not sit in the live order-decision path, grant authority, promote themselves, or rewrite a running bot.
9. **Historical evidence is not a return promise.** Backtest, replay, simulation, and future Paper evidence are bounded evidence, never proof of live profitability.
10. **Rollback is part of release.** Structural changes produce candidates; every promoted version has an applicable rollback target.

## 4. Three pipelines and their handoffs

```text
Software Factory
      ↓ versioned product capability release
AI Trading OS
      ↓ governed product services
Trading Agent Factory
      ↓ released, evidence-bound trading agents
Trading Operations
      ↓ bounded market interaction (future and locked)
Markets
      ↑ observations / outcomes
Experience and Evolution
```

| Pipeline | Owns | Inputs | Outputs | Handoff and authority boundary |
|---|---|---|---|---|
| **Software Factory** | Changes to the AI Trading OS: code, product capabilities, infrastructure, UI, integrations, tests, product versions | Product Graph work, approved Task/WU, product requirements, evidence | Versioned product capability releases and delivery evidence | A product release can enable an offline product capability. It does not create a bot release or capital authority. |
| **Trading Agent Factory** | Bot research, bot identity/version assembly and exact strategy/knowledge/risk/execution/model composition | Released OS capabilities, versioned component artifacts, mandates and evidence requirements | `BotVersion`, `CandidateAssembly` and `ReleaseCandidateRequest` | Release HQ alone creates the canonical candidate and can promote it. `RELEASED_OFFLINE` is not Paper or Live. |
| **Trading Operations** | Deployments, runs, reconciled runtime state, incidents, observations, and future market interaction | Explicit `ReleasedVersion`, environment admission, risk verdict, Owner decision, operational readiness | Runtime observations, audit events, incidents, and experience data | Consumes only allowed versions. It cannot write structural changes back into a running bot; feedback returns through Experience and Evolution. |

Shared words do not collapse ownership. A Software Factory “release” is a product version; a Trading Agent Factory “release” is an exact bot version; a Trading Operations “run” is an environment-scoped execution of that released version.

## 5. Canonical truth, projections, and data ownership

Every canonical entity MUST have one write owner. Other domains reference immutable IDs or consume versioned read models.

| Canonical owner | Canonical objects | Important consumers |
|---|---|---|
| Product Galaxy / Living Roadmap | `Product`, `Domain`, `Wave`, `Epic`, `Capability`, `Task`, `WorkUnit`, `Dependency`, `Decision`, `Proposal`, `Blocker`, graph evidence links | Owner HQ, Software Factory, World and Operations views |
| Software Factory | Product change plan, build/test/run artifacts, product release | Product Graph, Release evidence views |
| AI Organization | `RoleDefinition`, `WorkOrder`, `WorkerRun`, `ModelRoutingRecord`, `ModelRoutingPolicyVersion`, typed worker output | All intellectual-work domains |
| Knowledge Universe | `KnowledgeSource`, `KnowledgeItem`, `KnowledgePackVersion`, `AgentKnowledgeProfileVersion`, provenance | Research, Strategy, Trading Agent Factory |
| Research Campus | Research questions/protocols/datasets/findings/hypotheses/research experiments and `StrategyProposal` | Strategy Lab, Knowledge Graph, Evolution Engine |
| Strategy Lab | `Strategy`, immutable `StrategyVersion` | Trading Agent Factory, proving labs |
| Trading Agent Factory | Durable `TradingBot`, immutable `BotVersion`, `ExecutionPolicyVersion`, `CandidateAssembly` / `ReleaseCandidateRequest` | Release HQ, Bot Park |
| Proving domains | `BacktestRun`, `ReplayRun`, `SimulationRun`, robustness/reproducibility reports and their evidence artifacts | Reviewers, Risk Tower, Release HQ |
| Risk Tower | a bounded W3 mandate-authoring slice owns `RiskMandateVersion`; the W6 independent-evaluation slice owns risk evaluations and `RiskVerdict` | Trading Agent Factory, proving domains, Release HQ, Portfolio HQ, Operations |
| Release HQ | `ReleaseCandidate`, `ReleaseEvidenceSetVersion` (an immutable aggregation of proving/review/risk evidence references), release manifest, promotion record, `ReleasedVersion`, rollback target | Bot Park, Operations, Owner HQ |
| Market & Data Hub | Market/data observations, dataset manifests, venue/instrument/session profiles, adapter provenance | Research, proving, Operations |
| Operations Center | Deployment/run, reconciled order/position state when authorized, runtime observation, alert, incident | Owner HQ, Portfolio HQ, Experience |
| Experience / Memory System | Versioned experience datasets and scoped memory records | Research, Evolution, individual bots within allowed scope |
| Evolution Engine | Evolution observations, analyses and proposals | Product Graph, Research Campus, Trading Agent Factory |
| Portfolio HQ | Portfolio definitions, shadow/advisory allocation proposals, aggregate evidence; future decisions only under separate authority | Risk Tower, Owner HQ, Operations |

`Owner HQ`, `Bot Park`, World View, and Operations View are projections. `Knowledge Graph` is a relationship index over canonical IDs and version references; it MUST NOT copy mutable payloads into a second truth. The bootstrap TOML is a checked migration input, not a writer or runtime registry.

Ownership follows the artifact through explicit handoffs: Research Campus owns and submits a `StrategyProposal`; Strategy Lab consumes it and owns any resulting `StrategyVersion`. Trading Agent Factory owns `ExecutionPolicyVersion`, `EvidenceRequirementSetVersion`, `CandidateAssembly` and `ReleaseCandidateRequest`; Release HQ alone creates and owns the canonical `ReleaseCandidate`. Proving domains own their individual result/evidence artifacts; Release HQ owns only the immutable `ReleaseEvidenceSetVersion` that aggregates their exact references for a candidate. AI Organization owns `ModelRoutingPolicyVersion`. Risk Tower’s W3 authoring slice owns mandate versions derived from exact Owner-approved policy; its W6 evaluation slice consumes candidates/evidence and owns verdicts. Any future dedicated execution-policy domain requires a separately approved migration. A transfer of ownership requires a typed create/accept event, never two writable copies.

Dependencies have distinct semantics. A **schema/interface dependency** lets an earlier Wave define and validate a versioned contract without requiring the later service to exist. A **readiness dependency** blocks start until an upstream capability is DONE. **Artifact/evidence**, **operational-service**, and **authority** dependencies respectively require exact inputs, a working service, or an explicit gate. Narrative domain references MUST identify which kind applies; only actual readiness edges determine Wave ordering.

## 6. Product Galaxy domain catalog

The authority labels below describe current product-stage authority, not future entitlement. `SPEC_ONLY` means this document defines a seam. `OFFLINE_FUTURE` means a later approved work item may implement an offline capability. `CAPITAL_LOCKED` means any capital-bearing activation requires a separate Level C Owner gate.

### D01 — Owner HQ

- **Purpose:** the solo Owner’s 30-second command and decision surface.
- **Inputs:** canonical state projections, attention items, evidence changes, decisions, locks, alerts and incidents.
- **Outputs:** scoped Owner decisions, approved intent, prioritization, and drill-down navigation; no evidence is created by display actions.
- **Key entities:** `OwnerAttentionItem`, `OwnerDecision`, `OwnerIntent`, `DecisionRequest`, saved view.
- **AI roles:** requirements analyst, performance analyst, evolution analyst summarize with provenance and no authority inflation.
- **Owner interaction:** decide, defer, reject, request evidence, navigate, and inspect source artifacts.
- **Dependencies:** Product Graph and read models from every material domain.
- **Evidence produced:** signed/auditable decision record and decision rationale when the Owner acts.
- **Future extensibility:** additional workspaces, delegates, separation of duties, and multi-monitor layouts.
- **Authority:** `SPEC_ONLY`; navigation is non-mutating and future mutations remain permission/gate controlled.

### D02 — Product Galaxy / Living Roadmap

- **Purpose:** one dependency-aware map of what the product is, why it exists, and how it evolves.
- **Inputs:** Owner intent, accepted architecture, proposals, evidence, dependencies, blockers, and decisions.
- **Outputs:** prioritized graph, traceability, current/next/future/locked projections, and roadmap views.
- **Key entities:** product hierarchy plus `Dependency`, `Decision`, `Proposal`, `Experiment`, `Blocker`, `Evidence`.
- **AI roles:** requirements analyst, system architect, product/evolution analyst.
- **Owner interaction:** approve Level C changes, sequence work, resolve blockers, accept or reject proposals.
- **Dependencies:** governance, Software Factory evidence, all domain proposals.
- **Evidence produced:** versioned graph snapshot, validation report, decision lineage.
- **Future extensibility:** new node/edge types and domains without a schema rewrite; compatibility/migration rules required.
- **Authority:** `SPEC_ONLY`; the bootstrap is explicitly non-operational until W1 migration.

### D03 — Software Factory

- **Purpose:** build and evolve the AI Trading OS itself.
- **Inputs:** approved Product Graph work, spec/acceptance contracts, code, reviews, and evidence.
- **Outputs:** code, capabilities, infrastructure, UI, integrations, tests, and product versions.
- **Key entities:** `ProductChange`, `WorkUnit`, `Build`, `TestRun`, `ProductRelease`.
- **AI roles:** requirements analyst, architect, implementer, test engineer, independent reviewers, release verifier.
- **Owner interaction:** approve Level C work and future authority; inspect plans, gates, failures, and releases.
- **Dependencies:** governance and Product Graph.
- **Evidence produced:** diff, exact commands/results, review verdicts, hashes, CI and release record.
- **Future extensibility:** controlled coding execution, cadence, Git delivery, and real-time Owner UI in separately gated stages.
- **Authority:** current FACTORY-001A baseline only; FACTORY-001B–001E remain locked.

### D04 — AI Organization

- **Purpose:** coordinate temporary cognitive specialists that create typed intellectual artifacts.
- **Inputs:** work orders, role contracts, mandatory context, budgets, tools and memory scopes.
- **Outputs:** typed proposals, analyses, reviews, questions and evidence references.
- **Key entities:** `RoleDefinition`, `WorkOrder`, `WorkerRun`, `WorkerArtifact`, `ModelRoutingRecord`.
- **AI roles:** every cognitive role named in this document.
- **Owner interaction:** define authority/budget boundaries, inspect runs, resolve escalations, and approve governed decisions.
- **Dependencies:** Model Router, memory scopes, Product Graph work.
- **Evidence produced:** auditable run record, context manifest, routing record, output validation and verdict.
- **Future extensibility:** providers, roles, tools and organizational patterns through contracts.
- **Authority:** `OFFLINE_FUTURE`; workers cannot grant trading or product Level C authority.

### D05 — Agent Academy / Knowledge Universe

- **Purpose:** admit, curate, version and assign open-ended knowledge to bots individually.
- **Inputs:** courses, channels, messages, books, notes, PDFs, documents, web research, market research, historical trades, Owner knowledge, datasets, strategy descriptions and unknown future sources.
- **Outputs:** curated items, immutable knowledge-pack versions, bot-specific profile versions, provenance and quality/conflict records.
- **Key entities:** `KnowledgeSource`, `KnowledgeItem`, `KnowledgePack`, `KnowledgePackVersion`, `AgentKnowledgeProfile`, `AgentKnowledgeProfileVersion`, `KnowledgeProvenance`.
- **AI roles:** Knowledge Curator, Bot Researcher, Red Team.
- **Owner interaction:** admit/quarantine/revoke sources, assign profiles, approve sensitive or conflicting knowledge.
- **Dependencies:** source adapters, Knowledge Graph, Market & Data Hub where applicable.
- **Evidence produced:** raw/normalized/derived lineage, admission decision, licensing/consent status, checksums, quality and conflict assessments.
- **Future extensibility:** new source/media types through `KnowledgeSourceAdapter`; Telegram is only one adapter.
- **Authority:** `OFFLINE_FUTURE`; assignment does not prove learning or authorize following/execution.

### D06 — Research Campus

- **Purpose:** turn questions and evidence into falsifiable findings and strategy proposals.
- **Inputs:** knowledge, point-in-time datasets, market observations, experience analyses and Owner questions.
- **Outputs:** research artifacts, hypotheses, experiments/results and `StrategyProposal`.
- **Key entities:** `ResearchQuestion`, `ResearchBrief`, `ResearchProtocol`, `ResearchDataset`, `ResearchFinding`, `Hypothesis`, `Experiment`, `ExperimentResult`, `StrategyProposal`.
- **AI roles:** Bot Researcher, quant researcher, Quant Reviewer, Market Microstructure Reviewer, Red Team.
- **Owner interaction:** prioritize questions, approve costly/sensitive studies, inspect negative and positive results.
- **Dependencies:** Knowledge Universe, Market & Data Hub, Experiment Registry.
- **Evidence produced:** dataset manifest, preregistration, complete experiment record, reproducibility bundle and limitations.
- **Future extensibility:** causal, synthetic, cross-market and model-assisted research methods.
- **Authority:** `OFFLINE_FUTURE`; research findings are not strategies and do not authorize promotion.

### D07 — Strategy Lab

- **Purpose:** define and version explicit trading hypotheses and behavior specifications.
- **Inputs:** reviewed `StrategyProposal`, knowledge dependencies, risk constraints and market/execution assumptions.
- **Outputs:** immutable `StrategyVersion` candidates and change-impact assessments.
- **Key entities:** `Strategy`, `StrategyVersion`, parameter set, failure-mode record, compatibility record.
- **AI roles:** Strategy Architect, Quant Reviewer, Microstructure Reviewer, Red Team.
- **Owner interaction:** select proposals for development and approve Level C scope changes.
- **Dependencies:** W1/W2 canonical identity and knowledge contracts plus versioned risk, market and execution **schema/interface contracts**. When W4 exists, Strategy Lab consumes Research Campus proposals. It does not require an operational W5 proving service or W6 Risk Tower to complete the W3 core.
- **Evidence produced:** traceable logic specification, assumptions, dependency/version manifest, reviews and known failure modes.
- **Future extensibility:** discretionary-derived, rule-based, statistical, ML-assisted, hybrid and unknown future methods.
- **Authority:** `OFFLINE_FUTURE`; a strategy is not a released or running bot.

### D08 — Trading Agent Factory

- **Purpose:** create durable bots and assemble exact candidate versions.
- **Inputs:** strategy versions, knowledge profile versions, risk mandates, execution policies, optional models, evidence requirements and bounded experience snapshots.
- **Outputs:** `TradingBot`, immutable `BotVersion`, `ExecutionPolicyVersion`, `EvidenceRequirementSetVersion`, `CandidateAssembly`, `ReleaseCandidateRequest`, compatibility and assembly evidence.
- **Key entities:** bot identity, bot version, execution-policy version, evidence-requirement-set version, component binding, development work order and candidate-assembly manifest.
- **AI roles:** the on-demand Bot Development Organization defined in section 9.
- **Owner interaction:** name/commission bots, set approved purpose, inspect candidate composition, request proof and send eligible candidates to release.
- **Dependencies:** Strategy Lab, Knowledge Universe, Experience System and versioned risk/execution/model **schema/interface contracts**. W5 proving and W6 Risk/Release consume the W3 candidate downstream; they are not W3 readiness dependencies.
- **Evidence produced:** component manifest, version hashes, compatibility verdicts and artifact lineage.
- **Future extensibility:** additional bot engines and component types through versioned compatibility contracts.
- **Authority:** `OFFLINE_FUTURE`; cannot mutate a live bot or self-promote.

### D09 — Bot Park

- **Purpose:** inventory and inspect persistent trading bots and all versions.
- **Inputs:** canonical bot, release, evidence, lifecycle and runtime projections.
- **Outputs:** World/Operations projections, comparison, filtering and drill-down navigation.
- **Key entities:** no independent bot truth; saved views and presentation state only.
- **AI roles:** performance analyst and knowledge curator may provide cited summaries.
- **Owner interaction:** inspect bot DNA/brain/knowledge/experience, version drift, blockers and evidence.
- **Dependencies:** Trading Agent Factory, Release HQ, Operations Center and Owner HQ.
- **Evidence produced:** none from display; exported views MUST retain source/as-of context.
- **Future extensibility:** 5/20/100/500-bot scale, portfolios, markets, workspaces and accessible directory views.
- **Authority:** `SPEC_ONLY` projection; no arbitrary “run” or “ready” truth buttons.

### D10 — Backtest Lab

- **Purpose:** historical economic testing under declared data and execution assumptions.
- **Inputs:** exact strategy/data/parameter/execution-assumption versions and preregistered evaluation contract.
- **Outputs:** `BacktestRun`, report, metrics, uncertainty, sensitivity and limitations.
- **Key entities:** run, scenario, metric set, result artifact and reproducibility bundle.
- **AI roles:** Quant Reviewer and Performance Analyst; authors cannot close their own methodology findings.
- **Owner interaction:** inspect evidence and select further experiments; cannot convert failure into epistemic PASS.
- **Dependencies:** Strategy Lab, Market & Data Hub and methodology contract.
- **Evidence produced:** historical/simulated evidence only, net of declared costs and never a return promise.
- **Future extensibility:** new engines and methods through stable run/report contracts.
- **Authority:** `OFFLINE_FUTURE`.

### D11 — Replay Hangar

- **Purpose:** deterministically replay event, signal, intent, order and state sequences against historical conditions.
- **Inputs:** raw event lineage, exact parser/strategy/execution versions and causal time data.
- **Outputs:** `ReplayRun`, state-transition trace, reconciliation and determinism evidence.
- **Key entities:** replay fixture, event stream, checkpoint, expected/actual state and divergence.
- **AI roles:** Market Microstructure Reviewer, test engineer and Red Team.
- **Owner interaction:** inspect divergences, failure recovery and version regressions.
- **Dependencies:** Market & Data Hub, Strategy Lab, execution seams.
- **Evidence produced:** temporal correctness, idempotency, failure-path and reproducibility evidence; not market profitability proof.
- **Future extensibility:** venue-native and incident replays.
- **Authority:** `OFFLINE_FUTURE`.

### D12 — Simulation Arena

- **Purpose:** test synthetic, scenario, stress and adversarial conditions that history does not adequately cover.
- **Inputs:** exact candidate versions, scenario definitions, assumptions and failure injections.
- **Outputs:** `SimulationRun`, stress outcomes, boundary failures and robustness evidence.
- **Key entities:** scenario, generator/version, seed, fault, run, result and applicability limit.
- **AI roles:** Red Team, Risk Governor, Quant and Microstructure Reviewers.
- **Owner interaction:** set risk questions, review catastrophic paths and request new scenarios.
- **Dependencies:** bot candidate, its W3-authored `RiskMandateVersion`, Market & Data Hub assumptions and versioned Risk Tower schema/interface contracts. W6 independent risk evaluation is a downstream consumer of Simulation evidence, not a prerequisite.
- **Evidence produced:** synthetic/stress evidence explicitly labeled non-historical and non-live-equivalent.
- **Future extensibility:** new scenario generators, synthetic markets and organization-level exercises.
- **Authority:** `OFFLINE_FUTURE`.

### D13 — Risk Tower

- **Purpose:** author exact mandates from approved Owner policy in a bounded W3 slice, then independently evaluate strategy, bot, portfolio, execution, operational and capital-authority risk in W6 and later.
- **Inputs:** W3 authoring receives versioned governance/Owner policy and mandate schema; W6 evaluation receives the authored mandate, exact candidate versions, proving evidence, runtime state when applicable and Owner policy.
- **Outputs:** W3 produces only immutable `RiskMandateVersion` artifacts and grants no verdict or authority; W6+ produces `RiskVerdict = ALLOW | LIMIT | BLOCK | REQUEST_OWNER`, constraints and reasons.
- **Key entities:** `RiskMandateVersion`, risk evaluation, verdict, limit, exception request and expiry.
- **AI roles:** Risk Governor, risk reviewer, institutional portfolio reviewer and Red Team.
- **Owner interaction:** approve policies and any authority/limit increase; inspect blocks and requests.
- **Dependencies:** the W3 authoring slice depends on governance and W1 identity/version contracts; W6 evaluation depends on proving evidence, Market & Data Hub and Operations when active.
- **Evidence produced:** reproducible verdict with scope, inputs, freshness, policy version and limitations.
- **Future extensibility:** new risk classes and policies behind explicit governance.
- **Authority:** may reduce, limit, block or request Owner within policy; MUST NOT autonomously raise limits or restore authority. Capital remains locked.

### D14 — Release HQ

- **Purpose:** explicitly promote exact candidate versions and maintain rollback.
- **Inputs:** `CandidateAssembly`, `ReleaseCandidateRequest`, exact proving evidence artifacts, independent reviews, risk verdict and Owner decision.
- **Outputs:** `ReleasedVersion`, promotion/denial record and `RollbackTarget`.
- **Key entities:** `ReleaseCandidate`, `ReleaseEvidence`, `ReviewVerdict`, `RiskVerdict`, `OwnerDecision`, `ReleasedVersion`, `RollbackTarget`.
- **AI roles:** release verifier, independent reviewers and Risk Governor.
- **Owner interaction:** approve or reject eligible promotion and choose environment scope; Owner cannot turn failed evidence into PASS.
- **Dependencies:** Trading Agent Factory, proving domains and Risk Tower.
- **Evidence produced:** immutable release manifest, gate matrix, decision audit and rollback compatibility evidence.
- **Future extensibility:** environment-specific release lanes without implicit inheritance.
- **Authority:** current maximum is specification of `RELEASED_OFFLINE`; Paper/Live lanes remain locked.

### D15 — Portfolio HQ

- **Purpose:** eventually coordinate multiple proven bots under explicit capital-pool boundaries.
- **Inputs:** eligible released versions, portfolio mandate, reconciled exposures, evidence, capacity and risk state.
- **Outputs:** initially advisory/shadow allocation proposals and aggregate evidence; future decisions only under separate authority.
- **Key entities:** `CapitalPool`, `CapitalBook`, allocation mandate/corridor, reservation, admission, portfolio snapshot, risk contribution, concentration, capacity, conflict and allocation proposal/decision.
- **AI roles:** institutional portfolio reviewer, Risk Governor, Performance Analyst and Red Team.
- **Owner interaction:** define pools/mandates, approve allocations and resolve strategy conflicts.
- **Dependencies:** multiple independently proven bots, Risk Tower, Release HQ, bounded Operations safety and Market & Data Hub.
- **Evidence produced:** gross/net/contingent exposure, normal/stressed correlation, drawdown concurrence, concentration, shared capacity and joint stress evidence.
- **Future extensibility:** venues, accounts, currencies, portfolios and optimizers as later experiments.
- **Authority:** `CAPITAL_LOCKED`; W9 starts `SHADOW_ONLY`. Logical allocation MUST NOT imply physical isolation.

### D16 — Operations Center

- **Purpose:** professional runtime observation, control, reconciliation, incident handling and rollback.
- **Inputs:** environment-scoped released version, runtime events, connectivity/data freshness, risk state and reconciled external state.
- **Outputs:** deployment/run state, observations, alerts, incidents, reconciliation and experience events.
- **Key entities:** deployment, run, alert, incident, reconciliation record, runtime observation and rollback execution record.
- **AI roles:** performance analyst, Risk Governor, incident analyst and Red Team, within bounded tools.
- **Owner interaction:** triage, acknowledge with authority, contain, stop, reconcile and rollback through future approved workflows.
- **Dependencies:** Release HQ, Risk Tower, Market & Data Hub and later broker/execution capability.
- **Evidence produced:** append-only operational timeline, source/as-of/freshness, action audit and incident/postmortem records.
- **Future extensibility:** markets, venues, portfolios, multi-monitor and fleet-scale operations.
- **Authority:** `CAPITAL_LOCKED`; W6/W7 must provide bounded safety observation before Paper, while W10 scales and unifies the full console.

### D17 — Market & Data Hub

- **Purpose:** admit, normalize, version and serve market, reference, signal and future broker data while preserving native provenance.
- **Inputs:** adapters, raw observations, venue/reference data and source quality metadata.
- **Outputs:** point-in-time datasets, normalized observations, source lineage and capability profiles.
- **Key entities:** `MarketDataset`, `DatasetManifest`, `TradingSignal`, `SignalDataset`, venue/instrument/session profile, clock-quality and data-quality incident.
- **AI roles:** data curator, market researcher and Microstructure Reviewer.
- **Owner interaction:** approve new market/venue/source scope and inspect data-quality limits.
- **Dependencies:** source adapters and governance.
- **Evidence produced:** raw/normalized/derived lineage, availability times, revisions, quality and license/consent records.
- **Future extensibility:** `MarketDataAdapter`, `SignalSourceAdapter`, and future data types without a universal Telegram schema.
- **Authority:** `OFFLINE_FUTURE`; a configured adapter grants no network, credential, or trading authority.

### D18 — Knowledge Graph

- **Purpose:** connect products, sources, findings, hypotheses, strategies, bots, evidence and experience for traceability and retrieval.
- **Inputs:** canonical IDs, immutable version references and typed lineage edges.
- **Outputs:** graph queries, impact analysis, provenance paths and retrieval indexes.
- **Key entities:** relationship edge, graph snapshot and index status; payload ownership stays in source domains.
- **AI roles:** Knowledge Curator, research and evolution analysts.
- **Owner interaction:** explore why a bot knows, believes, uses or changed something.
- **Dependencies:** all artifact-owning domains.
- **Evidence produced:** graph validation, source links and impact paths, not independent artifact truth.
- **Future extensibility:** new nodes/edges with schema migration and compatibility.
- **Authority:** `OFFLINE_FUTURE` index/projection only.

### D19 — Experience / Memory System

- **Purpose:** keep distinct durable and temporary memory scopes and convert observations into governed datasets.
- **Inputs:** product decisions, assigned knowledge, runtime/research observations, results and worker context.
- **Outputs:** product/organization memory, bot knowledge references, `ExperienceDataset`, `ExperienceMemory`, scratch context and audit history.
- **Key entities:** memory record, scope, cutoff, retention/provenance policy, experience observation/dataset and audit event.
- **AI roles:** Knowledge Curator, Performance Analyst, Evolution Agent and Red Team.
- **Owner interaction:** assign/revoke knowledge, inspect experience, set retention/sensitivity rules.
- **Dependencies:** Knowledge Universe, Operations, Research and governance.
- **Evidence produced:** immutable cutoffs, provenance, access/use records and dataset version lineage.
- **Future extensibility:** storage/retrieval implementations, privacy/deletion policies and new memory types.
- **Authority:** `OFFLINE_FUTURE`; scratch/chat history is not the memory architecture and cannot silently change released behavior.

### D20 — Evolution Engine

- **Purpose:** turn evidence and experience into controlled product or strategy evolution proposals.
- **Inputs:** observations, experience datasets, incidents, performance/methodology analyses, Product Graph gaps and frontier items.
- **Outputs:** `EvolutionProposal`, hypothesis, experiment request and candidate-change request.
- **Key entities:** observation, analysis, proposal, change-impact class and candidate link.
- **AI roles:** Evolution Agent, Performance Analyst, system architect, Quant Reviewer, Risk Governor and Red Team.
- **Owner interaction:** approve Level C proposals, prioritize experiments and reject unsafe self-modification.
- **Dependencies:** Experience System, Research Campus, Product Graph and proving/release loop.
- **Evidence produced:** proposal lineage, rationale, affected evidence and post-change comparison plan.
- **Future extensibility:** organization-level learning and bounded adaptation policies.
- **Authority:** `OFFLINE_FUTURE`; proposes only. Structural change returns to the factory and proving cycle.

### D21 — Unknown Frontier

- **Purpose:** represent uncertainty explicitly instead of hiding it in implied plans.
- **Inputs:** unresolved assumptions, emerging capabilities, regulatory/market changes and failed experiments.
- **Outputs:** categorized unknowns, research questions, proposals and Owner decision requests.
- **Key entities:** frontier item, assumption, uncertainty, trigger, proposal and discovery evidence.
- **AI roles:** all discovery/review roles may add cited frontier proposals.
- **Owner interaction:** observe uncertainty, commission discovery and promote an item only through a governed Product Graph decision.
- **Dependencies:** Product Graph and all domains.
- **Evidence produced:** provenance for the unknown, trigger/impact and decision history.
- **Future extensibility:** deliberately open-ended.
- **Authority:** `SPEC_ONLY`; fog, empty terrain or AI speculation is never a commitment.

## 7. Owner experience and the 30-second contract

Owner HQ MUST surface, without raw-log inspection:

- what is running and in which environment;
- what is being built and by which pipeline;
- what is blocked and why;
- decisions requiring Owner action;
- the bot inventory and exact active/released versions;
- current risk and capital-authority state;
- important new or invalidated evidence;
- research, experiments and strategy candidates;
- product and strategy evolution proposals;
- critical alerts and incidents.

The above-the-fold priority is deterministic:

1. persistent safety strip: environment, source/as-of, freshness, connectivity, risk meta-state, capital authority and locked gates;
2. critical alerts/incidents and active containment;
3. unknown, stale, partial or reconciling state;
4. risk, authority, blockers and `NEEDS_OWNER` decisions;
5. running/stopped/degraded systems and active versions;
6. release/evidence changes;
7. current builds, research, experiments, candidates and evolution proposals;
8. routine activity and world navigation.

Every aggregate MUST drill to the exact entities, versions, filters, timestamps and evidence that formed it. `LOCAL_SEEN` is not authoritative `ACKNOWLEDGED`. Counts and building summaries MUST expose critical, blocked, stale, unknown or Owner-needed children instead of averaging them away.

## 8. Two UX views — one truth

### 8.1 Canonical view contract

World View and Operations View MUST consume the same stable entity/version IDs, query/filter context, selection, time context, authority, source, `asOf`, freshness, partial/error state and evidence references. UI-local writable state is limited to presentation, layout, navigation, filters and selection.

Switching views MUST preserve context and deep links. Neither view may calculate a gate verdict, persist canonical status, or mutate a domain entity. Current UI prototypes and mock snapshots are visual references only.

### 8.2 World View

World View is a warm pixel-art management game/campus/farm representation. It makes the organization intuitive, alive and enjoyable without trivializing risk.

| World object | Canonical meaning |
|---|---|
| Owner HQ | Owner attention, decisions, blockers and material evidence changes |
| District/building | A domain, wave or bounded capability aggregate |
| Persistent bot NPC | Exactly one durable `TradingBot` |
| Worker NPC | One temporary cognitive `WorkerRun` or assignment, visibly distinct from a bot |
| Gate/tower checkpoint | Explicit review, risk, release or capital verdict |
| Parcel/path/activity marker | Typed artifact flow, or explicitly cosmetic ambience |
| Blueprint/scaffold/closed district | Planned, proposed, blocked or locked scope with text reason/dependency |
| Frontier zone/observatory | Explicit unknowns, assumptions, experiments and proposals |

Animation MUST reflect actual cited activity or be visibly ambient; it cannot imply completion, health, authority or self-modification. Owner-avatar movement and selecting buildings/NPCs are navigation only. The Galaxy MUST scale through districts, zoom, minimap, search, bounded representatives and a searchable directory rather than drawing every entity at once.

Critical meaning MUST use text plus shape/icon and not rely only on sprite, color, motion, sound or tooltip. Support keyboard/D-pad navigation, screen readers, reduced motion, forced colors/high contrast, 200% zoom and small-screen review without hiding safety facets.

### 8.3 Operations View

Operations View is the calm, dense professional surface for evidence, versions, logs, charts, risks, experiments, release history, health and eventual positions/orders/PNL. Risk and freshness always outrank performance. Until authoritative runtime data exists, future fields render `LOCKED`, `NO_DATA`, `NOT_EVALUATED`, `UNKNOWN` or `STALE`, never simulated health.

The canonical fleet roster prioritizes: bot identity; exact component/release versions; primary blocker; risk; run/health/connectivity; freshness/source; evidence validity; gates; alerts. Search, grouping, saved views, density/column controls, virtualization, keyboard triage and a contextual inspector support scale. A warm shell, domain crests and compact bot portraits preserve identity; evidence/risk/incident surfaces remain professional and have no ambient loops.

Typed alerts include source, scope, severity, age, reason/rule, affected entities, acknowledgement authority and drill-down. Typed incidents include containment, timeline, affected versions/runs, reconciliation evidence, actions, resolution, postmortem and rollback.

## 9. AI organization and Model Router

### 9.1 Two meanings of “agent”

**Cognitive AI worker** — a temporary/on-demand specialist run that performs intellectual work under a role contract. It has bounded tools, context, memory, budget, authority and a typed output. It is not a durable trading entity.

**Trading agent / bot** — a persistent, named, versioned product entity that may eventually operate a proven strategy. It is not permanently six LLMs talking to each other. Its structural behavior is the explicit composition of versioned components.

### 9.2 On-demand Bot Development Organization

| Role | Primary typed outputs | Authority boundary |
|---|---|---|
| Bot Researcher | research question/brief/finding/hypothesis | proposes; cannot promote |
| Knowledge Curator | source admission, knowledge pack/profile version, provenance/conflict record | cannot declare learning success or runtime authority |
| Strategy Architect | strategy proposal/specification/candidate change | cannot mutate released logic |
| Quant Reviewer | methodology verdict and reproducible findings | independent; cannot close own findings |
| Market Microstructure Reviewer | execution-assumption and venue-mechanics findings | no endpoint or order authority |
| Performance Analyst | evidence-bound performance/diagnostic report | no return promise or automatic promotion |
| Evolution Agent | evolution proposal and change-impact request | proposal only |
| Risk Governor | `ALLOW`, `LIMIT`, `BLOCK`, `REQUEST_OWNER` within approved policy | can only constrain/stop/request; cannot raise authority |
| Red Team | adversarial scenarios and unresolved findings | cannot approve its own remediation |

Worker artifacts MUST record work order, role/version, mandatory context, tools, memory scope, model-routing record, budget, timestamps, validation, provenance and output contract. Workers do not write directly into released bot structure.

### 9.3 Abstract Model Router

```text
ROLE → ROUTING REQUEST → MODEL ROUTER → MODEL ADAPTER → MODEL PROVIDER
```

A role defines authority, allowed tools, mandatory context, memory scope, reasoning class, budget and output contract. The router selects a swappable provider/model/backend using policy, capability, availability, cost and data-boundary constraints. `ModelRoutingRecord` captures the requested role, selected adapter/provider/model version, fallback/refusal, relevant parameters, context manifest and validation result.

Router or model failure MUST fail closed. A fallback cannot gain tools, context or authority. Typed output validation, deterministic risk/execution logic and downstream gates remain outside the model. The architecture is not tied to OpenAI or any single model provider.

## 10. Knowledge platform and Telegram intelligence

### 10.1 Core knowledge entities

- `KnowledgeSource`: origin and access/admission metadata for any source type.
- `KnowledgeItem`: immutable or revision-aware captured unit with raw provenance.
- `KnowledgePack`: curated logical collection.
- `KnowledgePackVersion`: immutable manifest of exact items, transformations and policies.
- `AgentKnowledgeProfile`: durable assignment intent for one bot.
- `AgentKnowledgeProfileVersion`: immutable bindings, retrieval/rule policies, priority/conflict rules and cutoff.
- `KnowledgeProvenance`: source, author/channel when known, event/availability times, capture method, revisions, transformations, licensing/consent, quality and lineage.
- `SignalSource`, `SignalDataset`, `TradingSignal`: signal-specific source, versioned dataset and normalized signal representation.
- `ExperienceDataset`, `ExperienceMemory`: versioned observations/results and retrievable experience scoped to a bot/version/cutoff.

Admission MUST distinguish raw, normalized and derived representations; keep exact lineage; record quality, ambiguity, conflict, poisoning risk, license/consent/retention state; and support quarantine, revocation and downstream impact analysis. A knowledge assignment means “available under this profile”, not “learned”, “true”, “profitable” or “authorized”.

Required extension seams are `KnowledgeSourceAdapter`, `SignalSourceAdapter`, `MarketDataAdapter`, `BrokerAdapter`, and `ModelAdapter`. Lists are open. Telegram is one source/adapter type, not the universal architecture. The presence of a `BrokerAdapter` does not authorize credentials, connectivity, orders or capital.

### 10.2 TEACH FROM SIGNALS

Historical messages become a provenance-bearing `SignalDataset` for research, rule extraction, behavior study and evaluation. Conceptual extraction supports `ENTRY`, `STOP`, `TP`, `TIME`, `DIRECTION`, `RESULT`, and `CONTEXT`, plus ambiguity/censoring. Raw messages, edits, deletes, replies, channel/source, event time, receipt/availability time, parser version and label-policy version remain traceable. `RESULT` is derived by a preregistered labeling policy; retrospective commentary is not ground truth by default.

This mode is offline and does not authorize runtime following.

### 10.3 FOLLOW SIGNALS

Future runtime ingestion may act on new signals only through a separately approved capability, versioned execution strategy, risk mandate, freshness/ambiguity validation, idempotency, reconciliation, audit and environment authority. Historical teaching acceptance does not transfer to runtime following. **FOLLOW SIGNALS is currently LOCKED.**

## 11. Learning and memory

### 11.1 Learning modes

1. **Memory / retrieval:** retrieve cited knowledge or experience under a pinned profile/cutoff. Retrieval-policy changes that affect decisions are behavior changes and require impact review.
2. **Rule extraction:** transform knowledge into explicit, reviewable, versioned structured rules with provenance and conflict handling.
3. **Statistical learning:** fit statistical behavior from versioned data under a preregistered evaluation contract.
4. **Model training / fine-tuning:** only after an evidence/economics case, baseline comparator, isolated evaluation, dataset card, provider/model version, reproducibility-limit record and rollback target. It is not the default.
5. **Experience learning:** convert a bot’s observations/trades/results into a versioned experience dataset, then into analysis, hypotheses and candidates.

Learning outputs are typed artifacts, not implicit state. Own experience is endogenous and policy-selected; it does not by itself prove causal improvement. Any structural change, parameter-boundary change, feature/model/prompt/retrieval change or new data/label policy creates or updates a candidate and invalidates affected evidence.

### 11.2 Memory layers

| Layer | Scope | Rules |
|---|---|---|
| Product / Organization Memory | shared architecture, decisions and graph context | versioned, permissioned, source-linked |
| Personal / Bot Knowledge | knowledge assigned to one bot | pinned `AgentKnowledgeProfileVersion`; explicit inheritance/overrides |
| Experience Memory | bot observations and outcomes | versioned dataset, cutoff, provenance, bias/censoring flags |
| Scratch Memory | temporary worker/run context | bounded lifetime; not canonical truth |
| Audit Memory | append-only decisions/evidence history where appropriate | immutable lineage, actor/authority and timestamps |

Chat history is neither the complete memory architecture nor automatic canonical memory.

## 12. Research, strategy and proving methodology

### 12.1 Research lifecycle

```text
ResearchQuestion
→ ResearchBrief + ResearchProtocol
→ ResearchDataset / DatasetManifest
→ ResearchFinding
→ Hypothesis
→ Experiment + ExperimentResult
→ StrategyProposal
→ independent review
→ eligible StrategyVersion work
```

The preregistered protocol fixes, before results are inspected: hypothesis/mechanism; falsification; benchmark; universe/timeframe; exclusions; dataset roles and temporal splits; costs; primary metrics; uncertainty method; minimum meaningful effect; multiple-testing budget; and stopping rule. The registry retains failed and null experiments.

Data MUST provide immutable snapshot/manifests, event time and availability time, source revisions, quality incidents and as-of reproduction. Roles are explicit: research/train, validation, sealed holdout, forward observation, replay/regression and experience. One dataset cannot silently serve incompatible roles. No optimization occurs on holdout. Overlap, clustering, correlated sources, re-entry/scale-in and dependency-adjusted effective sample size are considered. Walk-forward/OOS, regime coverage, parameter/cost sensitivity, uncertainty and selection/multiple-testing controls are required by later candidate acceptance contracts.

### 12.2 Strategy model

`Strategy` is durable identity; `StrategyVersion` is immutable and can reference:

- hypothesis and applicability boundary;
- market/universe and timeframe;
- entry and exit logic;
- risk rules and position sizing;
- execution assumptions;
- knowledge, feature and data dependencies;
- parameter set;
- evidence and known failure modes;
- benchmark/evaluation protocol and change-impact class.

The architecture supports discretionary-derived, rule-based, statistical, ML-assisted, hybrid and unknown future methods. Strategy produces a bounded trading intent; `ExecutionPolicyVersion` translates allowed intent into venue mechanics and cannot create exposure or exceed `RiskMandateVersion`.

### 12.3 Non-substitutable proving layers

| Layer | Question answered | Cannot prove |
|---|---|---|
| Backtest Lab | How did the exact strategy behave historically under declared assumptions? | deterministic event handling, live fills or future profitability |
| Replay Hangar | Did exact event/order/state transitions behave causally and reproducibly? | economic robustness outside replayed conditions |
| Simulation Arena | How does the system behave under synthetic, stress, failure and adversarial scenarios? | historical prevalence or live equivalence |
| Robustness / independent review | Are methodology, uncertainty, selection bias, model risk and applicability adequate? | Owner authority or future return |

Each result binds exact data, code/build, strategy, parameters, knowledge policy when behavior-relevant, risk/execution policy, venue profile, fill/cost model, environment, seeds where applicable and limitations. Numerical thresholds belong in future versioned acceptance contracts and are fixed before evaluation. A reviewer or Owner cannot waive a failed epistemic gate; a PASS only makes promotion eligible within its scope.

## 13. Bot model, version binding and lifecycle

### 13.1 Durable bot and release manifest

`TradingBot` is durable identity. The metaphors are useful but not schemas:

- **BOT DNA:** explicit component/version composition;
- **BOT BRAIN:** strategy plus applicable deterministic/statistical/model behavior;
- **BOT KNOWLEDGE:** exact bot-specific knowledge profile version;
- **BOT EXPERIENCE:** bounded experience snapshot/cutoff and permitted use.

An immutable `BotVersion` MUST bind exact, never-latest references to:

```text
BotVersion
├─ StrategyVersion
├─ AgentKnowledgeProfileVersion
├─ RiskMandateVersion
├─ ExecutionPolicyVersion
├─ ModelVersion / ModelRoutingPolicyVersion (when behavior-relevant)
├─ EvidenceRequirementSetVersion
└─ ExperienceDatasetVersion + cutoff / permitted adaptation envelope
```

It also binds software/build versions, compatibility assessment and provenance. Produced evidence MUST NOT be a content-bearing input to the `BotVersion` it evaluates: every proving artifact targets the already immutable `BotVersion` ID. Release HQ creates an immutable `ReleaseEvidenceSetVersion` that aggregates exact proving, review and risk evidence references for that target, and the `ReleaseCandidate`/release manifest binds both IDs. This prevents the cycle “new evidence creates a new bot version that requires new evidence”. The bot’s graph record remains linked to applicable and historical evidence without making downstream evidence part of its behavior hash.

`ReleasedVersion` wraps one exact `BotVersion`, one exact `ReleaseEvidenceSetVersion`, environment/authority scope, Owner decision, validity, and `RollbackTarget`. Rollback compatibility covers the full composition, not strategy code alone.

### 13.2 Bot lifecycle

```text
IDEA
→ DESIGN
→ RESEARCH
→ KNOWLEDGE
→ STRATEGY
→ DEVELOPMENT
→ BACKTEST
→ REPLAY
→ SIMULATION
→ INDEPENDENT REVIEWS
→ OWNER RELEASE GATE
→ RELEASED OFFLINE
```

Future locked lanes:

```text
PAPER CANDIDATE → PAPER
PILOT CANDIDATE → OWNER LIVE GATE → LIMITED LIVE
LIVE CANDIDATE → OWNER LIVE GATE → LIVE
```

Then:

```text
MONITORING
→ EXPERIENCE
→ EVOLUTION PROPOSAL
→ CANDIDATE VERSION
→ PROVING
↺
```

Backtest, Replay, Simulation and reviews are repeatable evidence jobs as well as lifecycle requirements; new behavior-relevant inputs can invalidate them. `RELEASED_OFFLINE` carries zero Paper/Live inheritance.

### 13.3 Orthogonal state axes

The product MUST NOT encode all conditions in one giant status or synthetic readiness percentage.

| Axis | Meaning | Example values, not a frozen universal enum |
|---|---|---|
| `lifecycle_stage` | maturity/promotion position | `IDEA`, `PROVING`, `RELEASED_OFFLINE`, future candidates |
| `gate_verdicts` | independent gate outcomes | `PASS`, `FAIL`, `BLOCKED`, `NEEDS_OWNER`, `NOT_EVALUATED` |
| `run_state` | runtime activity | `STOPPED`, `STARTING`, `RUNNING`, `PAUSED`, `HALTED`, `RECONCILING` |
| `health_state` | observed health | `HEALTHY`, `DEGRADED`, `CRITICAL`, `UNKNOWN` |
| `risk_state` | current risk posture | `NOT_EVALUATED`, `NORMAL`, `WATCH`, `PROTECT`, `EMERGENCY`, `LOCKED` |
| `connectivity_state` | data/venue connectivity | `OFFLINE`, `CONNECTED`, `STALE`, `DISCONNECTED`, `UNKNOWN` |
| `evidence_freshness` | validity in time and scope | `FRESH`, `STALE`, `EXPIRED`, `SUPERSEDED`, `INVALIDATED`, `UNKNOWN` |

Example: `lifecycle = RELEASED_OFFLINE`, `health = HEALTHY`, `risk = LOCKED`, `run = STOPPED`. A green axis cannot conceal an unknown or locked axis.

## 14. Evidence-first truth and lineage

```text
SOURCE
→ HYPOTHESIS
→ DATA
→ BACKTEST
→ REPLAY
→ ROBUSTNESS / SIMULATION
→ RISK
→ REVIEWERS
→ OWNER DECISION
```

DONE, PASS and promotion MUST be derived from typed artifacts such as specifications, implementation, tests, backtests, replay, simulation, review/risk verdicts, CI, hashes, Owner decisions and runtime evidence. UI buttons only request a governed workflow.

An evidence record MUST identify artifact/version, claim and applicability scope; upstream dependencies; producer/actor; exact data/code/config/environment/model context; assumptions; timestamps; result/verdict; limitations; freshness/expiry; and reproducibility inputs. Lineage edges preserve the complete source-to-release path.

Evidence validity states include `VALID`, `STALE`, `EXPIRED`, `SUPERSEDED`, `INVALIDATED` and `NON_COMPARABLE`. Historical evidence remains auditable after invalidation but cannot support a changed candidate automatically. Behavior-relevant changes trigger `ChangeImpact` and re-proving of affected claims. Missing, stale, incompatible or differently scoped evidence cannot yield DONE.

## 15. Market, data, execution and microstructure seams

The product architecture reserves explicit versioned models for:

- fees, rebates and auditable cost attribution;
- spread, slippage, latency and clock quality;
- partial fills, queue/available volume, cancel/fill races and residual exposure;
- liquidity, market impact, capacity tiers and order-book constraints;
- funding, borrow/short and collateral mechanics;
- trading sessions, auctions, maintenance and exchange/broker-specific behavior;
- order types, time-in-force, tick/lot/minimums, price bands, rate limits, reduce-only/stops and rejection semantics;
- execution and reconciliation policies.

`VenueInstrumentProfileVersion` describes venue/instrument/session capability without pretending all venues share one state machine. `ExecutionAssumptionVersion` / fill-cost model is bound by every backtest, replay, simulation and future Paper evidence bundle. Evidence MUST use one declared accounting convention so spread/slippage/fill-price effects, fees, funding, borrow and impact are not double-counted.

Causal time semantics preserve source/venue, receipt/availability, decision, intent, simulated/actual send, acknowledgement, cancel and fill times plus clock-quality state. Normalization preserves venue-native raw fields.

Proving uses conservative/base/adverse execution scenarios, uncertainty and an execution-evidence level. A touched limit is not automatically a fill. Material unknowns become limitations or blocks, never optimistic defaults. Uncertain acknowledgements, unsupported capability, incomplete fills, stale clocks/data and failed reconciliation fail closed for new intents. Detailed order/reconciliation state belongs to future Operations/Execution objects, not the bot lifecycle axis.

All of these are **non-operational extension seams** in this stage.

## 16. Risk, release, portfolio and operations

### 16.1 Risk architecture

Risk is evaluated independently across strategy, bot, portfolio, execution, operational and capital-authority scopes. Verdicts are scope/version/policy/freshness bound. A Risk Governor may `ALLOW`, `LIMIT`, `BLOCK` or `REQUEST_OWNER` within approved policy. Automation is monotone-safe: it may reduce or stop authority, but cannot increase a limit or restore authority beyond Owner policy.

Current `governance/risk-policy.toml` is an owner-locked policy instance, not a universal product default and not a future multi-bot allocation mandate. No existing bot/setup percentage is multiplied into a portfolio limit.

### 16.2 Release architecture

Promotion is explicit and environment-scoped. Release HQ verifies component compatibility, evidence validity, independent review, risk verdict, Owner decision and rollback compatibility. Merge/release, Paper, Pilot and Live gates are independent and non-inheriting. A technically eligible candidate may still be denied by the Owner; an Owner approval cannot repair failed evidence.

### 16.3 Portfolio architecture

Portfolio HQ coordinates; it does not own hard risk policy, release eligibility, market truth or reconciled runtime truth. It consumes versioned references from Risk Tower, Release HQ, Market & Data Hub and Operations. W9 begins as advisory/`SHADOW_ONLY` and requires multiple independently proven bot versions plus joint portfolio evidence.

Capital-pool boundaries distinguish account/subaccount, venue, margin/collateral pool, currency, custody and capital book. Logical allocation is not physical isolation. Preserve gross, net and contingent exposure; open, conditional, cancel-pending and competing intents; normal/stressed correlation; concentration; drawdown budget; risk contribution; shared capacity; simultaneous exit/liquidity stress; funding/collateral shock; strategy-family crowding; and conflict/netting/hedging policy. Low net exposure cannot hide shared risk.

Admission, suspension, removal, re-entry and rollback are version/evidence bound. Initial allocation is deterministic/manual and Owner-defined. Any optimizer is a later non-authorizing experiment. Numerical mandates require future Owner decisions.

### 16.4 Operations architecture

Future observation includes bot/run state, exact strategy/knowledge/risk/execution/model versions, market connectivity, data/clock freshness, execution health, future positions/orders/PNL, alerts, incidents, degradation, reconciliation and rollback. PNL never visually outranks risk or freshness and is absent until authoritative.

W7 Paper cannot precede bounded safety observation: runtime status, data freshness/connectivity, order/position reconciliation appropriate to the Paper simulator, alerts, incidents, audit, protection state and rollback visibility. W10 later provides the scaled unified professional center; it is not the first observability delivered.

## 17. Controlled self-evolution

```text
OBSERVATION
→ EXPERIENCE
→ ANALYSIS
→ HYPOTHESIS
→ EXPERIMENT
→ CANDIDATE VERSION
→ BACKTEST
→ REPLAY
→ SIMULATION
→ REVIEWS
→ RELEASE GATE
```

Unrestricted live structural self-modification is prohibited. Structural strategy, knowledge/retrieval, feature, model, data/label, risk, execution or parameter-boundary changes create a candidate version and invalidate affected evidence. Rollback is mandatory.

Future runtime adaptation MAY exist only within a versioned, proven, monitored parameter envelope whose allowed variables, bounds, update rule, risk constraints, stop conditions, evidence, telemetry and rollback are explicitly approved. Crossing an envelope is a structural change. Experience creates evidence and proposals; it does not autonomously create authority.

## 18. Product Graph and Living Roadmap

### 18.1 Hierarchy and traceability

```text
PRODUCT / UNIVERSE
→ DOMAIN
→ WAVE
→ EPIC
→ CAPABILITY
→ TASK
→ WORK UNIT
```

Typed graph objects also include `Dependency`, `Decision`, `Proposal`, `Experiment`, `Blocker`, `Evidence` and locked `AuthorityGate` references. Every executable Work Unit traces upward to product intent and downward to acceptance/evidence. Dependencies are explicit, typed and acyclic. DONE requires evidence references; `NEEDS_OWNER` stops affected autonomous progress. An `AuthorityGate` node makes a required Owner decision visible but grants nothing by existing or by completion of its upstream Wave; it must reconcile to the same authority/lock subject rather than become a second policy store.

Product status vocabulary is: `DONE`, `READY`, `ACTIVE`, `PLANNED`, `PROPOSED`, `EXPERIMENT`, `NEEDS_OWNER`, `BLOCKED`, `LOCKED`, `SUPERSEDED`, `UNKNOWN_FRONTIER`. This vocabulary describes Product Graph objects and MUST NOT replace FACTORY-001A runtime vocabulary or bot state axes.

### 18.2 One roadmap truth

This Master Spec owns product semantics. `MASTER_ROADMAP.md` owns sequencing and narrative wave contracts. The future canonical Product Graph owns operational roadmap state. Views and documents become versioned projections or generated explanations; they do not remain independent writable registries.

`PRODUCT_GRAPH_BOOTSTRAP.toml` is a **NON-OPERATIONAL PRODUCT GRAPH BOOTSTRAP**. It is deterministic, checked and read-only in authority effect. `factory/registry.toml` remains only the current **Software Factory** runtime registry; it is not declared product-wide truth. W1 MUST designate the future product-wide canonical graph, migrate/evolve the bootstrap and reconcile or adapt the factory registry through one authoritative boundary, then retire the bootstrap as a writable input. Dual reconciliation-free writes are prohibited.

### 18.3 Uncertainty categories

- **COMMITTED CORE:** accepted scope backed by current evidence.
- **PLANNED:** sequenced intent with dependencies but not current truth.
- **PROPOSALS:** options awaiting evidence or decision.
- **EXPERIMENTS:** bounded learning work with no automatic promotion.
- **UNKNOWN FRONTIER:** unresolved future capability, assumption or discovery.

Unknowns are first-class nodes with provenance, impact, trigger and next discovery action. New node/edge/domain types use compatibility and migration seams instead of rewriting the architecture.

## 19. Authority and future Software Factory contract

### 19.1 Product Change levels

- `PRODUCT_CHANGE_LEVEL_A`: bounded implementation, tests, refactors or docs inside an approved Task/WU.
- `PRODUCT_CHANGE_LEVEL_B`: small compatible extension recorded in the Product Graph.
- `PRODUCT_CHANGE_LEVEL_C`: explicit Owner Gate. Includes a new major Domain, lifecycle stage, authority, market, exchange/broker, credential model, risk philosophy, global UX paradigm, Paper activation, Limited Live, Live or capital-bearing authority.

These names are strictly namespaced and MUST NOT be confused with any existing capital mandate Level A/B terminology. Product-change classification grants no capital authority and no current factory automation authority.

### 19.2 Current locks

- FACTORY-001A: `CURRENT / ACCEPTED` bounded deterministic planning baseline.
- FACTORY-001B: `LOCKED / NEEDS_OWNER` controlled coding-agent execution.
- FACTORY-001C: `LOCKED` three controlled Work Units/day.
- FACTORY-001D: `LOCKED` controlled Git delivery.
- FACTORY-001E: `LOCKED` real-time Owner UI.
- Paper: `LOCKED`.
- Limited Live: `LOCKED`.
- Live: `LOCKED`.
- `capital_authority = false`.

### 19.3 Future cadence — specification only

Timezone: `Europe/Moscow`.

- Mon–Thu: 10:00 Work Unit 1; 14:00 Work Unit 2; 18:00 Work Unit 3.
- Friday: 1–2 Work Units, architecture/integration review and weekly report.
- Weekend: paused.
- Limits: `max_active_epics = 1`, `max_work_units_per_day = 3`, `max_parallel_writers = 1`, `max_correction_loops_per_unit = 2`.

Execution is sequential. A dependent Work Unit starts only after prior PASS; FAIL blocks dependants; `NEEDS_OWNER` stops relevant autonomy. Empty slots do not create artificial work. This contract is future/locked and does not change current `factory/daily_run.toml` or FACTORY-001A behavior.

## 20. Explicit non-goals for this stage

This stage does not implement the Knowledge Platform, Research Campus, bot runtime, backtester, replay engine, simulator, portfolio allocator, execution engine, Paper, Limited Live, Live, new scheduler, FACTORY-001B, production credential/security infrastructure, or a database topology. It does not reconnect quarantined legacy Telegram/Bitget execution paths. It does not reopen frozen V13/PM V3/external trust-root work or alter current risk limits.

## 21. Conformance and observable acceptance

| Requirement group | Primary sections | Bootstrap/roadmap evidence |
|---|---|---|
| `PMS-REQ-001..003` | 2–6 | Product, domains, waves, epics and dependency nodes |
| `PMS-REQ-004..005` | 7–8 | Owner HQ and dual-view W1 capabilities |
| `PMS-REQ-006..007` | 9 | AI Organization and Model Router domain/epics |
| `PMS-REQ-008..010` | 10–11 | W2 knowledge/Telegram/provenance dependencies |
| `PMS-REQ-011..012` | 13 | W3 bot composition and lifecycle capabilities |
| `PMS-REQ-013..015` | 12, 14–15 | W4–W6 research/proving/evidence edges |
| `PMS-REQ-016..017` | 16–17 | W6–W11 risk/release/operations/evolution waves |
| `PMS-REQ-018..020` | 18–20 | graph metadata, authority locks and roadmap classifications |

The future W1 Owner HQ acceptance scenarios MUST include: 30-second morning review; blocked release; stale/partial data; degraded bot; alert storm; incident containment; version rollback; and 5/20/100/500-bot fleet triage. Tests MUST verify stable cross-view IDs/filter context, axis-qualified state, evidence drill-down, visible locks and accessible non-visual alternatives.

No Owner decision is required to accept this documentation-only architecture. Any activation of a locked capability remains a separate future decision.
