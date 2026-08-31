# FACTORY-001B — Controlled Coding-Agent Execution

Status: IMPLEMENTATION
Owner: Repository Owner
Target stage: CONTROLLED_GOAL_MODE
Product change authority: PRODUCT_CHANGE_LEVEL_A

## 1. Outcome

The accepted FACTORY-001A control plane can execute at most one concrete,
Owner-approved Work Unit through a provider-neutral coding-agent boundary,
run bounded tests and focused reviews, preserve durable evidence, generate a
compact Owner Report, and stop with an inspectable working-tree candidate.

The Owner authorization dated 2026-08-31 unlocks only FACTORY-001B and one
local candidate commit for this Work Unit. It does not authorize push, pull
request, merge, product approval, credentials, trading, Paper, Limited Live,
Live, capital, or exchange/broker execution.

## 2. In scope

- A strict, machine-readable `WorkUnit` contract linked to an existing Task
  and Epic in the current FACTORY registry.
- Canonical fail-closed eligibility, repository, integrity, dependency,
  authority, context, scope, concurrency, test, review, and correction gates.
- A bounded Context Compiler using MANDATORY, RELEVANT, FROZEN, and SKIP
  classes.
- Provider-neutral coding and review adapter protocols, deterministic fakes
  for tests, and an explicit `NOT_CONFIGURED` production default.
- Structured-argv test execution with a fixed repository cwd, timeout,
  sanitized environment, captured exit code, and output digests.
- Atomic JSON evidence and Markdown Owner Report artifacts.
- FACTORY-001A lock reuse and unchanged one-task scheduling behavior.

## 3. Out of scope

- A paid or credentialed Codex/model transport.
- Automatic commit, push, pull request, merge, release, or product approval.
- FACTORY-001C three-slot scheduling, FACTORY-001D Git delivery, or
  FACTORY-001E realtime UI.
- Mutable Product Graph runtime migration.
- Telegram, broker, exchange, order, position, fill, Paper, Limited Live,
  Live, risk-policy, credential, or capital behavior.
- Cryptographic signing infrastructure or external trust roots.

## 4. Architecture and trust boundaries

`factory.execution.execute_work_unit` is the public orchestration boundary.
It loads the canonical `factory/registry.toml` and `factory/daily_run.toml`,
probes Git and frozen/governance evidence itself, and holds the existing
FACTORY OS lock from preflight through evidence creation. Test seams are
private and cannot replace production evidence.

The Work Unit is a command/data contract, not authority. The control plane
decides eligibility and allowed changes before invoking any adapter. A
`CodingAgentAdapter` receives only the validated Work Unit, compiled context,
repository start state, and bounded correction findings. It cannot approve
the Epic, Task, authority level, paths, tests, reviews, or final verdict.

Review adapters are selected only from the Work Unit's requested roles and
budget. Missing optional reviewers are recorded and skipped without fallback;
a missing required reviewer blocks PASS. No adapter transport is configured
by default.

The Product Graph bootstrap stays a non-operational future migration input.
FACTORY-001B uses the existing registry for Epic, Task, dependency, active-run,
and Owner-decision truth, while the Work Unit contract supplies execution-only
detail linked by `epic_id` and `task_id`.

## 5. Work Unit contract

The strict TOML contract rejects unknown fields and requires:

- `id`, `task_id`, `epic_id`, `goal`, `status`, `authority_level`;
- explicit `allowed_paths` and `forbidden_paths`;
- `mandatory_context`, plus bounded RELEVANT/FROZEN/SKIP context classes;
- non-empty `acceptance_criteria`, `required_tests`, and
  `evidence_requirements`;
- `required_reviews`, optional reviews, reasoning/context/review budgets;
- `max_correction_loops`, `dependencies`, and NORMAL/LARGE routing class.

Paths are normalized repository-relative POSIX paths. Absolute paths,
traversal, ambiguous segments, duplicate paths, class overlaps, and an allowed
path contained by a forbidden or built-in sensitive scope are rejected.
`context_budget` is a deterministic UTF-8 byte budget. FROZEN context consumes
only identity/hash/size metadata; SKIP content is never loaded.

## 6. Behavioral scenarios

- An eligible READY LEVEL_A Work Unit can reach writer execution when a real
  configured adapter is supplied.
- LEVEL_B and LEVEL_C stop as `NEEDS_OWNER` before adapter invocation.
- Missing/non-READY Task, non-approved Epic, incomplete dependency, missing
  acceptance, missing allowed scope, unresolved context, dirty/unknown Git,
  integrity mismatch, active run, or unavailable correction budget fails
  closed.
- The existing OS lock permits one writer owner only.
- A fake caller cannot override canonical production probes.
- Context excludes SKIP, summarizes FROZEN, and blocks on byte-budget excess.
- Any changed path outside allowed scope or inside forbidden/sensitive scope
  blocks immediately and remains inspectable; no destructive recovery occurs.
- Test or required-review failure prevents PASS. Corrections stop after at
  most two loops and rerun tests plus only affected blocking reviewers.
- PASS writes durable context, diff, test, review, result, and Owner Report
  evidence and performs no Git delivery action.
- With the default adapter, no execution is claimed: status is
  `NOT_CONFIGURED` and no product file is changed.

## 7. Risk and execution rules

Only `PRODUCT_CHANGE_LEVEL_A` is executable. Product Change Level B or C is
`NEEDS_OWNER`; these labels never grant capital authority. Built-in sensitive
paths include `.github/`, `governance/`, frozen evidence, credential-like
files, and trading/exchange execution scopes. They are denied for this stage
even if a LEVEL_A contract attempts to allow them.

Required test commands use a small executable/module allowlist and
`subprocess` with `shell=False`, explicit argv, cwd, timeout, and sanitized
environment. Work Unit text is never concatenated into a shell command.

The factory records but does not automatically reset, clean, commit, push, or
open a pull request. Trading/exchange modules are neither context nor command
targets for this Work Unit. Paper, Limited Live, Live, and capital remain
false/locked.

## 8. State and evidence models

Execution states are local to Work Unit execution:

`READY -> PREFLIGHT -> ACTIVE -> TESTING -> REVIEW -> PASS`

Terminal alternatives are `FAIL`, `BLOCKED`, `NEEDS_OWNER`, and
`NOT_CONFIGURED`. These states do not alter unrelated registry vocabularies.

`ExecutionResult` records Work Unit/run identity, timestamps, status,
created/changed/deleted paths, tests and reviews, context and expansions,
correction-loop count, diff statistics, evidence references, blockers, and
Owner decisions required. Artifact payloads use deterministic ordering and
atomic replacement. Command output is represented by bounded metadata and
SHA-256 digests rather than blindly persisted raw output.

## 9. Agent and correction budgets

- NORMAL Work Unit: at most two reviewer invocations.
- LARGE/architecture Work Unit: at most four reviewer invocations.
- Absolute contract maximum: five.
- A correction reruns only reviewers with blocking findings.
- `max_correction_loops` is at most two.
- No automatic fallback reviewer is spawned.

Reasoning classes are `LOW`, `MEDIUM`, `HIGH`, and `XHIGH`; the contract must
choose one, and the router does not silently increase it.

## 10. Recovery and concurrency

Before writer execution the factory records starting HEAD, Git status, and
allowed paths. The FACTORY-001A persistent OS lock is held for the whole run.
On failure the diff and evidence are preserved. `git reset --hard` and
`git clean -fd` are never called.

## 11. Acceptance criteria

Machine-readable criteria `FACTORY-001B-AC-001` through
`FACTORY-001B-AC-026` are defined in `acceptance.toml` and traced in
`tasks.md` and focused tests.

## 12. Open decisions

- A production coding/model transport remains `NOT_CONFIGURED`.
- Fresh Ubuntu CI is required after the authorized local commit before
  FACTORY-001B can become accepted.
- FACTORY-001C, FACTORY-001D, and FACTORY-001E remain locked.
- Paper, Limited Live, Live, capital, credentials, and exchange/broker
  execution remain locked.
