# {{WORK_ITEM}} — {{BOT_NAME}}

Status: DRAFT  
Owner: {{OWNER}}  
Target stage: DRY_RUN

## 1. Outcome

Describe the observable result, not the implementation.

## 2. In scope

- ...

## 3. Out of scope

- Live trading unless separately approved.

## 4. Actors and systems

| Actor/system | Responsibility | Trust boundary |
|---|---|---|
| ... | ... | ... |

## 5. Inputs and data contracts

Specify sources, schemas, timestamps, units, precision, freshness, duplicates, and malformed input behavior.

## 6. Behavioral scenarios

Use `Given / When / Then`, including rejection and recovery paths.

## 7. Risk and execution rules

Reference `governance/risk-policy.toml`. Restate only work-item-specific rules.

## 8. State machines

Define signal, order, position, and reconciliation states plus allowed transitions.

## 9. Non-functional requirements

Reliability, idempotency, latency, security, observability, backup, recovery, and retention.

## 10. Research and backtest protocol

Datasets, time splits, costs, baselines, leakage controls, metrics, and rejection thresholds.

## 11. Acceptance criteria

Link each item to a machine-readable ID in `acceptance.toml`.

## 12. Open decisions

No implementation begins while a capital-impacting decision remains open.

