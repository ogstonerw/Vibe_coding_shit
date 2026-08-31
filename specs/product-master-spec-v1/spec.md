# PRODUCT-MASTER-SPEC-V1 — governed documentation work item

Status: **ACTIVE — DOCUMENTATION / ARCHITECTURE ONLY**

## Objective

Create the authoritative Product Master Spec, Living Master Roadmap and deterministic non-operational Product Graph bootstrap for the AI Trading Operating System on the accepted FACTORY-001A baseline.

## Sources

1. Current Owner direction for stage 4/5.
2. `governance/approval-policy.toml` and `governance/risk-policy.toml`.
3. This work item and `acceptance.toml`.
4. Accepted current architecture/Owner decisions identified in the Owner context.

The current Owner direction supersedes the older repository snapshot that still labels FACTORY-001A `REVIEW`; runtime factory files remain unchanged.

## Required behavior

- Satisfy `PMS-REQ-001..020` in `docs/product/PRODUCT_MASTER_SPEC.md`.
- Define W0–W12 and Unknown Frontier with the complete Wave contract in `docs/product/MASTER_ROADMAP.md`.
- Encode Product, Domains, Waves, initial Epics, hierarchy examples, dependencies, authority and locks in `docs/product/PRODUCT_GRAPH_BOOTSTRAP.toml`.
- Mark the bootstrap non-operational and require W1 migration into one canonical Product Graph.
- Preserve three-pipeline separation, one-Owner control, dual views over one truth, agent/bot distinction, exact version binding, evidence lineage, learning modes and controlled evolution.
- Keep FACTORY-001B–001E, Paper, Limited Live, Live and capital authority locked.

## Authority and non-goals

This work item authorizes only repository documentation and the tiny deterministic bootstrap validator/test. It does not authorize product-domain implementation, scheduler changes, FACTORY-001B, network access, credentials, broker/exchange integration, orders, Paper, Limited Live, Live, portfolio allocation or capital.

## Deliverables

- `docs/product/PRODUCT_MASTER_SPEC.md`
- `docs/product/MASTER_ROADMAP.md`
- `docs/product/PRODUCT_GRAPH_BOOTSTRAP.toml`
- `scripts/check_product_graph_bootstrap.py`
- `tests/test_product_graph_bootstrap.py`
- this work item's `spec.md`, `plan.md`, `tasks.md` and `acceptance.toml`

## Review contract

One root writer owns all changes. Every specialist is read-only. Final raw artifacts receive independent requirements, architecture, World UX, Operations UX, quant methodology, market microstructure, institutional portfolio, risk/authority, security/authority, test and code review. No unresolved BLOCKER/HIGH finding may remain. Regular correction loops are limited to two. The Owner explicitly authorized exceptional correction loop #3 on 2026-08-28, scoped only to Product Graph validator and test hardening. Release verification runs last.
