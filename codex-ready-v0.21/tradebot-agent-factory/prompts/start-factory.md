# Команда запуска фабрики

Передайте корневому Codex-агенту:

```text
Разработай work item TB-001 из specs/bitget-btc-telegram-v1.
Строго выполни multi-agent workflow из AGENTS.md и factory/pipeline.toml.
Сначала запусти requirements_analyst и quant_researcher параллельно, дождись обоих и сведи противоречия. Не начинай код, пока capital-impacting решения не закрыты.
Затем пройди архитектуру, спецификацию, реализацию, adversarial tests и три независимых review. После исправлений вызови release_verifier.
Live trading не включать, реальные credentials не запрашивать и не использовать.
Финальный ответ должен содержать release decision, AC traceability, точные команды и результаты, unresolved risks и следующий безопасный шаг.
```

Для новой задачи сначала скопируйте `specs/templates/bot-spec.md` в отдельную папку work item и замените идентификатор в команде.

