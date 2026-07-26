# PM-001 — Реестр независимого review

Дата: 17.07.2026  
Исходная редакция: 0.1  
Исправленная редакция: 0.5  
Объект фиксации: `TARGET + ACTIVE NON-CAPITAL OVERLAY / REAL CAPITAL BLOCKED`

## Состав проверки

1. `institutional_portfolio_reviewer` — CIO/CRO и совокупный риск.
2. `quant_methodology_reviewer` — accounting, evidence и model risk.
3. `market_microstructure_reviewer` — execution, account topology, venue и capacity.

Review выполнялся read-only. Исправления вносил один root writer. После исправлений затронутые findings были повторно проверены.

## Первичный вердикт

Все три reviewer-а выдали `PASS WITH REQUIRED CHANGES` для продолжения разработки и `BLOCKED` для machine ratification/реального капитала.

Ключевые проблемы исходной редакции:

- draft schema могла описать противоречивую комбинацию локального `ACTIVE` и real-capital полей;
- owner manifest schema могла выглядеть авторизующей без полного verifier contract;
- scalar `min()` смешивал несовместимые единицы риска;
- формулировка полномочий допускала трактовку, что владелец может отменить unknown-state gate;
- PnL identity не определяла точную знаковую конвенцию и ограничение residual;
- TWR/MWR, benchmark, multiple testing, evidence expiry, FX и capacity были недостаточно детерминированы;
- account/margin/credential topology и четыре execution policies не были отдельными machine gates;
- `ACTIVE/PAPER` не имел явного технического запрета real adapter;
- отсутствовала автоматическая проверка уникальности traceability IDs.

## Disposition

| Область | Исправление в 0.2 |
|---|---|
| Draft authority | `mandate.schema.json` и example принудительно задают `BLOCKED`, `DENY`, no-real credential, no endpoint access и zero real authority |
| Owner manifest | Текущая schema явно `NON_AUTHORIZING_DRAFT`, `decision=DENY`, `eligible_for_authorization=false`; ratified schema отложена до owner decisions |
| Risk limits | Введен типизированный вектор `L[metric,scope,horizon,unit,currency,basis]`; heterogeneous constraints применяются через `AND` |
| Runtime safety | Unknown state, reconciliation, stale mandatory data, auth, idempotency и policy/hash mismatch объявлены non-waivable |
| Accounting | Зафиксированы signed identities, automatic residual и обязательный accounting profile/tolerance |
| Return metrics | Добавлены детерминированные TWR/MWR/XIRR methodology requirements и undefined states |
| Evidence | Добавлены benchmark registry, experiment budget, clusters/effective sample, independent expiry/drift и mutation tests |
| FX | Добавлен versioned FX/stablecoin valuation profile; до него consolidated NAV только `INDICATIVE` |
| Capacity | Admission требует conservative hurdle с uncertainty, tested tiers, shared-pool demand и expiry |
| Execution | Добавлены отдельные entry/protective/profit/emergency policies и hash-bound venue capability profile |
| Topology | Добавлены account/margin/credential topology, book uniqueness и contagion gates |
| Traceability | Self-check проверяет уникальность task/requirement/decision/acceptance IDs и полное покрытие |

## Финальный вердикт

| Reviewer | Non-authorizing chapter freeze | Active mandate / real capital |
|---|---|---|
| Institutional CIO/CRO | `PASS` | `BLOCKED` |
| Quant methodology | `PASS` | `BLOCKED` |
| Market microstructure | `PASS` | `BLOCKED` |

Незакрытых `BLOCKER/HIGH` для фиксации версии 0.2 как неавторизующего черновика нет.

## Безопасно отложенные gates

До ratified machine mandate и тем более Pilot остаются обязательными:

- решения владельца `PM-DEC-001…PM-DEC-015`;
- полная ratified mandate/owner-manifest schema;
- semantic validator, persistent registry, signature/revocation verifier и authorization evaluator;
- численные typed aggregate hard caps и reserves;
- physical account/margin/credential topology;
- четыре owner-approved execution policies;
- отдельные crypto/MOEX venue profiles;
- accounting/TWR/MWR/FX/benchmark/statistical/capacity profiles;
- реализация всех применимых `PM-AC-*` и повторный evidence review.

Текущие governance policies не изменялись; live trading остается выключенным.

## Дополнение версии 0.3 — PM-DEC-001

Владелец выбрал вариант 3: глава обязательна для Development, Research, Replay, DRY_RUN и Paper. Решение записано в `decisions/PM-DEC-001.toml` и связано с `PM-REQ-039`/`PM-AC-037`.

После изменения проведен отдельный targeted review:

| Reviewer | Вердикт | Подтвержденная граница |
|---|---|---|
| Institutional CIO/CRO | `PASS` | Overlay не меняет policies и не предоставляет real capital authority |
| Quant methodology | `PASS` | Research/Paper evidence и preregistration обязательны, но не равны Pilot/live |
| Market microstructure | `PASS` | Только simulator/non-real boundaries, `RESEARCH_PAPER`, no credential и zero endpoint access |

Незакрытых `BLOCKER/HIGH` для `ACTIVE_NON_CAPITAL` overlay нет. `PM-DEC-002…PM-DEC-015`, ratified schemas/verifier, Pilot, Production и live остаются `BLOCKED`.

## Дополнение версии 0.4 — PM-DEC-002

Владелец выбрал вариант 3: Level A для некапитальных решений и Level B для любых действий с реальным капиталом. Level B требует криптографическую подпись и независимое второе подтверждение одного canonical payload; до принятия `PM-DEC-007` он неизменно возвращает `DENY`.

Первичный targeted review обнаружил три класса `HIGH`:

- Level-A record не был hash-bound к точным версиям `spec`, `acceptance`, policies и decision payload;
- Level A мог быть неверно истолкован как post-hoc одобрение результатов или waiver research/evidence gates;
- factor-binding допускал одинаково отсутствующие поля, не контролировал полный closed set финансовых действий и persistent sequence freshness.

Исправления редакции 0.4:

- decision record содержит точный duplicate-free набор SHA-256 четырёх утверждённых artifacts и hash полного canonical decision payload;
- изменение любого artifact, payload или обязательного hash делает запись неприменимой;
- post-hoc result ratification, benchmark/threshold mutation, viewed-holdout reuse, drift/expiry waiver и approval-only promotion явно запрещены;
- обязательны непустые и типизированные `manifest_id`, payload/scope/limits digests, положительный sequence и bounded UTC expiry;
- два фактора должны иметь разные trust roots и failure domains;
- missing/malformed/mismatch, replay/non-monotonic sequence, expiry, revocation и сужение closed action set дают `DENY`;
- даже валидная по форме пара не авторизует капитал до отдельного `PM-DEC-007` и реализации trusted verifier/state registry.

| Reviewer | Повторный вердикт | Подтверждённая граница |
|---|---|---|
| Institutional CIO/CRO | `PASS` | Artifact/payload hash binding и mutation detection |
| Quant methodology | `PASS` | Нет post-hoc evidence waiver; missing/malformed/replay fixtures дают `DENY` |
| Security | `PASS` | Closed action set, factor independence, sequence freshness и fail-closed до `PM-DEC-007` |

Незакрытых `BLOCKER/HIGH` для фиксации `PM-DEC-002` как некапитального governance-решения нет. Ratified Level-B schema/verifier, Pilot, Production и любой real-capital action остаются `BLOCKED`.

## Дополнение версии 0.5 — PM-DEC-003

Владелец выбрал вариант 3: Level A является долгосрочным version/hash/scope-bound non-capital record, Level-B operating approval ограничен временем, а отдельные финансовые/конфигурационные действия являются single-use. Численный validity profile не утвержден, поэтому модель имеет статус `PARTIALLY_RESOLVED` и любой Level B остается `DENY`.

Requirements, quant и architecture handoffs потребовали независимых validity clocks для mandate, approval, evidence, venue capability и runtime protection, а также `NO_NEW_RISK` без отключения доказуемо защитных действий по открытой экспозиции.

Первичный test/code/security/risk review обнаружил:

- переписывание historical `PM-DEC-002 v1` новыми hashes;
- смешение approval lifecycle и action lifecycle;
- недостижимое обещание нулевого внешнего эффекта при revocation race;
- отсутствие fencing token и точной dispatch linearization point;
- риск бессрочного расширения после consumed limit/account/scope mutation;
- недостаточно строгий protective/reconciliation exposure predicate;
- недоверенные типы времени и ложное толкование ZIP как trust anchor.

Disposition редакции 0.5:

- `PM-DEC-002 v1` восстановлен byte-for-byte; v0.4/v0.5 ZIP объявлены только non-authoritative consistency snapshots и не являются owner-ratification evidence;
- настоящий trust anchor, signature и WORM/versioned identity остаются `BLOCKED` до `PM-DEC-007`;
- approval и single-use action имеют отдельные closed transition matrices;
- `DISPATCH_CLAIMED` является linearization point, связанной одним durable CAS с revocation/version epoch, sequence, reservation generation, fencing token и outbox claim;
- revocation до claim запрещает adapter call; после claim допускается `IN_FLIGHT/RECONCILIATION_REQUIRED` без ложного обещания zero external effect;
- persistent configuration mutation не дает operating authority: новый hash остается `PENDING_OPERATING_AUTHORIZATION/BLOCKED_NO_NEW_RISK` до отдельного time-boxed manifest;
- reconciliation по умолчанию ограничен reads/cancel/ledger repair; protective trade требует preapproved policy, venue capability, typed PRE/POST proof и `post <= pre` по каждой применимой absolute/net/gross/contingent/margin/stress dimension без sign flip;
- canonical timestamps требуют RFC3339 UTC `Z`; rollback, reboot ambiguity, missing checkpoint и excessive skew дают `DENY`;
- `PM-AC-040…044` явно `PLANNED`: static checks не считаются runtime/persistence/concurrency/adapter evidence.

| Reviewer | Concept freeze | Artifact ratification / real capital |
|---|---|---|
| Test engineering | `PASS` для fail-closed concept после честной маркировки runtime AC как `PLANNED` | `BLOCKED` |
| Code review | `PASS` | `BLOCKED` |
| Quant/risk review | `PASS` | `BLOCKED` |
| Security review | `PASS` | `BLOCKED` до `PM-DEC-007` |

Итог: незакрытых `BLOCKER/HIGH/MEDIUM` для неавторизующей фиксации concept model `PM-DEC-003` нет. Численные TTL/review/skew/revocation/reconciliation значения, runtime implementation, artifact ratification, Pilot, Production и live остаются `BLOCKED`.

### Обязательный deep review PM-DEC-003

Первый release-verifier проход потребовал отдельные заключения трех доменных reviewer-ов. Они были выполнены на одной финальной редакции.

| Deep reviewer | Concept freeze | Real capital | Проверенная область |
|---|---|---|---|
| Institutional portfolio CIO/CRO | `PASS` | `BLOCKED` | Working-order sunset, GTC/conditional late fills, cancel races, contingent reservations, expiry/revocation |
| Quant methodology/model risk | `PASS` | `BLOCKED` | Signed-net absolute-risk order, metric bindings, scenario vectors, independent evidence/holdout validity |
| Market microstructure | `PASS` | `BLOCKED` | Dispatch/outbox/fencing, unknown ACK, venue-specific TIF/reduce-only, MOEX/crypto non-interchangeability |

Дополнительные findings и disposition:

- signed `NET_EXPOSURE` больше не сравнивается обычным знаком: применяется `abs(post) <= abs(pre)`, sign crossing запрещён кроме точного нуля;
- scalar dimensions обязаны быть non-negative risk magnitudes с точными unit/currency/time/horizon/netting-set/convention bindings;
- stress vector использует один scenario-set/hash и componentwise non-increase либо отдельно утвержденную conservative scalar function;
- risk-increasing resting/open/conditional orders имеют venue-enforced expiry не позже approval expiry минус owner-approved cancel/reconciliation buffer;
- до expiry включается `NO_NEW_RISK`, выполняются cancel/reconciliation; unknown/cancel-pending/halt/restart сохраняют contingent exposure и не дают zero-effect claim;
- численный buffer имеет `UNRESOLVED`, поэтому не создаёт скрытого разрешения.

Повторные команды: `python3 scripts/self_check.py` — `PASS`; `python3 -m unittest discover -s tests -v` — `21/21 OK`. Незакрытых `BLOCKER/HIGH/MEDIUM` для concept freeze после deep review нет.

### Release verification v0.5

- Non-authorizing concept freeze: `PASS`.
- Artifact ratification / real capital: `BLOCKED`.
- `PM-AC-040…046`: `PLANNED`, runtime evidence отсутствует.
- `PM-DEC-007`, численный validity profile и cancel/reconciliation buffer: не закрыты.
- Pilot, Production и live: запрещены.

Release verifier подтвердил `self_check PASS`, `21/21 unit tests`, совпадение governance/risk policy hashes и отсутствие незакрытых `BLOCKER/HIGH/MEDIUM` только для фиксации концепции. Этот verdict не снимает ни одного финансового gate.

## Implementation note v0.6 — PM-DEC-003 v2 (до независимого review)

Ответ владельца `3` записан как выбор методологии отдельных validity-профилей по площадке, среде, рынку, стадии капитала, классу approval/action/risk и точным capability/policy hashes. Это не утверждение численных TTL или буферов.

Реализованы только неавторизующие машинные артефакты и проверки формы:

- historical `decisions/PM-DEC-003.toml` сохранён byte-for-byte с SHA-256 `618dd1da08fb6a8f7f0631fa6824bea1cc527d071e035b20b9250bcd374789ce`;
- `PM-DEC-003-v2.toml` является self-contained version 2 и supersedes точный путь/hash v1; mutable `current` alias не создан;
- closed draft schema разделяет `owner_hard_bounds`, неавторизующую `calibration_recommendation` и `owner_selected_effective_values`; числовые owner layers остаются `UNRESOLVED`;
- длительности допускаются только как integer milliseconds без bool/float/string coercion;
- lookup требует ровно один `ACTIVE` exact match; cross-venue/risk/stage fallback, wildcard, zero/multiple match дают `DENY`; MOEX остаётся `FUTURE_BLOCKED`;
- автоматическая адаптация может только сокращать окна, увеличивать защитные буферы либо переводить профиль в restrictive state; relaxation/rebound/incomparable дают `DENY`;
- terminal profile states не реактивируются; `operating_ttl_ms <= cancel_buffer_ms + dispatch_guard_ms` неработоспособен и даёт `DENY`.

Это implementation note, а не reviewer/release verdict. `PM-AC-047…052` остаются `PLANNED`; trusted registry, owner-approved numerical values, telemetry calibration, runtime clock/order evidence, Pilot, Production и live не реализованы и запрещены.

### Implementation correction after test-engineer findings

Четыре `HIGH` из первого test-engineer прохода устранены одним writer-ом, но считаются закрытыми только после независимого повторного review:

- validator теперь сравнивает каждую новую секцию v2 с полным closed expected contract; mutation с пересчитанным payload digest не обходит holdout/censoring/risk-order/lifecycle/lookup/TTL/order-sunset ограничения;
- lookup принимает только schema-valid profile и closed registry context, проверяет exact-key enum/types, decision/policy/capability hashes, UTC validity, lifecycle и non-authorizing eligibility; MOEX безусловно `DENY_MOEX_FUTURE_BLOCKED`;
- DRAFT больше не выдаёт risk-policy за venue capability: используется typed sentinel `UNRESOLVED_NONAUTHORIZING_CAPABILITY` + zero hash + `ABSENT_DENY`, который lookup обязан отвергнуть;
- taxonomy синхронизирована с normative spec: `A0_NON_CAPITAL`, `B1_LIMITED_PILOT`, `B2_EXISTING_PRODUCTION`, `B3_CASH_ACTION`, `B4_AUTHORITY_MUTATION`;
- feasibility проверяет полный integer-ms vector, canonical UTC, строгий `TTL > buffer + guard`, а также `order_expiry_at <= approval_expires_at - buffer`; late-fill/terminal reconciliation uncertainty остаётся `RECONCILIATION_REQUIRED`;
- monotone evaluator требует полный numeric vector, subset authorized actions и историю без rebound; expansion, missing/incomparable и historical relaxation дают `DENY`.

Эта запись остаётся implementation note, а не закрытием finding или release verdict.

### Second implementation correction after code/risk review

Risk/code findings второго прохода реализованы, но их закрытие принадлежит независимым повторным reviewers:

- owner numbers теперь требуют одного exact manifest ref/hash/version/monotonic sequence и canonical owner payload, включающего profile id/version/payload hash и оба owner numeric layers; calibration явно не является authority;
- closed tuple/action matrix отделяет operating, one-time cash/config и non-capital profiles; missing/extra/inapplicable numeric field и смешение venue/environment/market/stage/tier/validity/action/risk дают `DENY`;
- `reconciliation_timeout_ms` удалён и заменён на `reconciliation_escalation_deadline_ms`: deadline только эскалирует, не доказывает no-fill, не освобождает exposure/reservation и не снимает protective states;
- schema const/enum comparison теперь type-strict, поэтому Python `0/1` не подменяют JSON boolean;
- все durations имеют технический representation maximum до datetime arithmetic; bound не является owner TTL, overflow/oversize дают `DENY`;
- future ACTIVE shape требует exact schema ID/version/hash, canonical profile payload, supersedes ref/hash/sequence и evidence manifest/hash/issuer/as-of/freshness; signed persistent registry всё ещё `PENDING_RUNTIME_IMPLEMENTATION`, helper остаётся `NON_AUTHORIZING`;
- non-authoritative v0.6 snapshot проверяется по закрытому member manifest, запрещает duplicate/path traversal и byte drift относительно working release tree.

DRAFT сохраняет только `ABSENT_DENY/UNRESOLVED` owner/evidence/capability sentinels; численной или криптографической owner authority в нём нет.
