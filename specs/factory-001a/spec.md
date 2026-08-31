# FACTORY-001A — Daily Autonomous Development Control Plane

Status: REVIEW
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
| Daily runner | Validates and plans one bounded task | Deterministic standard-library code; only the GitHub Actions history witness may use network |
| Registry | Versioned state and dependencies | Invalid or ambiguous input stops the run |
| GitHub Actions | Triggers the dry-run at 07:00 UTC and supplies its own history witness | `contents: read` plus `actions: read`; built-in token is used only for the workflow-history GET |

## 5. Inputs and data contracts

- `factory/registry.toml` contains versioned entities with unique IDs and enumerated statuses.
- `factory/daily_run.toml` contains immutable limits, active frozen manifests, governance hashes, and routing guidance.
- Production resolves only those exact two repository-rooted paths; neither the public API nor CLI accepts a replacement registry or configuration path. Alternate paths exist only on the explicitly private deterministic test seam.
- `repository.allowed_dirty_prefixes` is exactly the singleton `["factory/artifacts/"]`; empty, arbitrary, duplicate, additional, or broader prefixes are invalid configuration.
- Production lock, daily claim, plan, and report paths are fixed below `factory/artifacts/`; the public runner, public lock/claim helpers, daily CLI, and standalone claim CLI accept no alternate output namespace. Alternate namespaces exist only on explicitly private test seams. The public entry point owns the OS lock across claim and selection.
- Paths are repository-relative and cannot escape the repository root.
- Text evidence hashes use canonical UTF-8 with LF line endings; binary artifacts use raw bytes.
- The dry-run writes deterministic JSON and Markdown artifacts below the canonical `factory/artifacts/` directory.
- `factory/artifacts/run-history/YYYY-MM-DD.json` is the canonical immutable daily claim. It contains only schema version, Moscow production date, and stable owner ID, and is created with exclusive filesystem semantics.
- The persistent local lock file is opened without truncation and is never unlinked, renamed, or truncated during normal release. Ownership is only the continuously held nonblocking OS lock on the live file handle: `flock` on POSIX and a one-byte `msvcrt.locking` region on Windows. File contents have no authority.

## 6. Behavioral scenarios

- Given one eligible `READY` task, when preflight passes, then exactly that task is selected by `(priority, id)` and a plan/report pair is written.
- Given no `READY` task, then the run stops as `NO_WORK` and reports no selected task.
- Given an active run, unresolved Owner decision, invalid dependency, missing contract, dirty repository, exceeded budget, or changed frozen/governance evidence, then the run fails closed.
- Given a proposed decomposition outside the approved Epic capability set, then no child task is created and Owner review is required.
- Given any invalid state transition, then the state machine rejects it.
- Given a `READY` task, its referenced Epic must exist and be exactly `OWNER_APPROVED`, its capabilities must be a subset of that Epic's approved capabilities, all referenced contracts/context evidence must exist, and all dependencies must be valid and complete. A direct `READY` edit bypasses none of these checks.
- Given an existing canonical daily claim for the same owner and Moscow date, retry is allowed without rewriting the claim; a different owner or malformed claim blocks before selection. A different date has an independent claim.
- Given a concurrent lock attempt, the losing process cannot acquire or release the winner's live handle lock; after the winner unlocks and closes, another process can acquire the persistent path. Unsupported or ambiguous acquire/release behavior fails closed.
- Given direct public API use, the same canonical lock and daily-claim namespace applies as the CLI: alternate output namespaces are rejected, a competing public run cannot enter the critical section, same-owner retry remains idempotent, and another owner on the same date is denied.
- Given a tracked path renamed or copied into `factory/artifacts/`, NUL-delimited Git status parsing preserves and checks both source and destination exactly, including spaces and special characters; an outside source remains disallowed and blocks before selection.
- Given GitHub Actions execution, the runner must first witness its exact current run in the workflow-specific, branch-scoped Actions API history, must be attempt 1, and must find no prior scheduled or manually dispatched run started on the same Moscow date. Any prior started run consumes the date regardless of success, failure, cancellation, or in-progress status.
- Given metadata or history API failure, non-2xx response, timeout, malformed/contradictory response, inactive or path-mismatched workflow metadata, unresolved numeric workflow ID, missing/inconsistent current-run witness, or truncated bounded pagination, the GitHub run stops before local claim or task selection. Candidate `path` is non-authoritative and ignored; workflow identity is the resolved numeric `workflow_id`, while repository and `head_branch` are independently required to match the trusted scope.
- Given the public runner or dry-run CLI, configuration, registry, and output namespace always come from the exact canonical repository paths and repository/integrity evidence always comes from the canonical probes. Fabricated path, dirty-allowlist, output-namespace, or probe overrides are not accepted by the public interface.

## 7. Risk and execution rules

`governance/risk-policy.toml` and trading execution are read-only evidence. FACTORY-001A never imports or calls Telegram, exchange, trading, order, position, fill, Paper, or Live code. `auto_merge`, product approval, Paper authority, and Live authority remain false.

## 8. State machines

Success path: `SCHEDULED -> PREFLIGHT -> TASK_SELECTED -> PLAN_CREATED -> REPORT_CREATED`.

Stop states: `NO_WORK`, `BLOCKED`, `NEEDS_OWNER`, `FAILED`. Stop states are terminal; report serialization does not transition out of them.

## 9. Non-functional requirements

- Standard-library-only Python 3.12 implementation.
- Stable ordering and serialized output for reproducibility.
- Atomic artifact replacement.
- Atomic exclusive lock and daily-claim creation on Windows and Linux.
- At most one selected task per run and one active run in the registry.
- No secret values are logged or persisted. No LLM, trading, exchange, Telegram, or arbitrary network calls are allowed; the sole outbound call is the bounded read-only GitHub workflow-history witness inside GitHub Actions.
- Every `actions/*` workflow dependency is pinned to an Owner-reviewed full commit SHA; checkout persistence of GitHub credentials is disabled.

## 9.1 Lock and durable daily-history operational boundaries

Outside `GITHUB_ACTIONS`, the immutable local claim is authoritative across separate local processes: the same owner may retry, another owner on the same Moscow date is denied, and malformed state fails closed. The persistent lock prevents concurrent local critical sections on one trusted filesystem. Administrative replacement of the lock path is a trusted-filesystem boundary: POSIX can give the replacement a different inode, but the old holder still unlocks only its original live handle and never deletes or releases the replacement holder.

Inside GitHub Actions, the workflow-history API witness is authoritative and must succeed before the local claim and selection. Context and bearer token come only from trusted GitHub environment variables. Only branch refs are allowed: `GITHUB_REF` must be `refs/heads/<branch>`, must agree with `GITHUB_REF_NAME`, and `GITHUB_REF_TYPE`, when present, must be `branch`. `GITHUB_WORKFLOW_REF` must equal `GITHUB_REPOSITORY/.github/workflows/daily-factory-control-plane.yml@GITHUB_REF` exactly. The runner resolves `GET /repos/{repo}/actions/workflows/daily-factory-control-plane.yml`, requires strict successful metadata with a positive non-boolean numeric ID, canonical path, and active state, then queries history only through `/actions/workflows/{numeric_id}/runs` with the encoded trusted short branch. Every run must repeat that numeric `workflow_id`, repository, and `head_branch`. Candidate `path` is never parsed or used for authority. The API calls use explicit GitHub headers, bounded timeout/body/pages, strict unique-key JSON/field/timestamp parsing, and never log token, headers, or bodies. The current run must be completely witnessed before exact-ID exclusion; `GITHUB_RUN_ATTEMPT > 1` is denied before any API call. Administrative deletion or falsification of GitHub Actions history is a trusted-administrator boundary.

The exact repository/ref/date cache is optional transport for the local claim only. A cache hit, miss, save, loss, or restored file does not prove workflow-history freshness and does not grant selection authority. Cache restore may precede the runner and cache save may follow a successful run; the API witness remains mandatory for both schedule and manual dispatch.

## 10. Research and backtest protocol

Not applicable. Financial and strategy semantics are unchanged; no performance claims or backtests are introduced.

## 11. Acceptance criteria

Machine-readable criteria `FACTORY-AC-001` through `FACTORY-AC-017` are defined in `acceptance.toml` and traced by focused tests.

## 12. Open decisions

FACTORY-001B remains `NEEDS_OWNER`: automatic Codex invocation, writer execution, commit, push, PR, and merge are not authorized.

The frozen evidence conflict is resolved through the Owner-approved operational PM bundle V2. Historical PM V1 and core V11 remain unchanged; active PM V2 verifies active core V12 without changing PM-DEC-007 semantics or authority.

FACTORY-DEC-004 authorizes only the five release-blocking FACTORY-001A hardening corrections. FACTORY-001A remains `REVIEW`; FACTORY-001B and all Product Master Spec, coding-agent, trading, credential, Paper, Live, capital, commit, push, pull-request, merge, frozen-manifest, and risk-policy authority remain unchanged and excluded.
