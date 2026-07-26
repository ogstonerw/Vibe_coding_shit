# PM-001 — Задачи и traceability

## Выполнено в текущем черновике

- [x] `PM-TASK-001` — собрать requirements и quant handoffs (`PM-REQ-001…093`, `PM-AC-001…058`).
- [x] `PM-TASK-002` — получить architecture handoff и определить source precedence, enums и overlay semantics (`PM-AC-001`, `PM-AC-002`, `PM-AC-003`, `PM-AC-004`, `PM-AC-005`, `PM-AC-006`, `PM-AC-007`, `PM-AC-008`).
- [x] `PM-TASK-003` — написать подробную главу 1 и явно оставить live/Pilot заблокированными (`PM-AC-004`, `PM-AC-006`, `PM-AC-020`).
- [x] `PM-TASK-004` — создать строго неавторизующие draft schema/example, способные вернуть только `DENY` (`PM-AC-001`, `PM-AC-003`, `PM-AC-004`, `PM-AC-021`).
- [ ] `PM-TASK-005` — после owner decisions создать полную ratified mandate schema; draft envelope не переименовывать в активную (`PM-AC-006`, `PM-AC-022`, `PM-AC-023`, `PM-AC-029`).

## Решения владельца

- [x] `PM-TASK-010` — закрыть `PM-DEC-001`: вариант 3, нормативный Development/Research/Replay/DRY_RUN/Paper overlay без real authority (`PM-AC-004`, `PM-AC-021`, `PM-AC-037`).
- [x] `PM-TASK-011` — закрыть `PM-DEC-002`: hash-bound Level A для non-capital без права post-hoc waiver и Level B signature + independent second confirmation (`PM-AC-009`, `PM-AC-010`, `PM-AC-038`, `PM-AC-039`).
- [ ] `PM-TASK-012` — завершить `PM-DEC-003`: модель и вариант 3 `площадка × риск` выбраны; осталось утвердить отдельные численные owner hard bounds/effective values для каждого профиля (`PM-AC-010`, `PM-AC-040…052`).
- [ ] `PM-TASK-013` — закрыть `PM-DEC-004`: NAV perimeter (`PM-AC-013`, `PM-AC-014`).
- [ ] `PM-TASK-014` — закрыть `PM-DEC-005`: aggregate hard caps и reserves; требует отдельного owner-approved policy diff (`PM-AC-006`, `PM-AC-007`).
- [ ] `PM-TASK-015` — закрыть `PM-DEC-006/008`: authority и stage semantics (`PM-AC-009`, `PM-AC-011`).
- [ ] `PM-TASK-016` — закрыть `PM-DEC-009`: benchmark registry и comparative admission (`PM-AC-016`, `PM-AC-033`).
- [ ] `PM-TASK-017` — закрыть `PM-DEC-010`: distribution waterfall и treasury rules (`PM-AC-013`).
- [ ] `PM-TASK-018` — закрыть `PM-DEC-011/012`: accounting, TWR/MWR/XIRR и residual tolerance (`PM-AC-031`, `PM-AC-032`).
- [ ] `PM-TASK-019` — закрыть `PM-DEC-013/014/015`: FX valuation, statistical evidence и capacity hurdle (`PM-AC-026`, `PM-AC-034`, `PM-AC-035`, `PM-AC-036`).

## Будущая реализация contract validator

- [ ] `PM-TASK-020` — реализовать local schema плюс semantic/registry validator (`PM-AC-001`, `PM-AC-029`).
- [ ] `PM-TASK-021` — реализовать policy hash binding и mutation tests (`PM-AC-002`).
- [ ] `PM-TASK-022` — реализовать restrictive overlay/property tests (`PM-AC-003`, `PM-AC-004`, `PM-AC-005`, `PM-AC-006`, `PM-AC-007`, `PM-AC-008`).
- [ ] `PM-TASK-023` — реализовать owner manifest validation и replay protection (`PM-AC-009`, `PM-AC-010`, `PM-AC-018`, `PM-AC-030`).
- [ ] `PM-TASK-024` — реализовать authority/stage transition engine (`PM-AC-009`, `PM-AC-011`, `PM-AC-020`, `PM-AC-021`, `PM-AC-028`).
- [ ] `PM-TASK-025` — реализовать capital-book/topology ledger и transfer denylist (`PM-AC-012`, `PM-AC-013`, `PM-AC-023`).
- [ ] `PM-TASK-026` — реализовать typed aggregate reservation engine (`PM-AC-022`, `PM-AC-027`).
- [ ] `PM-TASK-027` — реализовать exact RUB accounting/TWR/MWR/FX fixtures (`PM-AC-014`, `PM-AC-015`, `PM-AC-031`, `PM-AC-032`, `PM-AC-036`).
- [ ] `PM-TASK-028` — реализовать benchmark/evidence freeze и anti-gaming gates (`PM-AC-016`, `PM-AC-017`, `PM-AC-018`, `PM-AC-033`, `PM-AC-034`, `PM-AC-035`).
- [ ] `PM-TASK-029` — реализовать capacity curve/promotion validation (`PM-AC-019`, `PM-AC-026`).
- [ ] `PM-TASK-030` — реализовать order-policy и venue-capability promotion gates (`PM-AC-024`, `PM-AC-025`).
- [ ] `PM-TASK-031` — связать TB-001 Paper evidence с применимыми portfolio AC без расширения policy (`PM-AC-020`, `PM-AC-021`).
- [ ] `PM-TASK-032` — закрыть `PM-DEC-007` и реализовать Level-B trust root, canonicalization, signature/second-factor verifier и revocation (`PM-AC-030`, `PM-AC-038`).
- [ ] `PM-TASK-033` — после численного профиля `PM-DEC-003` реализовать strict typed temporal/trusted-clock evaluator, раздельные approval/action registries, transition matrices, monotonic reservation/fencing, transactional CAS/outbox `DISPATCH_CLAIMED`, dimension-specific typed PRE/POST protective proof, working-order sunset/cancel/reconciliation с retained contingent reservations, а также post-configuration operating reauthorization (`PM-AC-040`, `PM-AC-041`, `PM-AC-042`, `PM-AC-043`, `PM-AC-044`, `PM-AC-045`, `PM-AC-046`).
- [ ] `PM-TASK-034` — реализовать strict validity-profile schema/registry/generator, exact-key lookup, monotone-safer recalibration, calibration evidence pipeline и Bitget/MOEX isolation (`PM-AC-047`, `PM-AC-048`, `PM-AC-049`, `PM-AC-050`, `PM-AC-051`, `PM-AC-052`).
- [x] `PM-TASK-035` — реализовать fail-closed pure validators и adversarial fixtures для будущей отдельной ACTIVE schema/evidence evaluator, semantic capability/stratum binding, timestamp-duration coupling, owner-envelope/protective-overlay separation, cross-risk registry order и durable earliest-cutoff sunset proof; результат остаётся non-authorizing, runtime trust root не реализован (`PM-AC-053`, `PM-AC-054`, `PM-AC-055`, `PM-AC-056`, `PM-AC-057`, `PM-AC-058`).
## Независимые reviews

- [x] `PM-TASK-040` — institutional portfolio review текущего черновика.
- [x] `PM-TASK-041` — quant methodology review текущего черновика.
- [x] `PM-TASK-042` — market microstructure review текущего черновика.
- [x] `PM-TASK-043` — исправить BLOCKER/HIGH одним writer-ом и повторить затронутые reviews.
- [ ] `PM-TASK-044` — release verification после реализации и evidence; сейчас неприменимо к live.
- [x] `PM-TASK-045` — провести targeted CIO/quant/microstructure review решения `PM-DEC-001` и границы Paper → real (`PM-AC-037`).
- [x] `PM-TASK-046` — устранить findings и завершить targeted CIO/quant/security review решения `PM-DEC-002` (`PM-AC-038`, `PM-AC-039`).
- [x] `PM-TASK-047` — завершить targeted code/quant-risk/security review concept model `PM-DEC-003` (`PM-AC-040`, `PM-AC-041`, `PM-AC-042`, `PM-AC-043`, `PM-AC-044`, `PM-AC-045`, `PM-AC-046`).
- [x] `PM-TASK-048` — получить release-verifier `PASS` для non-authorizing concept freeze v0.5 при отдельном `BLOCKED` для artifact ratification/real capital; deep institutional/quant/microstructure reviews приложены (`PM-AC-040…046`).
- [ ] `PM-TASK-049` — провести code/test/security/risk и deep institutional/quant/microstructure review `PM-DEC-003 v2` и profile-method artifacts (`PM-AC-047`, `PM-AC-048`, `PM-AC-049`, `PM-AC-050`, `PM-AC-051`, `PM-AC-052`).
- [ ] `PM-TASK-050` — получить release-verifier verdict для non-authorizing concept freeze v0.6; real capital обязан остаться `BLOCKED` до численных owner profiles и остальных gates (`PM-AC-047`, `PM-AC-048`, `PM-AC-049`, `PM-AC-050`, `PM-AC-051`, `PM-AC-052`).
- [x] `PM-TASK-051` — провести fresh isolated institutional/quant/microstructure review сырых v0.6 artifacts; зафиксированы BLOCKER/HIGH для исправления (`PM-AC-053…058`).
- [ ] `PM-TASK-052` — повторить fresh deep reviews по финальным evidence после исправлений и закрыть все BLOCKER/HIGH (`PM-AC-053…058`).
