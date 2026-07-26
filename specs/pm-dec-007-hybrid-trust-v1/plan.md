# PM-DEC-007 hybrid trust addendum — plan

Status: `PARTIALLY_RESOLVED_ARCHITECTURE_ONLY / NON_AUTHORIZING`.

## Phase 1 — Freeze the owner choice

- Record the selected physical-key + separate-device architecture.
- Bind it to frozen parent v11 and immutable governance/decision hashes.
- Keep exact algorithms, providers, recovery, numeric values and runtime open.
- Preserve Pilot/Production/live/real capital as `BLOCKED/DENY`.

Evidence: `spec.md`, `decisions/PM-DEC-007.toml`, `PM-AC-059`.

## Phase 2 — Specify failure boundaries

- Close the seven independence dimensions.
- Bind both factors to the same exact opaque payload bytes and locally
  recomputed SHA-256; do not parse or canonicalize payloads.
- Reject caller validity/independence/currentness booleans.
- Separate checkpoint shape from checkpoint authority.
- Preserve terminal revocation/no one-factor recovery semantics.

Evidence: `PM-REQ-094…096`, `PM-AC-060…061`.

## Phase 3 — Add only non-authorizing validators

- Validate exact decision record and immutable hash bindings.
- Validate equality of two opaque bytes values, locally recomputed SHA-256 and
  the exact closed typed factor shapes; do not parse or canonicalize payloads.
- Return explicit non-authorizing factor-shape results.
- Return explicit `DENY` for every caller-supplied checkpoint claim.
- Keep authority readiness unconditionally fail-closed and adapter-spy silent.

Evidence: standalone validator and adversarial unit tests.

## Phase 4 — Independent review

- Fresh institutional, quant-methodology and market-microstructure spec review.
- One implementer only.
- Test engineer review.
- Independent code, security and risk review against one frozen diff.
- Final fresh deep review and release verifier.

## Phase 5 — Package the partial decision

- Create a closed non-authoritative addendum snapshot.
- Create a dedicated frozen manifest without modifying frozen v11.
- Update handoff/token protocol.
- Package factory v0.20.

## Deferred integration

Do not merge the addendum into the parent portfolio mandate until exact
cryptography, canonicalization, providers, enrollment/recovery, clock/freshness,
numeric owner values and runtime verifier/checkpoint are approved and evidenced.
That later integration requires a new versioned parent decision/rebinding
release; frozen v11 and `PM-DEC-003` are never rewritten.

## Verification

```bash
python3 scripts/check_pm_dec007_hybrid.py
python3 -m unittest tests.test_pm_dec007_hybrid -v
python3 scripts/self_check.py
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/check_pm_dec007_hybrid.py tests/test_pm_dec007_hybrid.py
sha256sum -c docs/FROZEN_CORE_V11.sha256
```
