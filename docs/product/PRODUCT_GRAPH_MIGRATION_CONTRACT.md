# Product Graph Migration and Ownership Contract

Status: **APPROVED MIGRATION CONTRACT — MIGRATION NOT IMPLEMENTED**

Work Unit: `WU-W1-GRAPH-MIGRATION-CONTRACT`

This document defines the minimum repository-native contract for a future migration from the non-operational Product Graph bootstrap to one canonical product-wide Product Graph. It does not perform that migration, change Product Graph or Factory data, change application behavior, or declare W1, `TASK-W1-DESIGN-CANONICAL-GRAPH`, or `CAP-W1-GRAPH-MIGRATION` DONE.

The words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 1. Current state

At the time of this contract:

- `docs/product/PRODUCT_MASTER_SPEC.md` owns product semantics.
- `docs/product/MASTER_ROADMAP.md` owns narrative sequencing and wave contracts.
- `docs/product/PRODUCT_GRAPH_BOOTSTRAP.toml` is a checked, non-operational migration input. It is not writable runtime truth.
- `factory/registry.toml` is the Software Factory runtime registry. It is not the product-wide Product Graph.
- `apps/bot-farm-ui/src/data/generated/productGraphSnapshot.json` is a generated, read-only Owner HQ projection.
- W0 is `DONE`, W1 is `ACTIVE`, and W2 is `PLANNED`.
- FACTORY-001A and FACTORY-001B are `DONE`; FACTORY-001C, FACTORY-001D, and FACTORY-001E are `LOCKED`.
- Paper, Limited Live, and Live are `LOCKED`; `capital_authority = false`.

These states and locks MUST be preserved by migration. This contract does not advance any lifecycle state or authority level.

## 2. Target state and ownership

### 2.1 Canonical graph

The canonical product-wide Product Graph MUST be a single version-controlled TOML file at:

`docs/product/PRODUCT_GRAPH.toml`

That file MUST be the only writable authoritative source for product-wide lifecycle state, roadmap state, product hierarchy, product dependencies, product locks, and Product Graph relationships. Its repository history is the audit trail. No database, graph database, service API, event bus, daemon, or background synchronization process is required or authorized by this contract.

The Product Galaxy / Living Roadmap domain owns the graph's product meaning. A write MAY occur only as a reviewed repository change under an approved Task and Work Unit, within the authority recorded for that work, by the single writer assigned to that Work Unit. The Owner remains the decision authority for changes that require an Owner gate. A tool, UI, exporter, Factory run, or generated file MUST NOT write canonical graph state directly.

### 2.2 Authoritative sources and projections

An **authoritative source** owns the fields and decisions within its declared boundary. A **generated projection** is a deterministic, disposable representation derived from an authoritative source for a consumer.

The canonical Product Graph MUST own product-wide state only. Product semantics MUST remain governed by `PRODUCT_MASTER_SPEC.md`, and narrative sequencing MUST remain governed by `MASTER_ROADMAP.md`, according to their existing roles. After cutover, graph-backed statuses and relationships shown in narrative documents MUST be derived from or reviewed against the canonical graph; those documents MUST NOT become parallel writable state registries.

Owner HQ snapshots, UI data, reports, indexes, and any Factory-facing graph projection MUST be generated or read from `PRODUCT_GRAPH.toml`. They MUST be reproducible from a verified canonical revision and MUST NOT be reverse-written into the canonical graph. Editing a generated artifact is prohibited. A generated artifact MAY be committed only when its generating contract requires a checked-in projection and its bytes match deterministic regeneration.

### 2.3 Authority and data flow

```text
Product Master semantics + Owner decisions + approved Task/Work Unit
                              |
                              v
             docs/product/PRODUCT_GRAPH.toml
                  (one writable graph truth)
                    /          |           \
                   v           v            v
        Owner HQ projection  narrative   Factory graph references
        and UI snapshots     projections  (read/reference only)
                   ^                          |
                   |                          v
          no reverse writes       factory/registry.toml
                                  (Factory runtime truth only)
                                           |
                                           v
                              immutable Factory evidence refs
                              proposed for a governed graph write
```

The allowed projection direction is from the canonical Product Graph to consumers. There MUST NOT be an automatic reverse synchronization path from Owner HQ, generated projections, Markdown, or `factory/registry.toml` into the graph.

Factory runtime evidence MAY flow toward a later Product Graph change only as an immutable, source-linked evidence reference or proposal processed through an approved repository Work Unit. That handoff is not synchronization and MUST NOT silently change a graph status, dependency, lock, or authority field.

## 3. Bootstrap migration and retirement

### 3.1 During migration

`docs/product/PRODUCT_GRAPH_BOOTSTRAP.toml` MUST remain a frozen, non-operational migration input until cutover. It MUST NOT be promoted in place into the permanent canonical graph and MUST NOT become writable runtime truth.

The migration implementation MUST read one verified bootstrap revision and deterministically create the candidate `docs/product/PRODUCT_GRAPH.toml`. The same bootstrap bytes, migration version, and inputs MUST produce byte-identical canonical output. The implementation MUST NOT infer new states, IDs, edges, locks, evidence, or authority from file order, UI presentation, wall-clock time, or undocumented defaults.

While the candidate canonical file is under validation, the bootstrap remains the sole input used by existing consumers. The candidate MUST NOT be used to drive product or Factory behavior before all cutover validations pass.

### 3.2 Exact retirement point

The bootstrap is retired as a writable or active input at one exact repository boundary: **the accepted cutover commit that simultaneously introduces the validated canonical graph, switches every Product Graph and Owner HQ consumer to that canonical path, updates deterministic validation and projection checks, and removes the bootstrap from all active loader, exporter, test-fixture, and documentation-input lists**.

That cutover commit MUST remove `docs/product/PRODUCT_GRAPH_BOOTSTRAP.toml` from the active working tree. Its last verified blob ID, source revision, and migration fingerprint MUST be recorded in the cutover evidence; Git history remains the immutable archive. From that commit onward, recreating, editing, or consuming the bootstrap as an input is prohibited. A later migration MUST start from the canonical graph, never from the retired bootstrap.

If the full cutover cannot occur atomically in one accepted commit, the bootstrap MUST remain active and the candidate canonical file MUST remain non-authoritative. There MUST NOT be a period in which both files accept coordinated or uncoordinated writes.

## 4. Factory registry boundary

`factory/registry.toml` MUST remain authoritative only for Software Factory runtime concerns required by the existing Factory behavior, including its runtime epic/task records, eligibility and dependency inputs, Work Unit context and capability declarations, Owner-decision records used by the Factory, and Factory-specific runtime status vocabulary.

The Factory registry MUST NOT own or override product-wide lifecycle stages, roadmap sequencing, Product Graph dependency semantics, domain/capability state, authority gates, capital locks, or Owner HQ truth. A Factory status does not automatically equal a Product Graph status, even when the records describe related work.

Factory-only fields that do not belong in the product-wide graph MUST remain in the Factory registry. Examples include Factory scheduling or eligibility inputs, estimated duration, runtime-specific capability lists, spec and acceptance paths, context classifications, Factory owner-gate reasons, and Factory execution records. Such fields MUST NOT be copied into the Product Graph merely to make the graph comprehensive.

Where a Factory record corresponds to or consumes an approved Product Graph entity, the Factory MAY store or receive its stable Product Graph ID as a read-only reference. A graph-derived Factory reference MUST:

- preserve the canonical ID exactly;
- resolve to exactly one canonical object of an allowed type;
- be rejected when missing, unknown, duplicated, type-incompatible, stale, or inconsistent with the approved Work Unit;
- contain no independently editable copy of graph-owned status, dependency, lock, or authority fields; and
- grant no Factory, product-change, trading, or capital authority.

The Product Graph MAY reference immutable Factory evidence by stable ID and exact evidence locator. It MUST NOT copy mutable Factory runtime state and then treat that copy as current Factory truth. Each side owns its own fields; shared meaning crosses the boundary through stable references and explicit validation, not dual ownership.

## 5. Stable IDs and relationship preservation

Every existing Product Graph ID MUST be preserved byte-for-byte during migration, including IDs for the product, baseline, locks, authority gates, Factory stages, domains, waves, epics, capabilities, tasks, Work Units, dependencies, and unknown-frontier items. Existing Factory IDs used as cross-boundary references, including `FACTORY-001A` and `FACTORY-001B`, MUST retain their spelling and meaning.

An ID MUST identify one conceptual object for its lifetime. Migration MUST NOT renumber, normalize, case-fold, recycle, or silently alias an ID. If a future schema needs a replacement object, it MUST use the existing supersession and evidence rules rather than repurpose the old ID. Any explicitly approved alias or mapping MUST be deterministic, one-to-one, versioned, and auditable; migration completion MUST NOT depend on a many-to-one or ambiguous mapping.

All existing dependency IDs, endpoints, directions, kinds, and dependency types MUST be preserved. The migrated graph MUST preserve reachability and acyclicity. Owner HQ and every generated projection MUST emit canonical IDs unchanged. A displayed label MAY differ for presentation, but it MUST NOT be used as identity.

Duplicate IDs, duplicate dependency pairs, unresolved endpoints, unknown IDs, unknown reference types, or type-incompatible references MUST fail validation. A projection is stale when its recorded canonical source revision or content digest does not match the canonical input, or when deterministic regeneration produces different bytes. Missing source identity or digest metadata MUST be treated as stale once the canonical projection contract requires that metadata.

## 6. Compatibility contract

The migration implementation MUST preserve the existing `product_graph` public API: exported names, query method signatures, return types, immutable read behavior, ID lookup behavior, dependency direction, lock queries, current/next-wave semantics, and fail-closed validation errors. Consumers MUST be switched to the new canonical location in the cutover commit without requiring a parallel writable compatibility file.

A compatibility adapter MAY translate the canonical file into the existing in-process model only if it reads the single canonical file and creates an in-memory or disposable generated projection. It MUST NOT persist a second editable Product Graph. Existing Owner HQ data flow MUST remain a deterministic read-only projection, and existing Factory execution behavior MUST remain unchanged.

Schema evolution MUST be explicit and versioned. Unknown required fields, unsupported schema versions, malformed structures, or lossy conversions MUST fail closed. Compatibility MUST NOT be achieved by ignoring an unknown authority, lock, dependency, or identity field.

## 7. Required validation before cutover

Before the canonical graph can replace the bootstrap, a later implementation Work Unit MUST produce passing deterministic evidence for all of the following:

1. **Source integrity:** record the exact bootstrap Git revision and blob/content digest used; confirm it is the reviewed migration input.
2. **Determinism:** run migration at least twice from identical inputs in clean temporary locations and prove byte-identical canonical outputs.
3. **Schema and vocabulary:** validate the declared schema version, closed required shape, allowed product status vocabulary, dependency kinds and types, and authority vocabularies without inventing new product statuses or authority levels.
4. **Identity:** prove global ID uniqueness, exact preservation of every source ID, no unexplained new or missing IDs, and exact resolution of all cross-file references.
5. **Relationships:** prove dependency IDs and endpoint pairs are preserved, every endpoint resolves, duplicate edges are rejected, dependency kind/type remains compatible with endpoint scope, mandatory dependencies remain present, and the graph remains acyclic.
6. **State and evidence:** prove W0=`DONE`, W1=`ACTIVE`, W2=`PLANNED`; FACTORY-001A/001B=`DONE`; FACTORY-001C/001D/001E=`LOCKED`; DONE objects retain evidence; and `TASK-W1-DESIGN-CANONICAL-GRAPH` plus `CAP-W1-GRAPH-MIGRATION` are not marked DONE merely by this contract.
7. **Authority:** prove Paper, Limited Live, Live, and all required authority gates remain locked and non-granting; prove `capital_authority = false`; reject missing, weakened, duplicated, unknown, or conflicting lock records.
8. **Factory boundary:** prove `factory/registry.toml` remains unchanged unless a separately approved Work Unit explicitly permits a compatible reference-field change; prove Factory-only fields remain Factory-owned; reject stale, missing, duplicate, unknown, or type-incompatible graph-derived references.
9. **Consumer compatibility:** run the existing Product Graph API tests and equivalent tests against the canonical path; prove ID queries, dependency traversal, current/next-wave results, locks, and failure behavior are unchanged.
10. **Projection integrity:** generate Owner HQ and other checked-in projections twice; prove byte identity, canonical source identity, unchanged stable IDs, current locks/authority, no reverse-write path, and no unexplained diff from the expected consumer contract.
11. **Repository scope:** prove the cutover diff contains only approved migration, consumer-path, validation, projection, test, and bootstrap-retirement changes; prove no Factory execution, trading, risk, release, operations, W2, or infrastructure behavior changed.
12. **Quality gates:** pass the repository self-check, focused Product Graph/export tests, the complete automated test suite, and every additional command required by the later implementation Work Unit's acceptance contract.

Validation MUST report all checked source revisions, input and output digests, exact commands, results, and artifact paths. A claim, visual inspection, or successful parse alone is insufficient evidence.

## 8. Migration sequence

The later implementation Work Unit MUST execute this sequence:

1. Freeze and fingerprint the reviewed bootstrap revision and record the pre-migration canonical repository state.
2. Define the canonical schema version and deterministic serialization rules without changing product meaning.
3. Generate a candidate `docs/product/PRODUCT_GRAPH.toml` from the frozen bootstrap in an isolated temporary location.
4. Compare IDs, relationships, statuses, evidence references, locks, authority values, and Factory boundary references against the frozen source.
5. Validate the candidate with fail-closed canonical validators and repeat the migration to prove byte determinism.
6. Run existing `product_graph` and Owner HQ consumers against the candidate through the compatibility seam; regenerate projections and validate stale/missing/duplicate/unknown-ID failures.
7. Assemble one cutover commit that installs the candidate, switches all consumers and validators, retires the bootstrap, and contains the required tests and evidence references.
8. Run all cutover validations against that exact commit candidate. If any check fails, do not accept or use the cutover.
9. Accept the cutover commit only after independent review confirms one writable truth, preserved semantics and IDs, unchanged Factory execution behavior, and unchanged locks and authority.
10. After acceptance, permit future graph writes only to `docs/product/PRODUCT_GRAPH.toml` through approved repository Work Units.

Steps 1–8 create no authority. Completion of migration does not complete W1 and does not unlock any Factory or capital stage.

## 9. Failure and rollback

Migration and projection operations MUST fail closed. If parsing, validation, ID resolution, relationship comparison, projection generation, compatibility testing, or evidence collection fails, then:

- the candidate canonical graph MUST NOT become authoritative;
- no partial output MAY replace a last verified artifact;
- no consumer MAY switch to the candidate;
- no Product Graph or Factory status, lock, dependency, or authority value MAY advance;
- the bootstrap MUST remain the active non-operational input if cutover has not been accepted; and
- the failure MUST be recorded with exact input revision, digests, command, error, and affected artifacts.

Before the cutover commit is accepted, rollback means discarding the candidate outputs and returning to the exact pre-migration verified repository revision. After cutover acceptance, rollback means reverting the whole cutover as one repository change to its recorded parent commit, then rerunning the pre-cutover validators and projection checks. Rollback MUST NOT selectively restore only the bootstrap, only a projection, or only a consumer path, because that would create a mixed-authority state.

The last verified repository commit is the rollback authority. Generated artifacts MAY be regenerated only from the authoritative source at that restored commit. If a clean whole-commit rollback cannot be established, the graph and its consumers MUST remain unavailable for state-changing use and the issue MUST be escalated as `NEEDS_OWNER`; Factory and capital locks remain unchanged.

## 10. Evidence required to declare migration complete

A later implementation Work Unit MAY declare the Product Graph migration complete only when all of the following evidence is attached to one exact accepted cutover commit:

- bootstrap source revision, blob/content digest, and migration-tool version;
- canonical graph path, schema version, content digest, and byte-determinism comparison;
- complete before/after ID inventory and dependency comparison with zero unexplained differences;
- explicit state, evidence, lock, authority, and Factory-boundary validation results;
- passing malformed, missing, stale, duplicate, unknown-ID, unknown-field, and cycle failure tests;
- passing public-API compatibility and Owner HQ deterministic projection tests;
- proof that every active consumer reads `docs/product/PRODUCT_GRAPH.toml` and no active consumer reads the bootstrap;
- proof that the bootstrap is absent from the active tree and recoverable through the recorded Git history;
- proof that only the canonical graph is writable and every projection is read-only/generated;
- exact quality-gate commands and results;
- independent code, security, risk, and applicable architecture review results with no unresolved blocking findings; and
- release verification for the migration Work Unit.

Migration completion MUST NOT be inferred from the presence of `PRODUCT_GRAPH.toml`, from a passing exporter alone, or from Owner HQ rendering successfully. It MUST NOT mark W1 complete unless every separate W1 acceptance requirement is also satisfied.

## 11. Non-goals and out of scope

This contract MUST NOT be interpreted as authorization to:

- implement this migration in `WU-W1-GRAPH-MIGRATION-CONTRACT`;
- change any current Product Graph, Factory registry, generated snapshot, application, test, or UI data;
- redesign Owner HQ or change its data flow;
- extend Factory execution, scheduling, autonomy, or runtime vocabulary;
- implement W2 Knowledge Platform or any trading strategy, bot, proving, risk, release, portfolio, or operations capability;
- introduce a database, graph database, network API, event bus, daemon, watcher, background sync, Codex transport, or App Server;
- add credentials, exchange or broker connectivity, order submission, Paper, Limited Live, Live, or capital authority;
- create a new product status, lifecycle stage, authority level, market, venue, credential model, or risk philosophy; or
- mark W1, `TASK-W1-DESIGN-CANONICAL-GRAPH`, or `CAP-W1-GRAPH-MIGRATION` DONE.

Any such work requires a separate approved specification, acceptance contract, Work Unit, and any applicable Owner gate.
