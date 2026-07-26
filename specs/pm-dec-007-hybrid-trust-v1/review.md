# PM-DEC-007 hybrid trust addendum — review evidence

Date: 2026-07-24  
Scope: `PM-REQ-094…096 / PM-AC-059…061`  
Authority result: `NONE`  
Pilot / Production / live / real capital: `BLOCKED / DENY`

## Frozen parent evidence

- `docs/FROZEN_CORE_V11.sha256` SHA-256:
  `46f20183230d84f6fdaba9ccc63e8e504afcd2be77c4447c66a14f5a9be5390f`.
- Parent entries: `10/10 OK`.
- Immutable `PM-DEC-003 v1` SHA-256:
  `618dd1da08fb6a8f7f0631fa6824bea1cc527d071e035b20b9250bcd374789ce`.
- Governance approval/risk policies remain byte-identical.

## Pre-implementation review

Fresh institutional, quant-methodology and market-microstructure reviews first
returned `FAIL` because the draft simultaneously left Level-B canonicalization
unresolved and required rejection of noncanonical bytes. The corrected contract:

- treats payloads as opaque bytes;
- requires byte-for-byte equality and locally recomputed SHA-256;
- does not parse or canonicalize the Level-B payload;
- does not claim stateless replay/freshness detection;
- gives no checkpoint shape-success result;
- records commit-time/checkpoint/CAS/outbox behavior only as future runtime work.

All three reviewers then returned `PASS`.

## Implementation and adversarial tests

One persistent implementer created:

- `scripts/check_pm_dec007_hybrid.py`;
- `tests/test_pm_dec007_hybrid.py`.

The validator can return only non-authorizing shape results or `DENY`.
Checkpoint claims and authority readiness always return `DENY`; supplied adapter
callbacks are never invoked.

Test engineer result:

- final focused suite: `33/33 PASS`;
- final full repository suite: `76/76 PASS`;
- final direct correction reproductions: hostile-key equality callbacks `0`;
- self-check, compile and frozen-parent validation: `PASS`.

## Independent code, security and risk review

Two correction cycles closed four reproducible MEDIUM robustness findings:

1. exact `str` type was not initially required for dictionary keys;
2. malformed decision TOML could escape through decode/value errors;
3. hostile non-string keys could execute equality before early denial;
4. invalid UTF-8 in the frozen-parent manifest could escape deterministic CLI
   failure handling.

Final code, security and risk verdicts: `PASS`; unresolved MEDIUM+ findings:
`NONE`.

Final validator/test SHA-256:

- validator:
  `004bf6617ca93e45bede5f338f3cf291d636e0c62815893b63d02b316a14e89e`;
- tests:
  `bdd597e6753eb4b2fa5f63eb54c77988374d3642b86f98a1c93f92da41852c5d`.

## Fresh deep evidence review

Fresh isolated institutional, quant-methodology and market-microstructure
reviewers read the final raw artifacts and returned `PASS`; unresolved MEDIUM+
findings: `NONE`.

The evidence supports only:

`PARTIALLY_RESOLVED_ARCHITECTURE_ONLY / NON_AUTHORIZING`.

It does not establish signature validity, device/root independence, checkpoint
currentness, trusted clock, runtime persistence, recovery ceremony, numeric
validity profiles, stage promotion or real-capital authority.

## Final deterministic gates before release verifier

```text
python3 scripts/check_pm_dec007_hybrid.py       PASS
python3 -m unittest tests.test_pm_dec007_hybrid -v
                                                33/33 PASS
python3 scripts/self_check.py                   PASS
python3 -m unittest discover -s tests -v        76/76 PASS
python3 -m py_compile ...                       PASS
sha256sum -c docs/FROZEN_CORE_V11.sha256        10/10 PASS
```

Release verifier verdict is recorded in the final handoff/release report after
the snapshot and package bytes are frozen.

