# Owner Decision Log

## FACTORY-DEC-001 — Controlled core re-freeze

- Date: 2026-08-11
- Status: APPROVED
- Reason: UI product-development agents are now mandatory parts of the agent factory.
- Decision: `game_ux_designer` and `pro_trader_ux` are required, read-only agents with high reasoning effort.
- Freeze: `FROZEN_CORE_V11` remains an immutable historical baseline. `FROZEN_CORE_V12` is the active core freeze.
- Authority unchanged: this decision grants no Paper, Live, credential, exchange, order, or financial authority.

## FACTORY-DEC-002 — FACTORY-001A authority boundary

- Date: 2026-08-11
- Status: APPROVED
- Decision: the daily runner may validate, select, plan, and report one `READY` task.
- Limit: it cannot invoke Codex or another writer, change product scope, commit, push, create a pull request, merge, or grant trading authority.
- Next gate: FACTORY-001B requires a separate Owner decision.

## FACTORY-DEC-003 — Frozen parent compatibility conflict

- Date: 2026-08-11
- Status: RESOLVED / OWNER_APPROVED
- Evidence: V12 passes `10/10`, while frozen PM-DEC-007 V1 tests require V11 to pass `10/10` with the old `scripts/self_check.py` hash.
- Constraint: one file cannot match both the V11 and V12 hash.
- Resolution: PM-DEC-007 V1 is preserved as historical. PM-DEC-007 V2 is the active operational bundle and verifies active core V12.
- Reason: the approved agent architecture added mandatory `game_ux_designer` and `pro_trader_ux` roles to core V12.
- PM semantics and authority remain unchanged. Paper, Live, agents, commits, pushes, pull requests, and merge remain blocked.

## FACTORY-DEC-004 — FACTORY-001A release-blocking hardening only

- Date: 2026-08-11
- Status: OWNER_APPROVED
- Decision: correct only the five reviewed FACTORY-001A release blockers: lock ownership, durable daily history, `READY` authority, production trust-boundary injection, and workflow action pinning.
- Release state: FACTORY-001A remains `REVIEW` until the required independent reviews and release verification pass.
- Explicit exclusions: this decision grants no FACTORY-001B, Product Master Spec, coding-agent execution, trading-code, credential, Paper, Live, capital, commit, push, pull-request, merge, or risk-policy authority.
- Frozen evidence: no frozen manifest is changed by this decision.
