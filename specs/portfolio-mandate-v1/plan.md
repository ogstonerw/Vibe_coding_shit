# PM-001 — План ратификации инвестиционного мандата

Статус: ACTIVE NON-CAPITAL OVERLAY для Development/Research/Replay/DRY_RUN/Paper. Реальный капитал остается BLOCKED.

## Этап 1. Зафиксировать нормативную семантику

- Утвердить лексикографический порядок целей.
- Отделить target mandate от active Phase-1 overlay.
- Утвердить закрытые enums, deny-by-default и порядок разрешения конфликтов.
- Сверить требования `PM-REQ-*` с governance policy.

Evidence: `spec.md`, requirements/quant/architecture handoffs, deep expert review.

## Этап 2. Закрыть фундаментальные решения владельца

- `PM-DEC-001` принят: вариант 3, активный некапитальный overlay.
- `PM-DEC-002` принят: двухуровневая owner approval model.
- `PM-DEC-003 v2` concept model принят: отдельные evidence-calibrated profiles `площадка × риск` внутри owner hard bounds; Bitget и MOEX не объединяются, автоматическое изменение может быть только более строгим.
- Последовательно закрыть численные owner hard bounds/effective values каждого профиля `PM-DEC-003` и решения `PM-DEC-004…PM-DEC-015`; до этого real capital остается `DENY`.
- Для каждого решения зафиксировать область, fail-closed default, дату действия и влияние на старые evidence.
- Не объединять решения, если одно из них требует численных hard caps или расширения real scope.

Evidence: owner decision records; позднее — подписанный manifest.

## Этап 3. Завершить machine-readable contract

- Сохранить `mandate.schema.json` и `mandate.example.toml` как неавторизующий draft envelope, который может выдать только `DENY`.
- Утвердить отдельную полную ratified mandate schema только после owner decisions.
- Утвердить `owner-decision-manifest.schema.json`, canonicalization, trust root, signature verification, bounded TTL, nonce/sequence и revocation.
- Реализовать local schema validator, semantic validator, persistent version registry и policy-hash binding.
- Реализовать restrictive overlay; только отдельный authorization evaluator может выпустить short-lived `ALLOW`.
- Реализовать отдельные immutable validity profiles, exact-key registry/lookup, deterministic generator/replay и раздельные owner/calibration/effective слои без mutable authority alias.
- Отделить подписанный owner envelope от versioned protective overlay; profile authority change обрабатывать как Level-B B4 single-use action.
- Для будущего ACTIVE создать отдельные exact-hash schema/evidence/capability artifacts; DRAFT schema не мутировать в памяти и не использовать как authority.

## Этап 4. Добавить детерминированные проверки

- Schema/unknown-field/status tests.
- Policy mutation/hash mismatch tests.
- Scope intersection и minimum-cap property tests.
- Stage/authority/manifest expiry/revocation tests.
- Temporal-boundary, single-use atomic reservation/consumption, commit-time revocation race и supersession rollback tests.
- Capital-book conservation и запрещенные transfers.
- RUB PnL/NAV, TWR/MWR, FX/stablecoin attribution fixtures.
- Anti-gaming, benchmark-freeze и capacity tests.
- Cross-product Paper/live capability isolation и network-spy tests.
- Typed limit dimensionality и atomic parent reservation tests.
- Account/margin/credential topology и contagion tests.
- Protective/emergency order-policy и venue-capability gates.
- Independent evidence expiry/drift и exact PnL/TWR/MWR/FX fixtures.
- Cross-venue/risk/stage fallback denial, strict integer-duration, monotone-safer recalibration, censored tail-calibration и TTL/buffer feasibility fixtures.
- Duration-to-timestamp coupling, semantic capability/runtime-stratum binding, canonical exact-scope cross-risk ordering from complete owner-epoch history, shared exact-order earliest-validity-cutoff sunset/feasibility и durable fill-watermark/reconciliation fixtures.
- Strict canonical JSON rejects duplicate keys, malformed/non-finite values and non-canonical bytes; release source lstat/containment rejects symlink and nonregular members, while ZIP validation independently rejects traversal, duplicate, symlink and special-file members.
- Любая попытка выдать мутированную DRAFT schema за ACTIVE завершается `DENY_ACTIVE_SCHEMA_OR_RUNTIME_EVIDENCE_UNAVAILABLE`; shape-valid pure helper никогда не считается trust root.
- Bitget policy helper reads exact immutable `governance/risk-policy.toml` bytes, requires pinned `bitget-btc-v1` v1 SHA plus BTCUSDT-only/limit-only/live-disabled semantics, and rejects caller-selected alternate hashes. Closed venue mechanics reject unknown/mixed/CASH/unsupported tuples; MOEX remains blocked.
- B4 registry helper проверяет только caller-supplied global shape и возвращает исключительно `NON_AUTHORIZING_B4_REGISTRY_SHAPE_VALID`; protocol genesis, epochs, sequence/CAS и indexes не доказывают current checkpoint, persistence, atomicity или durable consumption. До PM-DEC-007 readiness всегда получает explicit trust-unavailable `DENY`, включая canonical/stale genesis. Operating-manifest helper аналогично проверяет только exact-byte PurePosix/supersedes/identity-digest shape без claim о registry trust/currentness/completeness.
- Evidence fixtures требуют explicit owner-bound sample/window threshold artifact без numeric defaults, causal sealed-window/holdout timestamps и actual counts не ниже owner minima.
- Absolute-time fixtures проверяют positive operating interval, effective <= evaluation <= commit < review_due < expiry, freshness at commit и non-future causal unknown/dispatch/ACK; review equality/post-cutoff deny. Feasibility и strict sunset используют один exact order identity/expiry helper и earliest approval/evidence/capability/policy/protection cutoff; legacy cancel+zero-open не reconciles без strict proof. Cross-risk comparison разрешён только для resolved nonzero exact-scope operating B1-to-B2 profiles, чья simultaneous ACTIVE shape выведена из complete contiguous owner-epoch history; unresolved/pending/not-implemented/deny sentinels, zero capability/calibration hashes и DRAFT scope с caller ACTIVE history запрещены, runtime ACTIVE остаётся unavailable.
- B4 canonical payload связывает previous configuration, выведенный из exact prior operating-manifest bytes/record, требует new configuration hash rotation и запрещает replacement manifest с reused configuration.
- Evidence helper закрывает regime/degraded/access-purpose enums и owner-bound exact provenance refs, но валидирует только declared canonical shape/causality; estimator correctness, statistical truth, owner authority и ACTIVE требуют будущего evaluator.
- Overlay registry fixture требует непустой immutable overlay ID и complete immutable owner-epoch history; late ACK не восстанавливает authority.

## Этап 5. Независимый контроль

- Requirements traceability review.
- Institutional CIO/CRO review.
- Quant methodology/model-risk review.
- Market microstructure review.
- После реализации: code, security, risk reviews и повторный deep evidence review.
- Release verifier запускается последним и не может снять проваленный gate.

## Этап 6. Связать с TB-001

- Добавить в TB-001 только те portfolio acceptance criteria, которые нужны для достоверного Paper evidence.
- Не расширять текущие venue/symbol/stage/risk permissions.
- Зафиксировать, что Paper evidence не означает Pilot authorization.

## Verification

Текущие обязательные команды:

```bash
python3 scripts/self_check.py
python3 -m unittest discover -s tests -v
```

После реализации validator должны быть добавлены formatter/linter/type/unit/property/integration commands и точные evidence paths. До этого этапа они имеют статус `PLANNED`, а не `PASS`.

## Rollback

Документ не мутируется задним числом. Ошибочная версия получает `RETIRED` или `SUPERSEDED_BY`, новая версия создается отдельным diff. Governance policies не откатываются или заменяются этим work item.
