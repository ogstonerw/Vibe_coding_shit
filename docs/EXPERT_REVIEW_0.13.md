# Реестр независимого экспертного аудита концепции

Дата аудита: 17.07.2026  
Объект: концепция до корректировок версии 0.13  
Текущая редакция с disposition: 0.14  
Статус: `PASS FOR CONTINUED DESIGN / BLOCKED FOR PILOT AND PRODUCTION`

## 1. Состав независимой проверки

Три read-only reviewer-а работали параллельно в отдельных контекстах и не редактировали объект проверки:

1. `institutional_portfolio_reviewer` — функция CIO/CRO;
2. `quant_methodology_reviewer` — независимая количественная валидация и model risk;
3. `market_microstructure_reviewer` — electronic trading, venue mechanics и execution risk.

Это были ограниченные review-сессии. После выдачи заключения они завершились и освободили слоты; сами роли и обязательные review gates добавлены в конфигурацию фабрики.

## 2. Итоговые вердикты

| Эксперт | Вердикт | Смысл |
|---|---|---|
| Institutional CIO/CRO | `BLOCKED` | Нельзя переходить к реальному капиталу до устранения конфликтов мандата, формализации лимитов, книг капитала и owner authorization |
| Quant methodology/model risk | `BLOCKED` | Paper duration и количество setups не доказывают экономическую состоятельность без отдельного Strategy Evidence Gate |
| Market microstructure/execution | `PASS WITH REQUIRED CHANGES` для проектирования; `BLOCKED` для капитала | Архитектуру можно уточнять, но Pilot невозможен без решения по защитному исполнению, margin topology и доказательности fill-модели |

Ни один эксперт не выдал безусловный `PASS`. Это ожидаемое безопасное поведение второй линии, а не сбой фабрики.

## 3. Findings и disposition

| ID | Severity | Finding | Disposition в 0.14 |
|---|---|---|---|
| CIO-01 | BLOCKER | Целевая концепция MOEX/мультигоризонт/аллокатор конфликтовала с узкой действующей Bitget/BTCUSDT policy | Добавлено разделение `Target mandate` и `Phase-1 active policy`; более узкое ограничение всегда имеет приоритет |
| CIO-02 | BLOCKER | Не была определена иерархия жестких и адаптивных лимитов | Установлено `hard cap → protection → adaptive cap → allocator → bot → intent`; адаптивный контур может только снижать лимит |
| CIO-03 | BLOCKER | Решение владельца существовало как неформальная фраза | Добавлен обязательный owner decision manifest, связанный с hashes, scope, expiry и revocation |
| CIO-04 | BLOCKER | Три крупные корзины смешивали экономически несовместимые состояния капитала | Определены шесть книг капитала и обязательная account topology matrix |
| CIO-05 | HIGH | Независимость ИИ-комитета была декларативной | Зафиксированы fresh contexts, первичные evidence, сохранение dissent и запрет reviewer-у закрывать собственные findings |
| QMR-01 | BLOCKER | Операционные Paper-критерии могли заменить доказательство экономической гипотезы | Добавлены отдельный Strategy Evidence Gate и `MR-01…MR-12` |
| QMR-02 | BLOCKER | Просмотренные Paper-события могли повторно считаться holdout | Просмотренное становится research data; после `C2/C3` требуется новое unseen forward-window |
| QMR-03 | BLOCKER | Emergency/hotfix смешивал срочность и влияние | Emergency сделан ортогональным urgency-флагом с обязательным impact `C0–C3` |
| QMR-04 | HIGH | PnL и издержки могли учитываться дважды | Добавлены PnL bridge, NAV identity, attribution residual и запрет двойного учета spread/slippage |
| QMR-05 | HIGH | FX и depeg смешивались | Установлена цепочка `USDT/USD × USD/RUB` с раздельным stablecoin basis и FX attribution |
| QMR-06 | HIGH | Не хватало point-in-time lineage и контроля multiple testing | Добавлены immutable data manifests, experiment registry, test budget, sealed holdout и effective sample |
| MM-01 | BLOCKER | `limit_only` не определяет безопасный stop/emergency exit | Политики entry/protective/profit/emergency разделены; конкретное решение владельца остается открытым до Pilot |
| MM-02 | BLOCKER | Виртуальные книги не изолируют cross-margin contagion | Явно требуется physical account/margin topology; виртуальная атрибуция не считается изоляцией |
| MM-03 | BLOCKER | Paper fills могли быть оптимистичными, включая `touch = fill` | Введены conservative/base/adverse сценарии и уровни evidence `E0…E3` |
| MM-04 | BLOCKER | Не был определен authoritative order lifecycle при потерянном ACK | Добавлены authoritative ledger, `SUBMISSION_UNKNOWN`, запрет blind retry и reconciliation |
| MM-05 | HIGH | Kill switch и конфликтующие горизонты были описаны слишком общо | Разделены действия kill switch и добавлен central execution book |
| MM-06 | HIGH | Не была зафиксирована специфика MOEX и 24/7 crypto | Добавлены отдельные требования к venue lifecycle, reference data, клирингу, settlement, funding и clock model |

## 4. Нерешенные блокировки владельца

Исправления концепции не означают разрешение капитала. До Pilot остаются открыты как минимум:

- численные hard caps и формулы только-снижающих adaptive limits;
- protective/emergency order policy;
- физическая account/margin/credential topology;
- подписываемый owner decision manifest;
- distribution waterfall и правила резервов;
- предварительно зарегистрированные Paper/Strategy Evidence thresholds;
- реальные E3 execution evidence, которые могут появиться только на отдельной будущей Pilot-стадии.

Действующая численная risk policy не изменялась, live trading остается выключенным.

## 5. Постоянный review gate

- Релевантный эксперт вызывается во время разработки каждой главы.
- Все три эксперта обязательны перед фиксацией главы, новым ТЗ бота, новой площадкой/счетом/стадией и финансово значимой реализацией.
- Каждый повторный review выполняется в новом изолированном контексте против точной версии и первичных evidence.
- `BLOCKER/HIGH` не закрывается автором и требует исправления плюс нового независимого прогона.
- Release verifier остается последним gate и не может отменить проваленный экспертный вывод.
