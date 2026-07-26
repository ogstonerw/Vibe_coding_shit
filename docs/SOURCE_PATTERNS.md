# Публичные исходные паттерны

Это не копия случайного набора «персон агентов». Каркас собирает проверяемые подходы из официальных публичных репозиториев крупных разработчиков:

- [OpenAI Agents SDK — AGENTS.md](https://github.com/openai/openai-agents-python/blob/main/AGENTS.md): репозиторные правила, обязательные команды и узкие ссылки на инструкции.
- [OpenAI Agents SDK — PLANS.md](https://github.com/openai/openai-agents-python/blob/main/PLANS.md): outcome-based acceptance, точные команды, безопасные retries/rollback и self-contained планы.
- [GitHub Spec Kit](https://github.com/github/spec-kit): цепочка specification → plan → tasks и ТЗ как источник истины.
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework): production-oriented agents и multi-agent workflows. Старый AutoGen не выбран как новая основа, поскольку его официальный репозиторий переведен в maintenance mode.
- [Anthropic Claude Code Security Review](https://github.com/anthropics/claude-code-security-review): независимый diff-based security review с фокусом на high-confidence findings.
- [LangGraph](https://github.com/langchain-ai/langgraph): durable execution и human-in-the-loop как ориентир для длинных workflow.

Публично нельзя подтвердить, что внутренние prompt-файлы крупных компаний дословно совпадают с этими репозиториями. Здесь используются официально опубликованные проекты и инженерные паттерны, а не заявление о доступе к закрытым внутренним процессам.

