# PM-001 — Инвестиционный мандат и цели портфеля торговых ботов

Версия документа: 0.6  
Статус документа: `TARGET + ACTIVE NON-CAPITAL OVERLAY / REAL CAPITAL BLOCKED`  
Статус реального капитала: `BLOCKED`  
Владелец: пользователь  
Базовая валюта: `RUB`  
Дата редакции: 17.07.2026

## 1. Назначение

Этот документ является первой подробной главой полного ТЗ системы торговых ботов. Он определяет, для чего существует портфель, какие цели имеют приоритет, что входит в управляемый капитал, какие рынки и горизонты относятся к целевому состоянию, кто имеет право расширять полномочия и по каким правилам оценивается результат.

Мандат не является обещанием доходности, торговой стратегией, разрешением на реальную торговлю или заменой численной risk policy. Он задает проверяемую рамку, внутри которой будут проектироваться платформа и отдельные боты.

Решения `PM-DEC-001` и `PM-DEC-002` приняты владельцем: настоящий документ обязателен для некапитального lifecycle, а подтверждения разделены на два уровня. Для `PM-DEC-003` владелец выбрал дифференцированную модель срока действия и вариант 3 для её детализации: отдельные профили `площадка × риск`, калибруемые по evidence внутри численных hard bounds владельца. Сами численные bounds и effective values ещё не утверждены. До их закрытия и решений `PM-DEC-004…PM-DEC-015` документ остается `BLOCKED` для Pilot, Production и любого реального капитала. Все некапитальные стадии выполняются только в пределах действующих более узких policies.

## 2. Источники истины и разрешение конфликтов

Применяется следующий порядок приоритета:

1. `governance/approval-policy.toml` — `tradebot-factory-approvals-v1`, version `1`.
2. `governance/risk-policy.toml` — `bitget-btc-v1`, version `1`.
3. Настоящие `spec.md` и `acceptance.toml`.
4. Принятые архитектурные документы в `docs/`.
5. ТЗ конкретного бота и существующая реализация.
6. Явно маркированные предположения.

Зафиксированные на дату редакции SHA-256:

| Файл | SHA-256 |
|---|---|
| `governance/approval-policy.toml` | `9be5ef3804dd8a35681526e9b154d50c0162ba610101dcbabd00ce29996a8708` |
| `governance/risk-policy.toml` | `4f34d45ac058bec6d5ce1ecc05dc242572a917bd6e2f6769ff53b7115f4b72e8` |

Эти hashes идентифицируют рассмотренную baseline, но не заменяют вычисление hash в момент проверки. Изменение policy делает старое решение неприменимым до повторного review.

Правила конфликта:

- allowlist вычисляется как пересечение разрешенных множеств;
- максимальные лимиты вычисляются как минимум применимых потолков;
- минимальные защитные требования вычисляются как максимум применимых требований;
- разрешающие boolean объединяются логическим `AND`;
- стадия выбирается наиболее ограничительная;
- отсутствующее, неизвестное, противоречивое, просроченное или отозванное разрешение дает `DENY`;
- пустое пересечение scope дает `DENY`;
- целевая формулировка никогда не расширяет active policy.

## 3. Термины и закрытые перечисления

### 3.1. Статус объекта

Допустимы только:

- `ACTIVE` — объект используется в указанном нефинансовом lifecycle boundary; этот статус сам по себе не разрешает реальный ордер;
- `TARGET` — целевое состояние, не создающее торговых полномочий;
- `FUTURE` — будущий scope, для которого отсутствует действующая policy;
- `SHADOW_ONLY` — рассчитывается и журналируется, но не изменяет реальные полномочия или капитал;
- `BLOCKED` — запрещено до выполнения указанного gate;
- `RETIRED` — выведено из эксплуатации; статус терминален.

### 3.2. Стадия

- `DEVELOPMENT`;
- `RESEARCH`;
- `REPLAY`;
- `DRY_RUN`;
- `PAPER`;
- `PILOT_LIMITED_LIVE`;
- `PRODUCTION_LIVE`.

### 3.3. Книги капитала

- `RESEARCH_PAPER`;
- `PILOT`;
- `PRODUCTION`;
- `OPERATIONAL_MARGIN_RESERVE`;
- `PROTECTED_RESERVE`;
- `DISTRIBUTION_PAYABLE`.

Неизвестное значение, синоним или дополнительное поле не нормализуется «по смыслу», а отклоняется.

Lifecycle status, execution boundary и financial authority являются разными измерениями. Реальное разрешение не читается непосредственно из mandate/template. Только отдельный deterministic authorization evaluator после проверки всех policy, manifest, runtime state и evidence может выпустить короткоживущий результат `ALLOW`; любой исходный artifact, текущий пример и любая неполная комбинация дают `DENY`.

## 4. Инвестиционная цель и порядок приоритетов

Владелец выбрал смешанную модель: долгосрочный геометрический рост капитала после полных издержек сочетается с формированием периодического денежного потока. Это не две равноправные цели: они подчинены лексикографической иерархии.

### 4.1. Лексикографическая иерархия

1. **Политика, полномочия и целостность состояния.** Система действует только в разрешенном scope. Неизвестное состояние, несовпадение policy/manifest, незавершенная reconciliation или отозванное разрешение запрещают новый риск.
2. **Выживание и защита капитала.** Hard limits, риск критической потери, stressed loss, margin, концентрации и изоляция защищенного капитала имеют приоритет над результатом.
3. **Ликвидность и обязательства.** Сохраняются операционный, маржинальный, налоговый и аварийный резервы, а также способность контролируемо сократить риск в стрессе.
4. **Геометрический рост в RUB после издержек.** Оптимизируется портфельный, а не изолированный bot PnL, с учетом исполнения, финансирования, FX и stablecoin basis.
5. **Распределяемый денежный поток.** Распределяется только settled/realized/reconciled cash после выполнения резервов и high-water-mark rules.
6. **Качество evidence и эксплуатации.** Невоспроизводимый или несверяемый результат не признается даже при привлекательном PnL.

`PM-REQ-001`: нижестоящая цель не может компенсировать нарушение вышестоящей балльной оценкой, средней метрикой или решением агента.

`PM-REQ-002`: мандат не содержит гарантированной, ожидаемой или минимально обещанной доходности. Численный performance hurdle может появиться только как отдельное owner-approved решение с методологией и uncertainty.

## 5. Target mandate и действующий Phase-1 overlay

Target mandate и active overlay хранятся раздельно. Эффективное разрешение вычисляется как:

> target mandate ∩ active governance policies ∩ verified owner decision manifest ∩ current protection/runtime state.

### 5.1. Решение PM-DEC-001: активный некапитальный overlay

Владелец выбрал вариант 3. Требования этой главы обязательны для:

- проектирования и разработки;
- Research и experiment governance;
- Replay;
- DRY_RUN;
- Paper trading и формирования Paper evidence.

Нормативность означает, что ТЗ ботов, планы, acceptance contracts, тесты, отчеты и решения агентов в этих стадиях должны соответствовать этой главе либо явно фиксировать конфликт. Она не означает доступ к капиталу.

Для всех перечисленных стадий неизменно:

- `authorization_result = DENY` для реальных ордеров;
- `real_capital_authority = false`;
- `trading_endpoint_access = false`;
- execution boundary ограничен research/replay/DRY_RUN adapter/Paper simulator;
- используется только `RESEARCH_PAPER` book;
- trade-capable credential отсутствует;
- любая попытка перейти в Pilot/Production или вызвать реальный trading endpoint является нарушением mandate.

Решение записано в `decisions/PM-DEC-001.toml`. Это record некапитального governance-решения, а не owner decision manifest для реального капитала; оно не изменяет `governance/risk-policy.toml` и `governance/approval-policy.toml`.

`PM-REQ-039`: Development/Research/Replay/DRY_RUN/Paper должны применять требования и acceptance этой главы, но cross-product authorization guard обязан сохранять `DENY_REAL_ORDERS` независимо от локального lifecycle status.

### 5.2. Решение PM-DEC-002: двухуровневое подтверждение владельца

Владелец выбрал вариант 3.

**Уровень A — некапитальные решения.** Для концепции, ТЗ, Research, Replay, DRY_RUN и Paper достаточно решения владельца в текущем рабочем интерфейсе с обязательной записью отдельного versioned decision record. Запись содержит decision ID/version, выбранный вариант, owner reference, timestamp, точный scope, SHA-256 утверждённых `spec`, `acceptance` и применимых governance policies, hash канонического payload самой записи и явный `DENY_REAL_ORDERS`. Изменение любого связанного байта делает запись неприменимой: решение не переписывают задним числом, а выпускают новую версию.

Level A подтверждает только заранее определённые правила или некапитальный scope. Он не является доказательством качества стратегии и не может задним числом утверждать результаты, менять threshold/benchmark после просмотра данных, объявлять уже просмотренное окно новым holdout, отменять preregistration, evidence expiry/drift gate либо самостоятельно повышать lifecycle stage.

**Уровень B — решения о реальных деньгах.** Подключение реального счета/credential, Pilot, Production, новый real venue/instrument, повышение hard cap, изменение leverage/margin, перевод между реальными books и distribution требуют одновременно:

1. криптографической подписи одного canonical owner decision manifest;
2. отдельного второго подтверждения того же payload и hash через независимый подтверждающий механизм.

Оба подтверждения привязаны к одному `manifest_id`, payload hash, monotonic sequence, scope, limits и сроку действия. Второй механизм обязан иметь отдельный trust root и отдельную failure domain: два клика, сообщения или токена одной сессии/ключа/процесса не являются двумя независимыми факторами. Подтверждение другого текста, старой версии либо только одного фактора дает `DENY`. Некапитальный decision record нельзя повысить до real-capital manifest копированием, переименованием или добавлением поля.

Точный trust root, алгоритм подписи, носитель ключа, canonicalization и независимый второй канал будут определены в `PM-DEC-007`. До его принятия и реализации verifier любой Level-B manifest имеет `eligible_for_authorization=false`.

`PM-REQ-040`: Level-A approval применяется только к Development/Research/Replay/DRY_RUN/Paper и никогда не является evidence личности для real-capital action.

`PM-REQ-041`: Level-B action требует успешной проверки криптографической подписи и второго независимого подтверждения одного canonical payload; отсутствие, несовпадение, replay, expiry или revocation любого компонента дают `DENY`.

`PM-REQ-042`: Level-A approval не может ратифицировать результаты post hoc, изменять preregistered protocol/threshold/benchmark после просмотра evaluation data, переиспользовать просмотренный holdout, отменять evidence expiry/drift/quality gate либо самостоятельно разрешать stage promotion.

### 5.3. Решение PM-DEC-003: дифференцированная действительность

Владелец выбрал вариант 3: срок и способ погашения approval зависят от финансового воздействия.

- **Level A** — долгосрочная, но строго version/hash/scope-bound запись для Development, Research, Replay, DRY_RUN и Paper. Изменение связанного artifact или scope требует новой версии; календарное review не превращает старые результаты в новые и не обновляет evidence.
- **Level B operating** — только ограниченный по времени manifest для точного Pilot/Production operating scope.
- **Level B single-use** — одноразовое разрешение для подключения/изменения real account или credential, расширения real scope, изменения hard limits/leverage/margin, перевода между real books либо distribution.

Отдельные алгоритмические order intents внутри уже действующего Level-B operating scope не требуют новой подписи владельца на каждую заявку, но каждый intent повторно проходит mandate, risk, evidence, execution, protection, idempotency и commit-time authorization gates.

Численные интервалы Level-A review, Level-B TTL, single-use activation window, clock skew и revocation freshness не следуют из выбора варианта 3. Они остаются owner inputs в `PM-DEC-003`; до их утверждения каждый Level-B approval имеет `eligible_for_authorization=false`. Значение `86400` в unit-test fixture не является утвержденным TTL.

Архивы `portfolio-mandate-v0.4.zip` и `portfolio-mandate-v0.5.zip` являются только неавторитетными consistency snapshots. Они помогают обнаружить случайный rebinding или неполную упаковку версии, но не являются trust root, не удостоверяют личность владельца и не доказывают owner ratification. До закрытия `PM-DEC-007` snapshot не может сделать artifact ratification eligible; real-capital authority и artifact ratification остаются `DENY/BLOCKED`.

`PM-AC-040…043` описывают будущие runtime acceptance gates и имеют статус `PLANNED`. Текущие self-check/unit fixtures проверяют непротиворечивость и fail-closed форму концептуального контракта, но не являются доказательством transaction/CAS registry, commit-time revocation barrier, реального adapter isolation или безопасного reduce-only исполнения. Эти критерии нельзя отметить выполненными до реализации `PM-TASK-033` и приложения persistent/concurrency/crash/restart/exposure evidence.

#### 5.3.1. Два независимых lifecycle

Lifecycle approval и lifecycle исполняемого single-use action разделены. Поле одного автомата не может содержать состояние другого.

Закрытый approval lifecycle: `DRAFT`, `PENDING_EFFECTIVE`, `ACTIVE`, `REVIEW_REQUIRED`, `SUSPENDED`, `EXPIRED`, `REVOKED`, `SUPERSEDED`, `INVALIDATED`. Разрешены только переходы:

- `DRAFT -> PENDING_EFFECTIVE|SUSPENDED|REVOKED|INVALIDATED`;
- `PENDING_EFFECTIVE -> ACTIVE|SUSPENDED|EXPIRED|REVOKED|SUPERSEDED|INVALIDATED`;
- `ACTIVE -> REVIEW_REQUIRED|SUSPENDED|EXPIRED|REVOKED|SUPERSEDED|INVALIDATED`;
- `REVIEW_REQUIRED -> SUSPENDED|EXPIRED|REVOKED|SUPERSEDED|INVALIDATED`;
- `SUSPENDED -> EXPIRED|REVOKED|SUPERSEDED|INVALIDATED`.

`EXPIRED`, `REVOKED`, `SUPERSEDED`, `INVALIDATED` терминальны. Любой не перечисленный переход, неизвестное/отсутствующее/конфликтующее состояние или попытка поместить `RESERVED/CONSUMED` в approval lifecycle дают `DENY`.

Закрытый action lifecycle: `PENDING`, `RESERVED`, `DISPATCH_CLAIMED`, `IN_FLIGHT`, `RECONCILIATION_REQUIRED`, `CONSUMED`, `CANCELLED_NO_EFFECT`, `BLOCKED_NO_NEW_RISK`. Разрешены только переходы:

- `PENDING -> RESERVED|BLOCKED_NO_NEW_RISK`;
- `RESERVED -> DISPATCH_CLAIMED|CANCELLED_NO_EFFECT|BLOCKED_NO_NEW_RISK`;
- `DISPATCH_CLAIMED -> IN_FLIGHT|RECONCILIATION_REQUIRED`;
- `IN_FLIGHT -> CONSUMED|CANCELLED_NO_EFFECT|RECONCILIATION_REQUIRED`;
- `RECONCILIATION_REQUIRED -> CONSUMED|CANCELLED_NO_EFFECT`.

`CONSUMED` и `CANCELLED_NO_EFFECT` терминальны; `RECONCILIATION_REQUIRED` может сохраняться без blind retry. `effective_from <= evaluation_time < expires_at` остается полуинтервалом; в `review_due_at` Level B уже не создает новый/увеличивающий риск, в `expires_at` approval становится `EXPIRED`.

#### 5.3.2. Linearization, fencing и неизвестный внешний результат

Single-use action связывается с `action_id`, canonical payload/hash, idempotency ref, account, book, typed amount/limits, approval version/sequence, revocation/version epoch и expiry. Каждая reservation получает строго возрастающие `reservation_generation` и fencing token.

`DISPATCH_CLAIMED` — единственная linearization point перед adapter call. Durable transaction/CAS атомарно связывает действующий revocation/version epoch, approval version/sequence, reservation generation/fencing token и transactional outbox dispatch claim. Только победитель CAS с актуальным fencing token может вызвать adapter.

- revocation/expiry/mismatch до успешного claim означает `BLOCKED_NO_NEW_RISK`, adapter не вызывается;
- после `DISPATCH_CLAIMED` нельзя обещать отсутствие внешнего side effect: crash, timeout или неизвестный ACK переводят действие в `IN_FLIGHT` или `RECONCILIATION_REQUIRED`;
- reservation можно безопасно освободить в `CANCELLED_NO_EFFECT` только при durable proof, что dispatch claim/outbox send не состоялись;
- после claim допустимы только подтвержденные исходы `CONSUMED`, `CANCELLED_NO_EFFECT` либо сохранение `RECONCILIATION_REQUIRED`; blind retry запрещен;
- duplicate success возвращает сохраненный outcome без нового side effect; stale fencing token всегда отклоняется.

#### 5.3.3. Денежные действия и изменение конфигурации

Cash-like single-use (`REAL_BOOK_TRANSFER`, `DISTRIBUTION`) завершается финансовым outcome. Persistent configuration mutation (`REAL_ACCOUNT_OR_CREDENTIAL_CHANGE`, `REAL_SCOPE_EXPANSION`, `HARD_LIMIT_INCREASE`, `LEVERAGE_OR_MARGIN_CHANGE`) только применяет новую конфигурацию.

После `CONSUMED` configuration mutation новая конфигурация получает новый hash/version и состояние `PENDING_OPERATING_AUTHORIZATION` или `BLOCKED_NO_NEW_RISK`. Она не наследует старый operating approval и не разрешает заявки, пока отдельно не подтвержден новый `TIME_BOXED_REAL_CAPITAL` manifest, связанный с новым configuration hash и прошедший все gates.

#### 5.3.4. Review, invalidation, clock, revocation и reconciliation

Изменение account/credential identity ref, stage, book, venue, market, instrument, strategy, bot, limit, payload, owner/trust/second-factor binding либо hash policy/spec/acceptance/mandate/build/dataset немедленно делает старое approval неприменимым. Изменение benchmark, параметров, данных, costs/fill model, capacity, venue/API mechanics либо breach drift threshold независимо инвалидирует затронутое evidence. Новый approval не продлевает evidence и не превращает просмотренный holdout в unseen data.

Revocation append-only и терминален. Недоступный, stale или противоречивый lookup дает `DENY`. Supersession требует новой immutable версии, большего monotonic sequence и явного `supersedes_ref`; старая версия не реактивируется. Расширение действует только после полного activation gate, аварийное сужение — немедленно.

Trusted-clock gate сверяет UTC wall clock, monotonic elapsed clock и persistent last-seen checkpoint. Rollback wall clock, reboot/boot ambiguity, недоступный checkpoint либо превышение owner-approved skew дают `DENY`; численные skew/freshness значения остаются owner input.

Reconciliation по умолчанию разрешает только reads, cancel attempts и ledger/audit repair. Торговый side effect во время reconciliation допускается исключительно заранее утвержденной protective policy, подтвержденной venue capability и typed PRE/POST proof. Каждый metric в паре обязан одинаково связывать `metric_id`, unit, currency, valuation timestamp, horizon, netting set и convention.

Absolute, gross, contingent и margin risk magnitudes неотрицательны и требуют `post <= pre`. Signed net сравнивается по `abs(post_net) <= abs(pre_net)`; переход через знак запрещен, кроме точного завершения в нуле. Stress/scenario vector требует точного совпадения scenario set/hash и componentwise non-increase либо отдельно owner-approved conservative scalar functional. Отсутствующая scenario/dimension, отрицательный scalar risk magnitude, несовпадающая единица/валюта/time/horizon/netting/convention или иная несопоставимость дает `DENY`.

Expiry, revocation, suspension или invalidation запрещают новые и увеличивающие риск side effects, но не выключают доказуемый protective path для уже открытой экспозиции. После dispatch claim система не утверждает «zero external side effects», а обязана reconciliation/cancel/protection до доказуемого outcome.

#### 5.3.5. Sunset работающих заявок

Каждая увеличивающая риск resting/open/conditional заявка обязана иметь venue-enforced TIF/expiry не позже `approval.expires_at - working_order_cancel_reconciliation_buffer`. Численное значение buffer остается owner input. Неограниченная GTC либо conditional заявка без подтвержденной venue expiry дает `DENY`.

В cancel deadline система входит в `NO_NEW_RISK`, отменяет все opening/conditional orders и reconciles venue state; при revocation отмена начинается немедленно. Cancel-pending, unknown/lost ACK, venue halt, crash или restart не доказывают отсутствие fill: contingent exposure и reservation сохраняются, состояние остается `BLOCKED/RECONCILIATION_REQUIRED`, и zero-effect promise запрещен. Sunset завершен только после доказанного нулевого остатка opening/conditional orders. Продолжаться может только отдельно верифицированный protective reduce-only path.

#### 5.3.6. Профили действительности `площадка × риск`

Вариант 3 фиксирует метод, но не числа. Для Bitget и MOEX создаются разные versioned validity profiles. Обобщённый «биржевой default», межбиржевой fallback, наследование по похожему инструменту или автоматическое заполнение пропущенного значения запрещены. MOEX дополнительно разделяется как минимум по рынку, режиму/борду, классу инструмента, торговой сессии и broker/API capability; до отдельных policy/capability artifacts вся ветка MOEX остается `FUTURE/BLOCKED`.

Профиль выбирается ровно по одному точному ключу: `venue_id`, `venue_environment`, `market_id`, `capital_stage`, `approval_tier`, `validity_mode`, `action_class`, `risk_class`, точные ID/version/hash venue-capability и risk-policy. Account, book, instrument, strategy, bot, build и owner-decision scope дополнительно связываются точными refs/hashes в manifest. Wildcard, null, неизвестный enum, ноль совпадений или несколько `ACTIVE` совпадений дают `DENY/NO_NEW_RISK`.

Закрытая risk taxonomy для выбора профиля:

- `A0_NON_CAPITAL` — Development/Research/Replay/DRY_RUN/Paper без trade-capable endpoint;
- `B1_LIMITED_PILOT` — ограниченный Pilot operating scope;
- `B2_EXISTING_PRODUCTION` — действующий Production operating scope без расширения;
- `B3_CASH_ACTION` — перевод между реальными books или distribution;
- `B4_AUTHORITY_MUTATION` — account/credential/scope/hard-limit/leverage/margin mutation.

Более высокий класс не может получать менее консервативные полномочия при сопоставимом действии. Для каждого временного поля schema указывает safety direction: `SAFER_DECREASE`, `SAFER_INCREASE` или `NON_MONOTONE_OWNER_ONLY`. Автоматическая рекалибровка допустима только если новое множество разрешённых действий является подмножеством прежнего: она может сократить TTL/activation window, увеличить защитный buffer, приостановить или инвалидировать профиль, но не расширить scope, увеличить TTL, уменьшить buffer или восстановить прежний максимум. Несопоставимость означает `DENY`.

В профиле строго разделены три слоя:

1. `owner_hard_bounds` — численные верхние/нижние границы, утверждённые владельцем;
2. `calibration_recommendation` — неавторизующая рекомендация из evidence;
3. `owner_selected_effective_values` — фактически утверждённые числа, которые не могут нарушать hard bounds.

Рекомендация не создаёт полномочий. Пока любой обязательный owner bound/effective value отсутствует, профиль имеет `eligible_for_authorization=false`. Временные величины кодируются только целыми миллисекундами; boolean, float, строковое число и неявная конверсия отклоняются.

`owner_hard_bounds` и `owner_selected_effective_values` получают полномочия только из одного exact owner-authority manifest binding: immutable ref/hash, version, monotonic sequence и canonical owner payload hash. Canonical owner payload обязан включать `profile_id`, `profile_version`, canonical profile payload hash и полные оба numeric layers. Missing/mismatch/replay либо подмена любого слоя дают `DENY`; calibration recommendation не входит в owner authority и не может заменить подпись. В DRAFT все owner bindings имеют typed `ABSENT_DENY/UNRESOLVED` sentinel и zero hash/sequence, которые никогда не трактуются как authority.

Даже корректная owner signature не повышает слой со статусом `UNRESOLVED`: для будущего ACTIVE оба owner layers обязаны иметь точный статус `VERIFIED`, а calibration — `NON_AUTHORIZING_RECOMMENDATION`. Для `SAFER_DECREASE` effective value не превышает owner hard bound; для `SAFER_INCREASE` effective value не меньше owner hard bound; `NON_MONOTONE_OWNER_ONLY` требует точного owner-selected значения и не меняется автоматикой. Missing, type-incomparable или outside-bound значение дает `DENY`.

Закрытая action matrix задаёт применимые числа. `PILOT_OPERATING_SCOPE/B1_LIMITED_PILOT` и `PRODUCTION_OPERATING_SCOPE/B2_EXISTING_PRODUCTION` в `TIME_BOXED_REAL_CAPITAL` требуют `operating_ttl_ms`, `cancel_reconciliation_buffer_ms`, `dispatch_guard_ms`, `clock_skew_tolerance_ms`, `revocation_snapshot_max_age_ms`, `review_lead_time_ms`, `reconciliation_escalation_deadline_ms` и запрещают single-use activation window. Cash/config actions в `ONE_TIME_REAL_CAPITAL` требуют `single_use_activation_window_ms`, `dispatch_guard_ms`, `clock_skew_tolerance_ms`, `revocation_snapshot_max_age_ms`, `reconciliation_escalation_deadline_ms` и запрещают operating-only поля. `A0_NON_CAPITAL/LONG_LIVED_NON_CAPITAL` не принимает real-capital duration fields. Missing, extra или inapplicable field и несогласованный stage/tier/action/risk tuple дают `DENY`.

`reconciliation_escalation_deadline_ms` — только срок обязательной эскалации человеку/защитному процессу. Его наступление никогда не доказывает отсутствие fill, не освобождает exposure/reservation и не снимает `NO_NEW_RISK/RECONCILIATION_REQUIRED` до verified terminal venue outcome. Для автоматики меньший escalation deadline является более безопасным.

Каждый duration ограничен техническим representation maximum, предназначенным только для предотвращения overflow/DoS и не являющимся owner-approved TTL. Profile schema связывается exact schema ID/version/hash; profile имеет canonical payload hash, supersedes ref/hash/sequence, а future `ACTIVE` требует evidence refs/hashes/issuer/as-of/freshness. DRAFT sentinels всегда дают `DENY`; signed persistent registry остаётся будущей runtime реализацией.

Утверждение, ослабление или замена validity-profile hard/effective values является отдельным `VALIDITY_PROFILE_AUTHORITY_CHANGE` класса `B4_AUTHORITY_MUTATION`. Оно требует Level-B signature и независимого второго подтверждения одного payload, durable single-use consumption, выпуска нового profile/configuration hash и отдельного time-boxed operating manifest для нового hash. Старый operating manifest не наследуется.

Автоматическое ужесточение не переписывает подписанный owner envelope. Оно выпускает отдельный versioned protective overlay с provenance и полной историей; effective authorization вычисляется restrictive intersection owner envelope и overlay. Overlay может только сузить action set, не может rebound без нового owner epoch и не изменяет calibration или подписанный payload задним числом.

Effective durations обязаны совпадать с фактическими временными границами: operating interval не длиннее `operating_ttl_ms`, single-use interval не длиннее activation window, `review_due_at` соблюдает review lead, commit-time имеет dispatch guard, а age revocation snapshot не превышает max age. Все derived timestamps входят в canonical profile/owner payload; mismatch и off-by-one в небезопасную сторону дают `DENY`.

Будущий `ACTIVE` profile использует отдельную immutable ACTIVE schema, а не мутированный DRAFT. Evidence status `VERIFIED` вычисляется детерминированным evaluator из versioned evidence manifest: event definitions, time origin, censoring reasons, unknown outcomes, competing-risk estimator/version, tail quantile/confidence, clustering unit, raw/cluster/effective sample, preregistered thresholds, sealed window hashes/cutoffs, holdout access log и forward confirmation result. Пустой либо самодекларированный `VERIFIED` manifest дает `DENY`.

Exact selection дополнительно связывает calibration-stratum ID/hash и runtime regime: API/protocol version, account mode, order type, TIF, session, liquidity/volatility regime и degraded state. Venue capability и risk policy не считаются проверенными по одному ID/hash: evaluator загружает exact bytes, проверяет provenance/lifecycle и сопоставляет venue/environment/market/API/session/board/instrument class/order mechanics с request/profile. Непокрытая stratum или semantic mismatch дает `DENY`.

Sunset deadline равен самому раннему известному cutoff нового риска среди approval review/expiry, evidence, capability, policy и protection validity, минус owner buffer. Завершение sunset требует durable terminal outcome каждого order, полного fill/trade watermark, сверки position/balance и triggered child orders, а также атомарного переноса либо сохранения reservation; zero open-order count сам по себе недостаточен.

Cross-risk ordering проверяется по всем одновременно ACTIVE profiles одного comparable family: более высокий класс не может иметь более широкое action set, больший `SAFER_DECREASE` или меньший `SAFER_INCREASE`. Monotone comparison использует только action-specific vector и immutable registry history текущего owner epoch. `DEVELOPMENT` входит в `A0_NON_CAPITAL` во всех schema/validators.

Reconciliation escalation отсчитывается от первого durable unknown/cancel-pending event. К deadline требуется durable dispatch и acknowledgment escalation; overdue без acknowledgment suspends/invalidates профиль, сохраняя exposure/reservation и `NO_NEW_RISK/RECONCILIATION_REQUIRED`.

Калибровка отдельно оценивает operating-approval TTL, one-time activation window, order TIF, cancel/reconciliation buffer, revocation freshness, reconciliation horizon и evidence age. Latency components, timeout, lost/unknown ACK, late fill и cancel outcome хранятся раздельно; цензурированные наблюдения не выбрасываются. Cancel/late-fill моделируются как time-to-event с censoring/competing risks, а не средним временем. Используются заранее зафиксированные tail quantiles, односторонняя uncertainty, effective sample size, recent rolling window, stress archive и отдельное forward confirmation window без настройки на holdout.

Evidence стратифицируется по venue/API version/account mode/order type/TIF/session/liquidity/volatility/degraded state. Разреженный, устаревший, drifted или непокрытый режим приводит к owner-approved более строгому fallback внутри того же точного профиля либо к `DENY`; объединять Bitget и MOEX или разные risk classes для получения достаточного sample запрещено. Изменение API/session model/account topology/clock/build, breach tail bound либо рост unknown outcomes автоматически только `SUSPEND/INVALIDATE` или ужесточает профиль.

Lifecycle профиля: `DRAFT -> EVIDENCE_READY -> OWNER_APPROVAL_PENDING -> ACTIVE`; из `ACTIVE` допустимы только `SUSPENDED`, `EXPIRED`, `REVOKED`, `SUPERSEDED`, `INVALIDATED`. Terminal version не реактивируется. Совместимые численные constraints объединяются наиболее ограничительным meet; несовместимые unit/direction/horizon дают `DENY`. Профиль непригоден, если operating TTL не превышает сумму cancel/reconciliation buffer и dispatch guard либо если working-order expiry нарушает sunset constraint.

Решение записывается как immutable `PM-DEC-003 v2`, которое точно ссылается на путь и SHA-256 неизменённого `PM-DEC-003 v1`. Изменяемый `current` alias запрещён в authorization chain. Позднейшие численные профили выпускаются отдельными versioned artifacts и связываются точными hash; детерминированный generator/replay обязан воспроизводить тот же canonical payload и результат.

`PM-REQ-043`: каждый approval имеет закрытые `approval_tier` и `validity_mode`: Level A — `LONG_LIVED_NON_CAPITAL`; Level B — ровно один из `TIME_BOXED_REAL_CAPITAL` или `ONE_TIME_REAL_CAPITAL`. Missing/unknown/incompatible значение дает `DENY`.

`PM-REQ-044`: temporal validity вычисляется в UTC по полуинтервалу `effective_from <= evaluation_time < expires_at`; неверный порядок timestamp, недоверенные часы или неопределенный evaluation time дают `DENY`.

`PM-REQ-045`: Level A действует только для неизменного non-capital scope и точных artifact hashes; после `review_due_at` он не утверждает новую baseline, experiment/evidence admission или promotion до новой версии.

`PM-REQ-046`: Level B всегда time-boxed либо single-use, не продлевается автоматически или задним числом и остается `eligible_for_authorization=false` до owner-approved numeric validity profile и всех остальных gates.

`PM-REQ-047`: single-use action требует atomic durable reservation/consumption по `action_id` и idempotency key; timeout/unknown result дает `RECONCILIATION_REQUIRED`, а replay не создает новый side effect.

`PM-REQ-048`: любое изменение bound identity/scope/limit/payload/trust/artifact hash инвалидирует старое approval; drift или изменение research/execution baseline независимо инвалидирует затронутое evidence.

`PM-REQ-049`: revocation append-only и terminal; unavailable/stale/conflicting revocation state дает Level-B `DENY`, а восстановление требует новой версии с большим sequence.

`PM-REQ-050`: expiry/revocation/suspension/invalidation запрещают новый или увеличивающий риск, сохраняя только отдельно разрешенные reduce-only protection и reconciliation для открытой экспозиции.

`PM-REQ-051`: supersession использует новую immutable версию, monotonic sequence и `supersedes_ref`; старая версия terminal и не реактивируется, расширение не действует до полного gate, сужение применяется немедленно.

`PM-REQ-052`: validity mandate, approval, evidence, venue capability и runtime protection проверяется независимо; ни один объект не продлевает другой, эффективен самый ограничительный результат.

`PM-REQ-053`: каждая смена lifecycle state журналируется append-only с object/version, old/new state, UTC evaluation time, reason/trigger, actor/source ref, sequence, hashes и action/idempotency reference без секретов.

`PM-REQ-054`: approval lifecycle и single-use action lifecycle имеют разные закрытые state sets и transition matrices; любое смешение или неразрешенный переход дает `DENY`.

`PM-REQ-055`: `DISPATCH_CLAIMED` является linearization point; один durable transaction/CAS связывает revocation/version epoch, approval sequence, reservation generation/fencing token и outbox claim. Revocation до claim запрещает adapter call; после claim неизвестный outcome требует reconciliation и не считается доказательством отсутствия внешнего эффекта.

`PM-REQ-056`: release reservation допустим только с durable proof отсутствия dispatch; после claim итог только `CONSUMED`, `CANCELLED_NO_EFFECT` либо остающийся `RECONCILIATION_REQUIRED`.

`PM-REQ-057`: consumed persistent configuration mutation переводит новый configuration hash в `PENDING_OPERATING_AUTHORIZATION/BLOCKED_NO_NEW_RISK`; operating orders требуют отдельный time-boxed manifest, связанный с новым hash.

`PM-REQ-058`: reconciliation по умолчанию ограничен reads/cancel/ledger repair. Protective trade требует заранее утвержденную policy, venue capability и typed PRE/POST metrics, одинаково связанные с `metric_id`, unit, currency, valuation timestamp, horizon, netting set и convention. Absolute/gross/contingent/margin magnitudes неотрицательны и требуют `post <= pre`; signed net требует `abs(post) <= abs(pre)` без sign crossing, кроме exact zero; stress vector требует exact scenario-set/hash и componentwise non-increase либо owner-approved conservative scalar functional. Missing scenario/dimension или incomparable proof дает `DENY`.

`PM-REQ-059`: trusted clock использует UTC wall, monotonic elapsed и persistent last-seen; rollback, boot ambiguity, missing checkpoint или excessive skew дают `DENY`, а численный tolerance утверждает владелец.

`PM-REQ-060`: все входы validity evaluator типизированы строго: boolean не заменяется integer/string, timestamp обязан быть strict UTC, а missing/`None`/unknown value дает `DENY` без исключения и без authority.

`PM-REQ-061`: каждая увеличивающая риск resting/open/conditional заявка имеет venue-enforced TIF/expiry не позже `approval.expires_at - owner-approved cancel_reconciliation_buffer`; GTC или conditional order без доказанной bounded expiry дает `DENY`. В deadline система входит в `NO_NEW_RISK`, отменяет все opening/conditional orders и reconciles venue state; revocation запускает немедленную отмену.

`PM-REQ-062`: cancel-pending/unknown/lost ACK, halt, crash или restart сохраняют contingent exposure и reservation в `BLOCKED/RECONCILIATION_REQUIRED`, потому что late fill остается возможным и zero-effect promise запрещен. Sunset завершается только при доказанном нулевом остатке opening/conditional orders; продолжаться может лишь verified protective reduce-only path.

`PM-REQ-063`: validity profile выбирается только по точному закрытому ключу `venue × environment × market × stage × approval tier × validity mode × action class × risk class × capability/risk-policy identity`; wildcard, fallback, zero/multiple matches и cross-venue/risk inheritance дают `DENY`.

`PM-REQ-064`: Bitget и MOEX имеют отдельные profile families и evidence. MOEX дополнительно связывает рынок/борд/класс/сессию/broker API и остается `FUTURE/BLOCKED` без отдельной policy и capability profile.

`PM-REQ-065`: `owner_hard_bounds`, неавторизующая `calibration_recommendation` и `owner_selected_effective_values` хранятся раздельно; ACTIVE требует точные статусы `VERIFIED/VERIFIED` и `NON_AUTHORIZING_RECOMMENDATION`. Для `SAFER_DECREASE` effective не выше hard bound, для `SAFER_INCREASE` не ниже, а `NON_MONOTONE_OWNER_ONLY` требует exact owner-selected value; рекомендация никогда не создаёт полномочий.

`PM-REQ-066`: все durations кодируются целыми миллисекундами без coercion; missing, boolean, float, string, отрицательное или неизвестное значение дает `DENY`.

`PM-REQ-067`: каждому численному полю назначается safety direction; автоматика может применить только изменение, чье разрешённое action set является подмножеством предыдущего. Relaxation, rebound или unknown comparison требуют новой owner-approved версии и до неё дают `DENY`.

`PM-REQ-068`: lifecycle validity profile закрыт и terminal versions не реактивируются; lookup допускает ровно один неистёкший `ACTIVE` profile с точными lifecycle timestamps и hashes.

`PM-REQ-069`: calibration evidence сохраняет страты, latency components, censored/unknown outcomes, tail quantile, one-sided uncertainty, raw/cluster/effective sample, rolling/stress/forward windows и holdout access history; regime/degraded/access-purpose используют закрытые enums, а provenance exact связывается owner-bound threshold artifact. Текущий pure validator подтверждает только declared canonical shape и причинный порядок, но не корректность estimator, статистическую истинность либо owner authority; среднее, pooled venue sample или post-hoc tuning недостаточны.

`PM-REQ-070`: sparse, stale, drifted, incomplete или incompatible calibration evidence может только сузить, suspend/invalidates профиль либо дать `DENY`; автоматически расширять TTL/scope или уменьшать protective buffer запрещено.

`PM-REQ-071`: profile invalidation triggers включают venue/API/session/account-topology/clock/build change, tail-bound breach, excessive unknown/late-fill outcome и evidence expiry; восстановление требует новой evidence/owner-approved version.

`PM-REQ-072`: operating TTL обязан быть строго больше cancel/reconciliation buffer плюс dispatch guard. Exact order identity и venue-enforced `order_expiry_at` связываются с единым sunset deadline: самый ранний cutoff среди approval/evidence/capability/risk-policy/runtime-protection минус buffer. Expiry позже этого deadline при любом earliest source делает профиль непригодным и даёт `DENY`.

`PM-REQ-073`: generator, canonicalization и replay validity profile детерминированы и связывают exact decision/profile/evidence/policy/capability/schema refs и hashes; schema SHA-256 вычисляется по exact bytes до parsing и сверяется с exact schema ID/version. Изменение любого байта инвалидирует binding.

`PM-REQ-074`: `PM-DEC-003 v2` supersedes неизменённый v1 только по exact path/hash и является self-contained; mutable `current` alias не участвует в authorization discovery или evaluation.

`PM-REQ-075`: пока owner не утвердил все обязательные численные bounds/effective values отдельного профиля, `eligible_for_real_capital_authorization=false` независимо от качества calibration recommendation.

`PM-REQ-076`: owner hard bounds и effective values связываются одним exact immutable owner manifest ref/hash/version/monotonic sequence; canonical owner payload включает profile identity/payload hash и оба numeric layers. Missing/mismatch/replay дает `DENY`, calibration не является owner authority.

`PM-REQ-077`: closed action/stage/tier/validity/risk matrix определяет обязательные и запрещённые numeric fields отдельно для operating, single-use и non-capital profiles; missing, extra или inapplicable field дает `DENY`.

`PM-REQ-078`: reconciliation escalation deadline только ускоряет эскалацию и никогда не доказывает no-fill, не освобождает exposure/reservation и не снимает `NO_NEW_RISK/RECONCILIATION_REQUIRED` до verified terminal outcome.

`PM-REQ-079`: каждый duration имеет строгий integer-ms тип и технический maximum до любых datetime arithmetic; overflow, bool/float/string и превышение representation bound дают `DENY`. Этот bound не является owner-approved TTL.

`PM-REQ-080`: venue/environment/market/stage/tier/validity/action/risk образуют закрытый coherent tuple; смешение Bitget/MOEX environment, noncapital/live stage или action/risk class дает `DENY`.

`PM-REQ-081`: schema/profile/supersession/evidence/owner manifests связываются exact IDs, versions, hashes и canonical payloads. Release snapshot проверяется по закрытому member manifest без duplicates/path traversal и остаётся non-authoritative.

`PM-REQ-082`: любое утверждение или ослабление validity profile является single-use `VALIDITY_PROFILE_AUTHORITY_CHANGE/B4_AUTHORITY_MUTATION`, требует Level-B signature и independent second factor. Canonical payload включает `previous_configuration_sha256`, выведенный и проверенный по exact prior operating-manifest bytes и registry record; `new_configuration_sha256` обязан отличаться именно от previous configuration hash. Старый configuration или operating manifest не наследуется.

`PM-REQ-083`: автоматическое ужесточение хранится отдельным immutable protective overlay; owner envelope не мутируется, effective authority является restrictive intersection, а rebound невозможен без нового owner epoch.

`PM-REQ-084`: absolute timestamps детерминированно соответствуют effective durations: operating/single-use window, review lead, dispatch guard и revocation freshness проверяются вместе и входят в canonical payload; mismatch даёт `DENY`.

`PM-REQ-085`: future ACTIVE использует отдельную exact-hash ACTIVE schema и будущий deterministic statistical evidence evaluator; status `VERIFIED` без полного censored competing-risk/tail/sample/window/holdout/forward evidence manifest даёт `DENY`. Текущий declared-shape/causality validator намеренно не проверяет estimator correctness, statistical truth или owner authority и всегда остаётся non-authorizing.

`PM-REQ-086`: exact profile/request key включает calibration-stratum ID/hash и текущие API/account/order/TIF/session/liquidity/volatility/degraded-state values; missing или mismatched coverage даёт `DENY`.

`PM-REQ-087`: capability и risk-policy artifacts проверяются по exact bytes, lifecycle и closed semantic scope, а не только registry hash membership; scope/API/session/order-mechanics mismatch даёт `DENY`.

`PM-REQ-088`: strict sunset связывает exact order identity и expiry и использует один общий с feasibility helper earliest new-risk cutoff всех independently expiring mandatory objects минус buffer. `order_expiry_at` позже deadline запрещён независимо от того, был earliest approval, evidence, capability, policy или protection; zero open-order count без terminal order outcomes, fill watermark, position/balance/child-order reconciliation и reservation proof не завершает sunset.

`PM-REQ-089`: cross-risk partial order проверяется только для B1/B2 profiles с одним canonical exact resolved scope binding: venue/environment/market/API/account/order/TIF/session/capability/policy/calibration/regime. ACTIVE comparison запрещает `UNRESOLVED*`, `*_DENY`, `PENDING*`, `NOT_IMPLEMENTED*` и all-zero capability/calibration hashes, хотя DRAFT taxonomy сохраняет такие fail-closed sentinels. Caller-supplied family label не создаёт comparability; cross-venue, unresolved binding или любой scope mismatch даёт `DENY`.

`PM-REQ-090`: monotone overlay и cross-risk comparison используют только exact action-specific vector и complete immutable contiguous owner-epoch history. Одновременный `ACTIVE` выводится из exact profile identity/hash, lifecycle interval и non-superseded history records, а не caller boolean; caller-declared ACTIVE history не может повысить DRAFT unresolved scope. Omitted/reset history, unresolved binding, extra/inapplicable field или rebound дают `DENY`. Pure history shape остаётся non-authorizing и не делает ACTIVE runtime доступным.

`PM-REQ-091`: reconciliation escalation due-time выводится из первого durable unknown/cancel-pending event; overdue без durable dispatch/ack suspends/invalidates profile, но не освобождает exposure/reservation и не снимает reconciliation.

`PM-REQ-092`: calibration recommendation проходит strict type/technical-bound/directional comparison с owner hard bounds; outside-bound recommendation даёт `DENY`, даже оставаясь неавторизующей.

`PM-REQ-093`: `DEVELOPMENT` согласованно входит в `A0_NON_CAPITAL` в spec, schemas, tuple matrix и validators.

### 5.3.1. Граница fix-only validator evidence

Текущая реализация содержит только deterministic pure validators и adversarial fixtures. Успешный shape-result всегда маркируется `NON_AUTHORIZING`; он не заменяет signature/trust root, persistent registry, trusted clock, venue telemetry, order ledger или reconciliation dispatcher. Любой профиль либо schema, заявляющие `ACTIVE`, до отдельной exact-byte ACTIVE schema и runtime evidence evaluator получают ранний `DENY_ACTIVE_SCHEMA_OR_RUNTIME_EVIDENCE_UNAVAILABLE`.

Closed lookup tuple дополнительно включает calibration-stratum ID/hash, API/protocol version, account mode, order type, TIF, session, liquidity/volatility regime и degraded state. Exact-byte capability/risk/evidence helpers проверяют lifecycle, freshness, provenance и semantic scope, но после успешной проверки всё равно не выдают `ALLOW`.

Для Bitget runtime scope закрыто связывает `risk_policy_id`, version и SHA-256 непосредственно с exact bytes `governance/risk-policy.toml`; caller-supplied hash другого artifact не принимается. Parser дополнительно подтверждает `bitget-btc-v1` v1, Bitget USDT-margined futures, exact allowlist `[BTCUSDT]`, `limit_only` и `live_trading.enabled = false`. Те же ID/version в произвольных либо мутированных bytes получают `DENY`; успешный shape-result всё равно не является runtime trust.

Venue mechanics используют explicit reject-all default и closed matrix. Bitget допускает только `PAPER_SIMULATOR|BITGET_TESTNET|BITGET_PRODUCTION × BITGET_USDT_FUTURES × BITGET_API_V2 × ONE_WAY_MODE × BITGET_24X7` и `LIMIT` с `GTC|IOC|FOK|POST_ONLY`; futures+CASH, неизвестный `KRAKEN`, mixed environment/API/market/account/session и unsupported order/TIF получают `DENY`. `MARKET` запрещён policy `limit_only`, а MOEX остаётся `FUTURE_BLOCKED`.

B4 `VALIDITY_PROFILE_AUTHORITY_CHANGE` связывает owner-selected single-use window и canonical absolute timestamps, требует раздельных Level-B/second-factor identities и один global closed append-only durable registry `validity-profile-authority-global-v1` для всех owner epochs. Его protocol genesis не выбирается caller: reserved genesis owner epoch равен `0`, `base_sequence = latest_sequence = latest_owner_epoch = 0`, records пусты, а canonical empty-genesis SHA-256 закреплён как `00d45207979fc16245c40b9c850d7cad99b664e4678a2f100350ebae15705c34`. Любое изменение registry ID/scope/genesis/digest получает `DENY`.

После genesis registry хранит contiguous sequence/CAS до `latest_sequence`; owner epoch каждой записи является положительной version value, не убывает, а `latest_owner_epoch` точно равен epoch последней записи. Proposal owner epoch не может быть раньше этого head. Action ID, parent profile hash, parent operating-manifest hash, их pair и CAS token индексируются через всю историю epochs и потребляются независимо и единожды: epoch-scoped reset, скрытый prefix, две ветви от одного parent либо повторное использование любого parent component получают `DENY`.

Все перечисленные проверки registry являются только проверками caller-supplied shape. Единственный успешный результат такого helper — `NON_AUTHORIZING_B4_REGISTRY_SHAPE_VALID`; он не доказывает current/fresh checkpoint, persistence, atomic consumption или полноту runtime history. B4 readiness требует независимо trusted current registry checkpoint из будущего PM-DEC-007 runtime trust root. Поскольку такого capability сейчас нет, и epoch-9 canonical genesis, и тот же stale genesis для epoch 10 получают `DENY_B4_CURRENT_REGISTRY_CHECKPOINT_OR_RUNTIME_TRUST_UNAVAILABLE`; self-declared consumption record также не доказывает durable consumption.

Новый operating manifest принимается только как canonical exact bytes с canonical PurePosix versioned ref, hash, timebox и точными bindings change action/payload/new profile/configuration. B4 payload отдельно связывает `previous_configuration_sha256`, выведенный из exact prior-manifest bytes и соответствующей registry record; new configuration обязан отличаться от него. Его caller-supplied registry/prior exact-byte shape связывает last prior manifest посредством exact supersedes ref/version/sequence/hash и требует следующий version/sequence без replay или gap. Каждому `(manifest_ref, manifest_version, manifest_sequence)` соответствует ровно один digest; alias path, non-increasing sequence, identity/digest conflict, reused prior configuration, старый либо malformed manifest получают `DENY`. Pure helper остаётся `NON_AUTHORIZING`: shape не доказывает trust, currentness, completeness, runtime persistence или trust-root authority.

Evidence manifest требует отдельного owner-bound exact-byte threshold artifact для minimum raw/cluster/effective sample, minimum observations каждого sealed window и exact required provenance refs. Liquidity/volatility/degraded values совпадают с closed profile enums, unresolved значения запрещены, а holdout access purpose закрыт на `FINAL_FORWARD_CONFIRMATION`. Не существует implicit numeric default: отсутствие binding либо actual count ниже owner minimum даёт `DENY`; holdout access и sealed windows не могут находиться после `AS_OF`, evaluation time или profile expiry. Успех `NON_AUTHORIZING_DECLARED_EVIDENCE_SHAPE_CAUSALITY_VALID` означает только declared canonical shape/causality; estimator correctness, statistical truth и owner authority остаются непроверенными до будущего evaluator.

Temporal binding требует положительный operating interval и причинный порядок `REVOCATION_SNAPSHOT_AT <= EVALUATED_AT <= COMMIT_AT < REVIEW_DUE_AT < EXPIRES_AT`, где `EFFECTIVE_FROM < REVIEW_DUE_AT`; freshness измеряется на commit как `COMMIT_AT - REVOCATION_SNAPSHOT_AT`. Evaluation либо commit на границе review или после неё получают `DENY`. Первый durable unknown, escalation dispatch и ACK не могут быть timestamp из будущего либо нарушать causal order. Cross-risk dominance допускается только для operating-профилей пары `B1_LIMITED_PILOT -> B2_EXISTING_PRODUCTION` с одним canonical exact resolved scope. Unresolved/pending/not-implemented/deny sentinels и zero capability/calibration hashes непригодны для ACTIVE comparison; caller ACTIVE history не превращает DRAFT scope в resolved. Simultaneous ACTIVE выводится из complete immutable contiguous owner-epoch history; caller family/active flags, cross-venue mismatch, `NON_CAPITAL`, `SINGLE_USE` и неизвестный action family не являются обходом. Shape остаётся `NON_AUTHORIZING`, а runtime ACTIVE evaluator отсутствует.

Release verifier применяет source-side `lstat`: release directory и его ancestors не могут быть symlink, каждый source member обязан быть regular file/directory и после resolve оставаться внутри release root. Архивная проверка duplicate/traversal/symlink/special members остаётся независимой.

Protective overlay имеет непустой immutable ID, exact action-specific vector и complete immutable owner-epoch history; late ACK не восстанавливает authority и не разрешает rebound.

Feasibility и strict sunset используют один helper для exact order identity/expiry и deadline `min(approval,evidence,capability,risk-policy,runtime-protection) - buffer`; любой источник может быть earliest, а expiry позже границы даёт `DENY`. Sunset завершается только через strict validator после terminal order-ledger outcomes, complete fill/trade watermark, position/balance/child-order reconciliation и durable reservation release/transfer proof. Legacy bounded-order helper не может вернуть reconciled: confirmed cancel + zero open orders + generic venue reconciliation без этих доказательств сохраняет `RECONCILIATION_REQUIRED_NO_ZERO_EFFECT_PROMISE`. Поздняя escalation ACK также не снимает `RECONCILIATION_REQUIRED/NO_NEW_RISK`.

### 5.4. Текущее состояние

| Scope | Целевой статус | Эффективный статус сейчас | Основание |
|---|---|---|---|
| Bitget, USDT futures, BTCUSDT | `TARGET` | `ACTIVE` только для разработки, DRY_RUN/Paper | `bitget-btc-v1` и TB-001 |
| Scalping / intraday | `TARGET` | `ACTIVE` только в текущем Phase-1 scope | Owner-locked 15/85 policy |
| MOEX | `TARGET` | `FUTURE/BLOCKED` | Нет отдельной policy, ТЗ и owner manifest |
| Swing / medium-term | `TARGET` | `FUTURE/BLOCKED` | Нет отдельной стратегии и policy |
| Гибридный аллокатор | `TARGET` | `SHADOW_ONLY` | Нет права записи реальных лимитов |
| `PILOT_LIMITED_LIVE` | `TARGET` | `BLOCKED` | Нет aggregate hard caps, topology и owner manifest |
| `PRODUCTION_LIVE` | `TARGET` | `BLOCKED` | Нет Pilot evidence и отдельного решения |
| Live trading | — | `false` | Owner-locked governance baseline |

`PM-REQ-003`: новое venue, instrument, account, capital book, horizon, strategy или bot не наследуют разрешение по сходству названия либо базового актива.

`PM-REQ-004`: значения Phase 1 не копируются в мандат как второй редактируемый источник истины; active overlay ссылается на точные `policy_id`, version и hash.

## 6. Периметр портфеля и NAV

### 6.1. Определение периметра

Портфельный NAV должен вычисляться только по явному перечню включенных юридических счетов, субсчетов, кошельков, активов, обязательств и книг капитала. Актив не входит в управляемый капитал только потому, что принадлежит владельцу или технически виден системе.

Для каждого элемента периметра фиксируются:

- `perimeter_item_id`;
- legal owner/account reference без секретов;
- venue/broker/custodian;
- capital book;
- native currency и valuation method;
- включение в reporting NAV, risk NAV и stressed liquidation NAV;
- обязательства и ограничения доступности;
- effective timestamp и статус качества данных.

`PM-REQ-005`: точный NAV perimeter является owner decision `PM-DEC-004`. До решения консолидированный NAV имеет статус `INDICATIVE`, не разрешает капитал и выплаты.

### 6.2. Три вида NAV

1. **Reporting NAV** — сверенная официальная оценка для отчетности.
2. **Risk NAV** — консервативная оперативная база для риск-решений.
3. **Stressed liquidation NAV** — оценка после haircuts, exit costs, gap, depeg и доступности ликвидности.

Stale, disputed, estimated или unreconciled стоимость не может увеличивать risk capacity, distributable profit либо apparent benchmark outperformance.

## 7. Учет результата в RUB

RUB является базовой валютой консолидации, но не предписывает хранить или конвертировать все активы в RUB. Параллельно сохраняется нативный учет каждого счета и инструмента.

Для USDT-контура базовая цепочка:

`V_RUB = V_USDT × Q_USDT/USD × Q_USD/RUB`.

Отдельно отражаются:

- constant-FX strategy result;
- counterfactual/decision PnL;
- execution shortfall;
- booked PnL по подтвержденным fills;
- fees, funding, borrow, налоги и другие денежные потоки;
- stablecoin basis/depeg;
- FX translation;
- attribution residual.

Применяется единая знаковая конвенция: прибыль и входящий инструментальный cash flow положительны; убыток, cost и исходящий cash flow отрицательны. Для каждой нативной валюты:

`BookedPreCostPnL = DecisionPnL - ImplementationShortfall`,

где положительный `ImplementationShortfall` означает ухудшение относительно заранее замороженной reference price. Затем:

`NetNativeResult = BookedPreCostPnL + InstrumentCashFlows + ExplicitCosts`,

где комиссии, funding/borrow и налоги входят ровно в один заранее определенный компонент. Если они уже включены в booked cash ledger, повторное вычитание запрещено.

Для консолидации:

`ΔNAV_RUB - ExternalFlows_RUB = ConstantFXNetResult_RUB + FXTranslation_RUB + StablecoinBasis_RUB + AttributionResidual_RUB`.

Методика фиксирует порядок последовательного attribution, поэтому FX/stablecoin cross-term всегда попадает в один определенный компонент. `AttributionResidual` рассчитывается автоматически как разность сторон identity, не вводится вручную, классифицируется по причине и не может использоваться как балансирующая строка. Превышение утвержденной абсолютной или относительной tolerance делает отчет и evidence недействительными.

`PM-REQ-006`: изменение NAV за вычетом внешних cash flows должно сверяться с суммой торгового результата, инструментальных cash flows, издержек, FX/stablecoin effects и residual.

`PM-REQ-007`: spread/slippage нельзя одновременно включить в fill и повторно вычесть как расход.

`PM-REQ-008`: финансовые расчеты используют decimal/fixed-point. Каждое значение содержит currency, unit, scope, time horizon, valuation timestamp и источник.

`PM-REQ-031`: accounting profile должен версионировать reference-price rule, inclusion каждого cost/cash-flow, FX attribution order, rounding и residual tolerance; отсутствие профиля блокирует финансово значимую отчетность.

## 8. Доходность и опыт владельца

### 8.1. Обязательные показатели

- RUB time-weighted return (`TWR`) как показатель инвестиционного процесса, очищенный от внешних вводов/выводов;
- money-weighted return (`MWR/XIRR`) как отдельный показатель опыта владельца;
- геометрическая/log return и итоговый net PnL;
- rolling/subperiod результаты на заранее определенных интервалах;
- excess return относительно замороженного benchmark;
- вклад стратегии в портфельный результат и риск;
- drawdown depth, duration, time under water и recovery;
- uncertainty interval и устойчивость по режимам.

Sharpe, Sortino, win rate и profit factor могут быть диагностическими метриками, но не являются единственным admission/allocation gate.

`PM-REQ-009`: внешний ввод RUB увеличивает NAV, но не создает TWR или strategy alpha.

`PM-REQ-010`: годовые показатели, вычисленные из короткого окна, маркируются как экстраполяция и не применяются как самостоятельный gate.

`PM-REQ-032`: до расчета TWR фиксируются valuation subperiods, timing intraday flows, linking formula, precision, zero/negative NAV и stale-valuation behavior. Для XIRR фиксируются day-count, timestamp precision, numerical method, root-selection и статусы `UNDEFINED_NO_ROOT`/`UNDEFINED_MULTIPLE_ROOTS`. Внутренний transfer между книгами является внешним потоком книги, но не консолидированного портфеля.

## 9. Система бенчмарков

Используется не один универсальный benchmark, а иерархия:

1. **Capital-preservation benchmark** — owner-approved RUB cash/cash-equivalent opportunity cost.
2. **Policy portfolio benchmark** — заранее замороженная композитная экспозиция только из разрешенных рынков.
3. **Strategy economic benchmark** — сопоставимый по риску и горизонту baseline: no-trade/always-flat, passive или иное заранее утвержденное простое правило.
4. **Execution benchmark** — замороженная reference price для implementation shortfall.

Для TB-001 `always-flat/no-trade` обязателен как safety baseline. BTC buy-and-hold может быть вторичным аналитическим сравнением, но не считается risk-equivalent long/short futures benchmark.

`PM-REQ-011`: benchmark, веса, источники, cost/tax treatment, as-of rule и rebalancing convention фиксируются до начала evidence window.

`PM-REQ-012`: ретроспективная смена benchmark делает comparative evidence этого окна недействительным; старый результат не удаляется.

`PM-REQ-033`: machine-readable benchmark registry содержит ID/version/type, scope/purpose, instruments/weights, source/data hashes, costs/taxes, as-of/rebalancing/reference-price rules, freeze timestamp, evidence-window ID, benchmark hash и supersession link.

## 10. Портфельная панель риска

Численные hard caps задает только владелец в отдельной policy. Мандат требует, чтобы до реального scope были определены минимум:

- loss и drawdown caps на уровнях setup, bot, strategy family, account, venue и portfolio;
- Expected Shortfall с зафиксированными horizon/confidence/method;
- historical и hypothetical stress loss;
- gross, net и contingent exposure до разрешенного netting;
- notional, leverage, margin usage и liquidation distance;
- gap loss и risk of ruin с неопределенностью модели;
- concentration по instrument, underlying, factor, sector, currency, venue, broker, custodian, collateral, stablecoin, settlement system, data source и strategy family;
- normal/stressed correlation, drawdown concurrence и component/marginal risk contribution;
- counterparty, custody, settlement и operational failure exposure.

`PM-REQ-013`: действующие setup limits нельзя механически умножить на количество позиций и объявить портфельным лимитом.

`PM-REQ-014`: отсутствие aggregate hard cap не означает бесконечный лимит; соответствующий real-capital transition возвращает `DENY`.

## 11. Гибридная иерархия лимитов

Применяется порядок:

> owner hard cap → protection state → adaptive only-down caps → portfolio allocator → strategy/bot cap → order intent.

Лимиты представлены типизированным вектором:

`L[risk_metric, scope, horizon, unit, currency, valuation_basis]`.

`min()` применяется только среди верхних границ с одинаковым ключом и совместимыми единицами. Разнородные ограничения — loss, notional, leverage, margin, liquidation distance, liquidity, concentration и stress — применяются к intent и портфельному состоянию логическим `AND`. Missing key или невозможность однозначного преобразования единиц дают `DENY`.

`PM-REQ-015`: ни один adaptive/allocator/bot input не может увеличить hard cap.

`PM-REQ-016`: missing, stale, contradictory или uncertain input уменьшает/замораживает риск либо дает `DENY`; возврат к максимуму запрещен.

`PM-REQ-017`: если adaptive recommendation несовместима с owner-locked minimum/other policy, intent отклоняется или обнуляется; система не изменяет policy самостоятельно.

`PM-REQ-018`: восстановление после `PROTECT/EMERGENCY` требует hysteresis, cooldown, повторного evidence и предусмотренного owner gate.

`PM-REQ-034`: child reservations по positions, open/cancel-pending/conditional orders и одновременно конкурирующим intents атомарно агрегируются в parent account/venue/portfolio limits. Low net exposure не уменьшает gross/contingent checks.

До отдельного решения центральный аллокатор работает только в `SHADOW_ONLY` и не имеет write-capability к лимитам, торговым правам и переводам капитала.

## 12. Ликвидность и capacity

Capacity задается кривой по tested size tiers, а не одним числом. Для каждого tier показываются conservative/base/adverse execution scenarios.

Обязательны:

- spread и executable depth;
- participation rate;
- market impact и slippage;
- queue/partial-fill/cancel uncertainty;
- exit horizon в normal, adverse и venue-impaired состояниях;
- cost/risk неисполненного protective exit;
- margin liquidity coverage;
- агрегированный спрос всех коррелированных ботов на один liquidity pool;
- максимальный размер, при котором conservative net edge остается положительным и hard constraints соблюдены.

`PM-REQ-019`: линейная экстраполяция за пределы проверенных size tiers запрещена.

`PM-REQ-020`: low net exposure после netting не скрывает gross и contingent exposure.

`PM-REQ-035`: capacity tier связан с order-size distribution, participation, market-data sample, fill-model version/evidence level, uncertainty interval, shared liquidity pool, stress exit horizon и expiry. Положительная точечная оценка недостаточна: tier проходит только owner-approved economically meaningful hurdle и uncertainty criterion. Первый failing/untested tier и все более крупные tiers недоступны.

## 13. Книги капитала

### 13.1. Назначение книг

| Книга | Назначение | Реальные торговые полномочия сейчас |
|---|---|---|
| `RESEARCH_PAPER` | Симуляция и evidence | Нет |
| `PILOT` | Отдельный ограниченный реальный капитал | `BLOCKED` |
| `PRODUCTION` | Допущенные стратегии | `BLOCKED` |
| `OPERATIONAL_MARGIN_RESERVE` | Утвержденные операционные/маржинальные обязательства | Не является свободным капиталом стратегии |
| `PROTECTED_RESERVE` | Капитал вне полномочий ботов | Нет |
| `DISTRIBUTION_PAYABLE` | Settled/realized/reconciled cash, признанный к выплате | Не используется для покрытия торговых убытков |

`PM-REQ-021`: отсутствие явно разрешенного transfer route означает запрет.

`PM-REQ-022`: перевод между книгами не является PnL и не меняет общий NAV.

`PM-REQ-023`: unrealized, unsettled, stale, disputed, encumbered или unreconciled amount не попадает в `DISTRIBUTION_PAYABLE`.

`PM-REQ-024`: виртуальная книга не доказывает физическую изоляцию. До Pilot требуется account topology matrix: `book → venue/broker → legal account → subaccount → margin pool → bot/strategy → credential scope`.

Machine accounting profile определяет для каждой книги включение в reporting/risk/stressed NAV и TWR denominator, double-entry проводки и статус ограничения средств. `DISTRIBUTION_PAYABLE` отдельно классифицируется как internal reservation либо recognized liability; одна сумма не может одновременно учитываться как свободный капитал, резерв и payable.

## 14. Распределение прибыли

Выплата возможна только после:

1. полного PnL/NAV reconciliation;
2. settlement денежных потоков;
3. восстановления обязательных резервов;
4. выполнения owner-approved high-water mark;
5. отсутствия stale/disputed valuation и неизвестных обязательств;
6. расчета применимых налоговых/операционных резервов;
7. отдельного owner-approved transfer decision.

Distribution waterfall, payout share, frequency и suspension rules являются решением `PM-DEC-010`. До его утверждения распределяемая сумма равна нулю вне зависимости от Paper PnL.

## 15. Полномочия

| Actor | Может | Не может |
|---|---|---|
| `OWNER` | Утверждать/отзывать scope, hard caps, real stage, transfers и distribution | Отменять non-waivable safety invariants даже явным принятием риска |
| `INVESTMENT_COMMITTEE` | Собирать evidence и рекомендовать решение | Разрешать реальный капитал |
| `SECOND_LINE_REVIEWER` | Блокировать gate и фиксировать finding | Редактировать объект review или закрывать собственный finding |
| `RISK_SENTINEL` | Уменьшить лимит, заблокировать новые intents | Повысить лимит или перевести капитал |
| `PORTFOLIO_ALLOCATOR` | В shadow рекомендовать распределение | Менять hard caps или real books |
| `STRATEGY_BOT` | Предложить order intent в своем scope | Выдать себе лимит или permission |
| `OPERATOR` | Остановить, изолировать, запустить reconciliation | Расширить scope или повторно включить после owner gate |
| `RELEASE_VERIFIER` | Выдать `PASS/FAIL/BLOCKED` | Waive failed gate |

`PM-REQ-025`: только владелец может расширить финансовые полномочия. Автоматика может сохранить или сузить их.

Неотменяемые даже владельцем runtime-инварианты: unknown account/order/position state, незавершенная reconciliation, stale/malformed mandatory data, auth/secret failure, отсутствующая idempotency, policy/hash mismatch и невозможность доказать фактический exposure всегда означают `NO_NEW_RISK`. Владелец может принять остаточный business/model risk только после восстановления доказуемого состояния; принятие риска не превращает неизвестное состояние в известное.

## 16. Owner decision manifest

Разрешение владельца оформляется отдельным машиночитаемым manifest и содержит минимум:

- `manifest_id`, version, decision и monotonic sequence/nonce;
- `owner_identity_ref` без секретного значения;
- проверяемое approval evidence и trust root;
- `issued_at`, `effective_from`, `review_due_at`, `expires_at`;
- точный scope: stage, account, capital book, venue, market, instruments, strategy и bot;
- точные limits с units/currency/horizon;
- hashes governance policy, mandate, spec, acceptance, build и dataset, где применимо;
- canonicalization/hash algorithm;
- revocation reference, `revoked_at` и reason.

`PM-REQ-026`: отсутствие manifest, несовпадение любого hash/scope/stage/account/instrument, expiry, revocation либо неподтвержденная owner identity дают `DENY`.

`PM-REQ-027`: старый manifest нельзя применить к новой baseline, policy, build, dataset или расширенному scope.

Текущий `owner-decision-manifest.schema.json` является только `NON_AUTHORIZING_DRAFT`: он способен выразить исключительно `DENY` и не может войти в authority path. Полная ratified schema создается после owner decisions и semantic review. В будущем mandate ссылается на стабильный `manifest_id`, а manifest содержит hash mandate payload; circular content hashes запрещены. Проверка signature/trust root, monotonic sequence, bounded TTL и revocation обязательна вне JSON Schema.

## 17. Стадии и переходы

Допустимы автоматические переходы только в равное или более ограничительное состояние. Повышение стадии требует всех gates и нового owner manifest.

| Переход | Автоматически | Owner decision | Текущий статус |
|---|---:|---:|---|
| `RESEARCH → REPLAY` | После research gates | Нет | Возможен |
| `REPLAY → DRY_RUN` | После acceptance | Нет | Возможен в Phase 1 |
| `DRY_RUN → PAPER` | После acceptance/evidence freeze | Требуется по активному work item | Цель первого среза |
| `PAPER → PILOT_LIMITED_LIVE` | Никогда | Обязательно | `BLOCKED` |
| `PILOT → PRODUCTION_LIVE` | Никогда | Обязательно | `BLOCKED` |
| Любая стадия → более ограничительная | По protection policy | Для аварийного снижения не требуется | Разрешено |
| `PROTECT/EMERGENCY → восстановление` | Никогда немедленно | По утвержденному gate | `BLOCKED` до review |

Expiry, manifest mismatch, revocation, policy conflict, unknown account state или emergency переводят scope в `BLOCKED/NO_NEW_RISK`.

До `PAPER → PILOT_LIMITED_LIVE` обязательны четыре отдельные owner-locked ссылки: `entry_order_policy`, `protective_exit_policy`, `profit_taking_policy`, `emergency_liquidation_or_hedge_policy`. Они определяют trigger source, native/synthetic stop, reduce-only, stop-limit no-fill, gap, price protection, partial fill, cancel/fill race, halt, residual-exposure timeout, fallback и reconciliation. Неизвестная или неподдерживаемая venue capability дает `DENY`.

Каждый scope также ссылается по hash на отдельный versioned `venue_capability_profile`: official-document date/API version, sessions/timezone/clocks, auctions/halts/maintenance/clearing, order types/TIF/conditional/reduce-only, tick/lot/price bands, settlement/margin/borrow, corporate actions/expiry/roll, funding/mark/index, rate limits и degraded states. Профили MOEX и 24/7 crypto не взаимозаменяемы.

## 18. Evidence и запрет metric gaming

До окна оценки фиксируются:

- objective hierarchy;
- formulas и полный metric panel;
- NAV perimeter и valuation time;
- data/FX sources и stale rules;
- benchmarks и weights;
- cost/fill assumptions;
- risk horizons;
- evidence window и stopping rule;
- minimum economically meaningful result;
- multiple-testing budget и experiment registry.

Запрещено:

- выбирать лучшие dates/regimes/bots/fills/FX conversion/software baseline после результата;
- скрывать failed experiments или excluded periods;
- считать raw setups независимой выборкой при clustering/overlap;
- выдавать FX или deposit effect за strategy alpha;
- скрывать gross leverage netting-ом;
- использовать optimistic fill model как единственное основание допуска;
- повышать риск по recent PnL;
- объединять несовместимые baselines в непрерывный track record.

`PM-REQ-028`: полный experiment registry, versions, exclusions и negative results сохраняются.

`PM-REQ-029`: positive result содержит uncertainty и поправку на selection/multiple testing.

`PM-REQ-030`: evidence имеет expiry/review date и downgrade rules; expired evidence не разрешает capital increase или promotion.

`PM-REQ-036`: experiment evidence содержит заранее определенные family/test budget, unique experiment IDs включая failures, sealed cutoff/access log, setup-cluster rule, raw/cluster/effective sample, uncertainty estimator и multiple-testing correction. Missing/post-hoc method дает `BLOCKED`.

`PM-REQ-037`: каждый evidence item имеет собственные scope, dataset/build/model/benchmark hashes, observation cutoff, issue/review/expiry timestamps, drift metrics/thresholds, invalidation events, downgrade action и reviewer verdict. Evidence expiry не наследуется от срока mandate или manifest.

`PM-REQ-038`: FX valuation profile задает source hierarchy, bid/mid/ask convention для каждого NAV, as-of/calendar, stale/conflict thresholds, fallback, depeg/liquidity haircuts, cross-rate construction, rounding и missing-market behavior. До утверждения consolidated NAV остается `INDICATIVE` и недоступным для comparative admission/distribution.

## 19. Reporting contract

Каждый портфельный отчет содержит:

- mandate/policy/build/dataset identifiers и hashes;
- reporting period и valuation timestamps;
- reporting/risk/stressed NAV;
- external cash flows, TWR и MWR/XIRR;
- full PnL bridge и attribution residual;
- benchmark results и uncertainty;
- drawdown/recovery/ES/stress/risk-of-ruin panel;
- gross/net/contingent exposures и concentrations;
- liquidity/capacity и exit horizon;
- stale/disputed/unreconciled percentage;
- incidents, unknown orders, reconciliation duration и ledger gaps;
- capital-book balances и transfers;
- действующий protection state;
- unresolved findings, evidence expiry и next review date.

Пустое обязательное поле является отсутствующим evidence, а не нулем.

## 20. Управление изменениями

Каждое изменение создает новую версию, diff, decision ID и audit event. In-place mutation нормативного artifact запрещена.

Изменение цели, scope, hard cap, benchmark, NAV perimeter, authority, transfer route, stage semantics или distribution waterfall является финансово значимым и требует owner review. При неопределенности выбирается более высокий impact class.

Удаление requirement ID запрещено. Устаревшее требование получает `SUPERSEDED_BY` и остается в истории.

## 21. Известные конфликты и ограничения

| ID | Severity | Ограничение | Безопасный статус |
|---|---|---|---|
| `PM-RISK-001` | BLOCKER | Target MOEX/дополнительные горизонты шире active Phase 1 | `FUTURE/BLOCKED` |
| `PM-RISK-002` | BLOCKER | Нет owner-approved aggregate portfolio hard caps | Pilot/Production `BLOCKED` |
| `PM-RISK-003` | HIGH | Cross margin создает account-level contagion | Не заявлять физическую изоляцию; Pilot `BLOCKED` |
| `PM-RISK-004` | BLOCKER | Не определены protective/emergency order policies | Pilot `BLOCKED` |
| `PM-RISK-005` | BLOCKER | Нет owner manifest trust/verification model | Real scope `BLOCKED` |
| `PM-RISK-006` | HIGH | Не утверждены benchmark/valuation/waterfall | Comparative admission/distribution `BLOCKED` |
| `PM-RISK-007` | HIGH | TB-001 acceptance еще не покрывает все portfolio accounting/capacity gates | Paper bot result не считается полным portfolio evidence |

## 22. Решения владельца

### 22.0. Принятые решения

| ID | Решение | Эффект |
|---|---|---|
| `PM-DEC-001` | Вариант 3: `TARGET + нормативный overlay Development/Research/Replay/DRY_RUN/Paper` | Обязателен для некапитального lifecycle; real orders/Pilot/Production остаются `DENY/BLOCKED` |
| `PM-DEC-002` | Вариант 3: versioned record для некапитальных решений; cryptographic signature + independent second confirmation для real-capital actions | Level A не дает real authority; Level B `DENY` до `PM-DEC-007` и verifier |
| `PM-DEC-003 v2` | Вариант 3: отдельные evidence-calibrated профили `площадка × риск` внутри owner hard bounds | Метод и fail-closed lookup приняты; численные bounds/effective values не утверждены, поэтому Level B остается `DENY` |

### 22.1. Блокируют ратификацию active machine mandate

| ID | Решение | Fail-closed default |
|---|---|---|
| Численный профиль `PM-DEC-003` | Численные review/TTL/single-use/revocation-freshness/clock-skew значения для принятой differentiated validity model | Мандат не разрешает real scope |
| `PM-DEC-004` | Точный NAV perimeter | Consolidated NAV `INDICATIVE` |
| `PM-DEC-005` | Численные aggregate hard caps и резервы | Pilot/Production `BLOCKED` |
| `PM-DEC-006` | Финальная authority matrix и delegation boundaries | Расширение полномочий только вручную владельцем |
| `PM-DEC-007` | Canonicalization/hash/signature/manifest verification | Любой manifest `DENY` |
| `PM-DEC-008` | Fail-closed semantics всех stages/scopes | Самый ограничительный статус |
| `PM-DEC-009` | Binding benchmark hierarchy и comparative-admission rules | Admission по excess return `BLOCKED` |
| `PM-DEC-010` | Distribution waterfall, HWM, reserves, taxes, payout cap/frequency/suspension/clawback и source/destination books | Distributions `BLOCKED`, payable amount zero |
| `PM-DEC-011` | Accounting profile и residual tolerance | Финансовое evidence не допускает promotion |
| `PM-DEC-012` | TWR/MWR/XIRR methodology profile | Показатели маркируются `UNRATIFIED` |
| `PM-DEC-013` | FX/stablecoin valuation profile | Consolidated NAV `INDICATIVE` |
| `PM-DEC-014` | Experiment/effective-sample/multiple-testing policy | Comparative strategy admission `BLOCKED` |
| `PM-DEC-015` | Capacity economically meaningful hurdle и uncertainty criterion | Real size tier отсутствует |

### 22.2. Допускается отложить при сохранении scope BLOCKED/FUTURE/SHADOW_ONLY

- MOEX universe, boards/regimes и instruments — до MOEX ТЗ;
- account/subaccount/margin/credential topology — до Pilot;
- protective/profit/emergency execution — до Pilot;
- adaptive formulas, windows, floors, hysteresis/cooldown — до write-enabled allocator;
- allocation corridors четырех горизонтов — до реального капитала;
- FX sources, stale thresholds и haircuts — до консолидированной финансово значимой отчетности;
- Paper/Strategy Evidence numeric thresholds — до `Paper → Pilot`;
- protection-state numeric thresholds и action matrix — до Pilot;
- legal/tax/broker/custody/settlement perimeter — до соответствующего real venue;
- intent conflict/netting/hedging policy — до одновременной активации ботов на одном underlying.

## 23. Acceptance contract

Машиночитаемые критерии находятся в `acceptance.toml`. Каждый `PM-AC-*` связан с требованиями и рисками. Для текущей редакции прохождение document gates означает только готовность продолжать проектирование; оно не означает разрешение Pilot/live.

## 24. Явные предположения

- `PM-ASM-001`: документ действует как нормативный overlay только для Development/Research/Replay/DRY_RUN/Paper; реальное разрешение из этого не следует.
- `PM-ASM-002`: Phase 1 ограничен DRY_RUN/Paper и не требует real order submission.
- `PM-ASM-003`: RUB — валюта консолидации, а не обязательная валюта хранения.
- `PM-ASM-004`: существующие численные значения Phase 1 сохраняются без изменения только в собственном scope.
- `PM-ASM-005`: шесть книг пока являются нормативной моделью; physical topology не доказана.
- `PM-ASM-006`: юридическая, налоговая и регуляторная применимость будет проверена отдельно до реального капитала.

## 25. Не-цели этой главы

Глава не:

- выбирает конкретные торговые сигналы;
- обещает прибыль или доходность;
- утверждает численные aggregate limits;
- разрешает MOEX, новый символ, счет или credential;
- определяет все детали execution и fill model;
- разрешает перевод либо вывод средств;
- включает live trading.
