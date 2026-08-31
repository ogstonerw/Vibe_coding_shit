# PRODUCT-MASTER-SPEC-V1 — execution and verification plan

## Sequence

1. Verify clean exact baseline and create `feature/product-master-spec-v1` locally.
2. Read only mandated/relevant current sources.
3. Run read-only pre-draft specialist reviews.
4. Draft the three product artifacts with one writer.
5. Add and run deterministic graph validation.
6. Run repository self-check and full unit discovery.
7. Run independent post-draft reviews against raw artifacts.
8. Resolve at most two correction loops, re-run affected and full gates.
9. Run release verifier last.
10. Create one local commit; do not push, open a PR or merge.

## Exact validation commands

```bash
python3 scripts/check_product_graph_bootstrap.py
python3 -m unittest tests.test_product_graph_bootstrap -v
python3 scripts/self_check.py
python3 -m unittest discover -s tests -v
```

No bot-specific formatter, linter, type checker, integration, replay or backtest command applies because no bot or runtime behavior is implemented.

## Evidence

Record exact command outcomes, reviewer verdicts, final diff, commit SHA and clean/expected git status. The bootstrap validator checks parsing, global ID uniqueness, reference resolution, acyclicity, W0–W12 coherence, baseline identity, future factory locks, capital locks and DONE evidence.
