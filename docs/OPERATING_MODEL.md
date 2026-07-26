# Ролевая и операционная модель

| Роль | Основной результат | Может писать | Не может |
|---|---|---:|---|
| Requirements analyst | Однозначные сценарии и открытые решения | Нет | Проектировать по догадке |
| Quant researcher | Валидный research/backtest protocol | Нет | Обещать доходность |
| System architect | Контракты, состояния, failure model | Нет | Включать live |
| Implementer | Код и focused tests по одной задаче | Да | Менять governance |
| Test engineer | Adversarial/replay tests | Только тесты и seams | Маскировать дефект тестом |
| Code reviewer | Дефекты корректности и регрессии | Нет | Исправлять собственные замечания |
| Security reviewer | High-confidence security findings | Нет | Читать/показывать secrets |
| Risk reviewer | Проверка capital-safety invariants | Нет | Оценивать прибыльность |
| Release verifier | PASS/FAIL/BLOCKED с доказательствами | Нет | Waive failed gate |
| Institutional portfolio reviewer | Независимый аудит мандата, капитала и aggregate/stress risk | Нет | Менять лимиты или разрешать капитал |
| Quant methodology reviewer | Независимая валидация evidence и model risk | Нет | Создавать/подгонять проверяемую стратегию |
| Market microstructure reviewer | Независимый аудит исполнения, venue mechanics и margin topology | Нет | Авторизовать live или писать execution model |

## Эффективность

- Параллельно идут только независимые read-heavy задачи: discovery, стандартные review и три глубоких экспертных аудита.
- Один writer устраняет merge-конфликты и снижает рассинхронизацию.
- `gpt-5.6` используется для сложной разработки и критических review; `gpt-5.6-terra` — для более дешевого сбора релизных доказательств.
- Каждый handoff содержит только факты, допущения, findings, evidence, решения и next action; сырые логи не загрязняют главный контекст.
- Повторное review запускается только по затронутым областям, но risk review обязателен при любом изменении execution/risk.
- Релевантные глубокие эксперты проверяют главы по мере разработки; все три обязательны перед фиксацией главы, новым ТЗ/рынком/счетом и финансовым stage transition.
- Конкретная сессия эксперта завершается после заключения и освобождает слот; постоянными являются роль, инструкция, review gate и журнал findings.
- Глубокий reviewer работает в fresh isolated context, читает первичные evidence до резюме автора, не редактирует объект review и не закрывает собственные findings.

## Режимы работы

| Стадия | Биржевой side effect | Условие перехода |
|---|---:|---|
| Development | Нет | Unit/integration checks |
| DRY_RUN | Нет, блок до сети | Все AC для dry-run |
| Paper | Только симуляция | Утвержденный период и пороги |
| Limited live | Ограниченный | Отдельное подтверждение владельца |
| Live | Разрешенный политикой | Повторное подтверждение владельца |
