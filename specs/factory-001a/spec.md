# FACTORY-001A — Daily Autonomous Development Control Plane

Status: OWNER_APPROVED
Owner: Repository Owner
Target stage: DETERMINISTIC_DRY_RUN

## 1. Outcome

A scheduled, deterministic control plane validates the development registry, selects at most one eligible `READY` task, writes an execution plan and Owner Report, and stops without invoking a coding agent or changing product code.

## 2. In scope

- Machine-readable EPIC, TASK, DEPENDENCY, OWNER DECISION, and RUN registry.
- Deterministic daily-run state machine and fail-closed preflight.
- Owner-approved Epic decomposition contract.
- Owner decision gate for product, architecture, authority, governance, market, exchange, credential, Paper, and Live changes.
- Dry-run CLI and daily 10:00 Europe/Moscow GitHub Actions schedule.
- Owner control-plane documents and token-aware context classification.

## 3. Out of scope

- OpenAI or Codex invocation.
- Automatic writer, commit, push, pull request, merge, or product approval.
- Telegram or Bitget API access, credentials, orders, positions, fills, Paper, Live, or legacy execution.
- Any change to financial semantics, risk limits, lifecycle authority, market, or exchange scope.

## 4. Actors and systems

| Actor/system | Responsibility | Trust boundary |
|---|---|---|
| Owner | Approves WHAT, WHY, scope, authority, and governance | Only actor allowed to resolve Owner gates |
| Daily runner | Validates and plans one bounded task | Deterministic local code; no LLM or network |
| Registry | Versioned state and dependencies | Invalid or ambiguous input stops the run |
| GitHub Actions | Triggers the dry-run at 07:00 UTC | Read-only repository permission; no secrets |

## 5. Inputs and data contracts

- `factory/registry.toml` contains versioned entities with unique IDs and enumerated statuses.
- `factory/daily_run.toml` contains immutable limits, active frozen manifests, governance hashes, and routing guidance.
- Paths are repository-relative and cannot escape the repository root.
- Text evidence hashes use canonical UTF-8 with LF line endings; binary artifacts use raw bytes.
- The dry-run writes deterministic JSON and Markdown artifacts below the configured output directory.

## 6. Behavioral scenarios

- Given one eligible `READY` task, when preflight passes, then exactly that task is selected by `(priority, id)` and a plan/report pair is written.
- Given no `READY` task, then the run stops as `NO_WORK` and reports no selected task.
- Given an active run, unresolved Owner decision, invalid dependency, missing contract, dirty repository, exceeded budget, or changed frozen/governance evidence, then the run fails closed.
- Given a proposed decomposition outside the approved Epic capability set, then no child task is created and Owner review is required.
- Given any invalid state transition, then the state machine rejects it.

## 7. Risk and execution rules

`governance/risk-policy.toml` and trading execution are read-only evidence. FACTORY-001A never imports or calls Telegram, exchange, trading, order, position, fill, Paper, or Live code. `auto_merge`, product approval, Paper authority, and Live authority remain false.

## 8. State machines

Success path: `SCHEDULED -> PREFLIGHT -> TASK_SELECTED -> PLAN_CREATED -> REPORT_CREATED`.

Stop states: `NO_WORK`, `BLOCKED`, `NEEDS_OWNER`, `FAILED`. Stop states are terminal; report serialization does not transition out of them.

## 9. Non-functional requirements

- Standard-library-only Python 3.12 implementation.
- Stable ordering and serialized output for reproducibility.
- Atomic artifact replacement.
- At most one selected task per run and one active run in the registry.
- No secret values, outbound network calls, subprocess-based agents, or production side effects.

## 10. Research and backtest protocol

Not applicable. Financial and strategy semantics are unchanged; no performance claims or backtests are introduced.

## 11. Acceptance criteria

Machine-readable criteria `FACTORY-AC-001` through `FACTORY-AC-012` are defined in `acceptance.toml` and traced by focused tests.

## 12. Open decisions

FACTORY-001B remains `NEEDS_OWNER`: automatic Codex invocation, writer execution, commit, push, PR, and merge are not authorized.

The frozen evidence conflict is resolved through the Owner-approved operational PM bundle V2. Historical PM V1 and core V11 remain unchanged; active PM V2 verifies active core V12 without changing PM-DEC-007 semantics or authority.
