# Repository instructions for AI agents

## Mission

Build auditable trading-bot software from versioned specifications. Optimize for correctness, capital safety, reproducibility, and evidence. A plausible answer is not evidence.

## Sources of truth

Use this precedence order:

1. `governance/approval-policy.toml` and `governance/risk-policy.toml`.
2. The active work item's `spec.md` and `acceptance.toml`.
3. Accepted architecture decisions in `docs/`.
4. Existing code and tests.
5. Agent assumptions, which must be labeled and must never override 1–4.

If sources conflict, stop implementation, record the conflict, and request an owner decision. Never silently choose a financially riskier interpretation.

## Mandatory workflow

For a new bot or financially meaningful change, the root agent must orchestrate these stages:

1. Run `requirements_analyst` and `quant_researcher` in parallel. They return structured findings only.
2. Run `system_architect` after the specification is coherent.
3. Root agent writes or updates `spec.md`, `plan.md`, `tasks.md`, and `acceptance.toml`.
4. For every new bot, strategy, venue, capital stage, or financially meaningful design, run `institutional_portfolio_reviewer`, `quant_methodology_reviewer`, and `market_microstructure_reviewer` in fresh isolated contexts. Resolve every BLOCKER/HIGH finding before implementation.
5. Run one `implementer` at a time. Parallel write-heavy implementation is prohibited.
6. Run `test_engineer` after implementation.
7. Run `code_reviewer`, `security_reviewer`, and `risk_reviewer` in parallel against the same diff.
8. Re-run the applicable deep expert reviewers against the final evidence, not the author's summary.
9. Send actionable findings back to one `implementer`; repeat verification after fixes.
10. Run `release_verifier` last. It may issue `PASS`, `FAIL`, or `BLOCKED`; it cannot waive a failed gate.

Maximum nesting depth is one. Subagents do not spawn subagents.

Deep reviewers are independent second-line functions. They read raw artifacts before author conclusions, do not edit the object under review, and do not close their own findings. Agreement among agents never substitutes for deterministic evidence or owner authorization.

## Safety invariants

- Never enable live trading, submit a real exchange order, or use production credentials.
- Never read, print, log, commit, or request secret values. Use environment-variable names and fakes.
- Never change risk limits, leverage boundaries, margin mode, allowed symbols, or approval rules without explicit human approval recorded in the work item.
- Default to fail-closed: malformed signals, stale prices, missing stops, incomplete exchange responses, uncertain account state, and duplicate events must not create orders.
- Backtest results never prove live profitability. Do not present simulated performance as guaranteed or expected return.
- Every order-intent path requires idempotency, bounded retries, reconciliation, and an auditable event trail.
- Financial calculations use decimal/fixed-point arithmetic, never binary floating point.

## Engineering rules

- Keep exchange, Telegram, strategy, risk, execution, storage, and notification concerns behind explicit interfaces.
- Pin external API versions and record the official documentation date used.
- Add tests for both the requested behavior and its failure modes.
- Prefer deterministic code for parsing, sizing, risk checks, and order state transitions. An LLM may propose code but must not sit in the live order-decision path.
- Do not optimize strategy parameters on the holdout period. Record fees, funding, slippage, latency, missing data, and survivorship/look-ahead assumptions.
- Preserve user changes and unrelated work.

## Required verification

Run before declaring completion:

```bash
python3 scripts/self_check.py
python3 -m unittest discover -s tests -v
```

For an implemented bot, also run the project-specific formatter, linter, type checker, unit tests, integration tests, replay tests, and backtest commands documented in its `plan.md`. Report exact commands and outcomes.

## Definition of done

A change is done only when:

- the specification and acceptance contract describe the final behavior;
- code traces to task and acceptance IDs;
- all automated gates pass;
- independent code, security, and risk reviews have no unresolved blocking findings;
- paper/DRY_RUN evidence is attached when execution behavior changed;
- release verifier returns `PASS`;
- live activation remains disabled unless the owner separately approves it.

## Review guidelines

Prioritize correctness defects, unsafe capital exposure, auth/secret leakage, duplicate orders, race conditions, stale data, precision/rounding, incomplete reconciliation, and test gaps. Cite file and line, show the failure scenario, severity, and a concrete fix. Do not dilute high-confidence findings with style commentary.
