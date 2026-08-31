# PM-DEC-007 — гибридный Level-B trust-контур

Версия addendum: `1`  
Статус: `PARTIALLY_RESOLVED_ARCHITECTURE_ONLY`  
Authorization effect: `NONE`  
Pilot / Production / live trading / real capital: `BLOCKED / DENY`

## 1. Outcome

Владелец выбрал гибридную архитектуру Level-B trust-контура:

1. одни exact opaque bytes owner manifest подписываются физическим аппаратным ключом;
2. тот же exact payload независимо подтверждается на отдельном устройстве;
3. commit-time readiness требует независимо доверенного актуального checkpoint из append-only registry.

Решение фиксирует только топологию. Оно не ратифицирует алгоритм подписи, canonicalization Level-B manifest, конкретные ключи, устройства, поставщиков, enrollment/attestation/recovery protocol, trusted clock, численные интервалы либо runtime verifier. Любой результат этого addendum остаётся non-authorizing.

## 2. In scope

- immutable owner decision record `PM-DEC-007 v1`;
- закрытая модель первичного физического ключа и подтверждения на отдельном устройстве;
- обязательная независимость trust root, failure domain, key material, device, session/process, administrative domain и recovery path;
- exact-byte и exact-hash binding обоих факторов к одному manifest;
- обязательный independently trusted current checkpoint;
- fail-closed граница между shape validation и runtime authority;
- adversarial fixtures, которые доказывают отсутствие `ALLOW`.

## 3. Out of scope

- выбор криптографического алгоритма и параметров;
- выбор canonicalization Level-B manifest;
- конкретный аппаратный ключ, устройство, поставщик или облачная учётная запись;
- enrollment, attestation, rotation, compromise и recovery ceremony;
- exact owner identity / public-key / attestation bindings;
- exact-byte ACTIVE manifest schema и production verifier;
- persistent registry, trusted clock, revocation service, CAS/outbox и durable consumption;
- численные TTL, activation window, clock skew, freshness, buffers и guards;
- Pilot, Production, реальные credentials, real-capital authority и MOEX.

## 4. Sources and precedence

Addendum подчиняется:

1. `governance/approval-policy.toml`;
2. `governance/risk-policy.toml`;
3. frozen parent contract `docs/FROZEN_CORE_V11.sha256`;
4. `specs/portfolio-mandate-v1/decisions/PM-DEC-002.toml`;
5. неизменённым `PM-DEC-003 v1/v2`.

Parent frozen manifest SHA-256:
`46f20183230d84f6fdaba9ccc63e8e504afcd2be77c4447c66a14f5a9be5390f`.

Этот addendum не изменяет 10 frozen v11 paths, `portfolio-mandate-v0.6.zip`, governance policies или `PM-DEC-003`.

## 5. Owner decision

### 5.1. Primary factor

Первый фактор имеет роль `PRIMARY_CRYPTOGRAPHIC_SIGNATURE` и класс
`PHYSICAL_HARDWARE_SIGNING_KEY`. Конкретные key/root/provider/algorithm refs пока
`UNRESOLVED`. Строка о физическом ключе не является доказательством его
аппаратности, неизвлекаемости или регистрации.

### 5.2. Independent confirmation

Второй фактор имеет роль `INDEPENDENT_SECOND_CONFIRMATION` и класс
`SEPARATE_DEVICE_CONFIRMATION`. Он проверяет тот же exact payload самостоятельно,
а не подтверждает абстрактную кнопку или текстовое описание действия.

### 5.3. Independence

Разными должны быть все bindings:

- `TRUST_ROOT_ID`;
- `FAILURE_DOMAIN_ID`;
- `KEY_MATERIAL_ID`;
- `DEVICE_ID`;
- `SESSION_ID`;
- `ADMIN_DOMAIN_ID`;
- `RECOVERY_PATH_ID`.

Один и тот же владелец может управлять обоими факторами, но общий ключ, root,
device, session/process, административный домен, cloud account или recovery
controller означает `DENY`. Caller-supplied labels и booleans не доказывают
независимость.

### 5.4. Factor loss, compromise and replacement

Потеря или компрометация любого фактора блокирует новые Level-B полномочия и
требует suspension/revocation соответствующего trust set. Оставшийся фактор не
может единолично восстановить второй. Replacement требует новых root/factor IDs,
нового owner trust epoch, большего monotonic sequence и terminal revocation
старых roots. Старый manifest не реактивируется.

Точная recovery ceremony остаётся нерешённым owner input.

## 6. Behavioral scenarios

1. **Record shape valid.** Exact decision record даёт только
   `NON_AUTHORIZING_PM_DEC_007_ARCHITECTURE_SHAPE_VALID`.
2. **Shared recovery path.** Совпадение хотя бы одного independence binding даёт
   `DENY_PM_DEC_007_FACTORS_NOT_INDEPENDENT`.
3. **Payload mismatch.** Отличие exact bytes/hash, manifest identity/version,
   sequence, action, scope, limits, artifacts/configuration или time interval
   даёт `DENY_PM_DEC_007_PAYLOAD_BINDING_MISMATCH`.
4. **Caller validity flag.** `signature_valid=true`, `device_valid=true`,
   `checkpoint_current=true` и аналогичные self-declared booleans не являются
   evidence и дают `DENY_PM_DEC_007_CALLER_AUTHORITY_CLAIM`.
5. **Checkpoint claim.** Любой caller-supplied checkpoint — включая формально
   полный, старый, forked, replayed или self-declared current — получает
   `DENY_PM_DEC_007_TRUSTED_CHECKPOINT_UNAVAILABLE`. Stateless helper не
   классифицирует его как действительно свежий или replayed.
6. **Authority readiness.** Для любых текущих inputs результат равен
   `DENY_PM_DEC_007_RUNTIME_TRUST_INCOMPLETE`.
7. **Factor unavailable.** Новый или увеличивающий риск запрещён. Этот addendum
   не создаёт protective exception; применимы только уже существующие parent
   reconciliation/protection contracts.

## 7. Risk and execution rules

- `live_trading_enabled = false`;
- `eligible_for_real_capital_authorization = false`;
- `artifact_ratification_eligible = false`;
- `authorization_effect = NONE`;
- форма двух факторов не является stage approval;
- физическое разделение устройств не заменяет независимость roots и recovery;
- подпись не доказывает актуальность checkpoint;
- offline snapshot, ZIP, pure validator и caller registry не являются trust root;
- fixture values не являются owner-approved TTL/freshness/skew;
- ни один helper этого addendum не вызывает adapter, сеть или биржу.

## 8. Machine-readable contract

### 8.1. Decision record

`decisions/PM-DEC-007.toml` имеет закрытый exact contract и содержит:

- identity/version/status/evidence;
- выбранную модель;
- primary/confirmation topology;
- independence и same-payload bindings;
- factor lifecycle и checkpoint boundary;
- полный список unresolved dependencies;
- immutable parent/governance artifact hashes;
- canonical digest самого non-authorizing decision record.

Canonicalization записи decision record используется только для integrity этого
файла. Она не ратифицирует canonicalization будущего Level-B manifest.

### 8.2. Factor evidence shape

Factor object — закрытый словарь без дополнительных полей и coercion. `bool` не
является `integer`. ASCII token имеет grammar
`^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$`. Digest — lowercase
`^[0-9a-f]{64}$`. Timestamp — strict UTC
`YYYY-MM-DDTHH:MM:SS[.ffffff]Z`.

| Field | Type / constraint | Relation |
|---|---|---|
| `factor_record_version` | integer const `1` | equal |
| `role` | exact role enum | primary/confirmation differ as defined below |
| `factor_class` | exact class enum | primary/confirmation differ as defined below |
| `factor_id` | ASCII token | distinct |
| `trust_set_id` | ASCII token | equal |
| `owner_identity_ref` | ASCII token | equal |
| `owner_trust_epoch` | positive integer | equal |
| `global_sequence_namespace_id` | ASCII token | equal |
| `trust_root_id` | ASCII token | distinct |
| `failure_domain_id` | ASCII token | distinct |
| `key_material_id` | ASCII token | distinct |
| `device_id` | ASCII token | distinct |
| `session_id` | ASCII token | distinct |
| `admin_domain_id` | ASCII token | distinct |
| `recovery_path_id` | ASCII token | distinct |
| `manifest_id` | ASCII token | equal |
| `manifest_version` | positive integer | equal |
| `monotonic_sequence` | positive integer | equal; shape does not prove freshness |
| `action_class` | ASCII token | equal |
| `payload_sha256` | lowercase SHA-256 | equal and recomputed from both opaque byte inputs |
| `scope_sha256` | lowercase SHA-256 | equal |
| `limits_sha256` | lowercase SHA-256 | equal |
| `artifact_set_sha256` | lowercase SHA-256 | equal |
| `configuration_sha256` | lowercase SHA-256 | equal |
| `effective_from` | strict UTC | equal |
| `review_due_at` | strict UTC | equal |
| `expires_at` | strict UTC | equal |
| `factor_evidence_ref` | ASCII token | factor-specific |

Primary exact values:
`role=PRIMARY_CRYPTOGRAPHIC_SIGNATURE`,
`factor_class=PHYSICAL_HARDWARE_SIGNING_KEY`.
Confirmation exact values:
`role=INDEPENDENT_SECOND_CONFIRMATION`,
`factor_class=SEPARATE_DEVICE_CONFIRMATION`.

Validator принимает отдельно `primary_payload_bytes` и
`confirmation_payload_bytes`. Оба значения должны иметь точный тип `bytes`,
совпадать byte-for-byte, а их локально пересчитанный SHA-256 должен совпадать с
`payload_sha256` обоих factor objects. Bytes не парсятся и не объявляются
canonical: Level-B canonicalization остаётся нерешённой.

Обязателен `effective_from < review_due_at < expires_at`, но длина интервала не
считается утверждённым TTL/freshness profile. Любые поля или строки, заявляющие
`valid`, `trusted`, `current`, `approved`, `ACTIVE`, `VERIFIED`,
`EVIDENCE_READY`, Pilot либо Production truth, являются неизвестными полями и
дают `DENY`. Stateless shape helper отклоняет nonpositive или mismatched
sequence, но не утверждает, что положительный sequence свежий и не replayed.

### 8.3. Checkpoint and commit-time boundary

Checkpoint authority в будущем должна происходить из pinned implementation
profile и independently trusted append-only service. До этого любой checkpoint
claim получает `DENY_PM_DEC_007_TRUSTED_CHECKPOINT_UNAVAILABLE`; текущего
checkpoint shape-success результата нет.

Будущий trusted checkpoint обязан связывать:

- `registry_id`, registry scope, pinned genesis и contiguous head;
- global sequence namespace, head sequence и supersedes/digest chain;
- `owner_trust_epoch`, exact trust set и оба factor/root IDs;
- lifecycle/revocation epoch каждого root и terminal old-root state;
- checkpoint trust-root, failure-domain, admin-domain, recovery-path и
  runtime-host bindings, отличные от соответствующих bindings обоих факторов;
- trusted UTC/monotonic/persistent-last-seen clock evidence.

В будущем current checkpoint/revocation epoch повторно проверяются внутри той же
durable transaction/CAS, которая связывает exact operating manifest,
`intent_id`, reservation generation, fencing token и transactional outbox
переход `DISPATCH_CLAIMED`. Изменение, revocation или недоступность до claim
означают zero adapter call. Неопределённость после claim означает
`RECONCILIATION_REQUIRED` без blind retry. Trust loss запрещает новый риск,
инициирует cancel opening/conditional orders и сохраняет contingent
reservations до terminal venue reconciliation. Этот addendum не симулирует и
не помечает выполненным данный runtime contract.

## 9. Requirements

`PM-REQ-094`: Level-B использует выбранную hybrid topology: primary factor —
physical hardware signing key, confirmation — отдельное устройство. Все семь
independence bindings различны и в будущем выводятся из pinned registry/profile,
а не из caller labels. Потеря/compromise блокирует новые полномочия; one-factor
или shared-backend recovery запрещён.

`PM-REQ-095`: оба фактора независимо подтверждают одни opaque exact payload
bytes/hash и полный закрытый typed набор factor/trust-set/owner-epoch/global-
sequence/identity/version/action/scope/limits/artifact/configuration/time
bindings из §8.2. Missing, extra, malformed, mismatch, nonpositive sequence,
неправильный factor class или caller truth/validity claim дают `DENY`.
Stateless shape helper не доказывает canonicality, freshness, отсутствие replay
или действительность подписи/attestation.

`PM-REQ-096`: Level-B readiness дополнительно требует independently trusted
current append-only checkpoint и commit-time contract из §8.3. Caller shape,
self-declared head, cached genesis, stale, truncated, replayed или forked
history никогда не доказывают currentness и сейчас одинаково получают
`DENY_PM_DEC_007_TRUSTED_CHECKPOINT_UNAVAILABLE`. Пока exact crypto/
canonicalization/carriers/enrollment/recovery/clock/numeric/runtime profiles
отсутствуют, readiness всегда
`DENY_PM_DEC_007_RUNTIME_TRUST_INCOMPLETE`, adapter не вызывается, а
Pilot/Production/live остаются `BLOCKED`.

## 10. Evidence boundary

Pure validators могут доказать только:

- exact decision-record structure и integrity binding;
- отсутствие очевидного shared dimension в предъявленной factor shape;
- equality exact payload bindings;
- закрытую factor-object shape и equality opaque payload bytes/hash.

Они не доказывают:

- действительность подписи или attestation;
- регистрацию/pinning root;
- реальную независимость устройств и recovery;
- актуальность checkpoint, replay/fork classification, полноту истории,
  durable persistence или atomicity;
- корректное намерение владельца;
- готовность стратегии, биржи, risk/evidence/runtime контуров;
- право на Pilot, Production или реальный капитал.

## 11. Acceptance criteria

Нормативные критерии: `acceptance.toml`, `PM-AC-059…061`.

## 12. Open decisions

- exact cryptographic algorithm profile;
- exact Level-B manifest canonicalization profile;
- concrete key/device/provider profiles и pinned trust roots;
- enrollment/attestation protocol;
- rotation/revocation/compromise/recovery ceremony;
- trusted clock и checkpoint verifier;
- owner numeric TTL/freshness/skew/buffer/guard values;
- durable runtime registry, CAS/outbox и single-use consumption;
- parent mandate integration release.
