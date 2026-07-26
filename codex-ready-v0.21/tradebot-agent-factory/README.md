# TradeBot Agent Factory

Готовый каркас мультиагентной команды, которая превращает идею торгового бота в проверяемое ТЗ, код, тесты и подготовленный к ревью релиз.

Система рассчитана на Codex и GitHub. Она также содержит совместимые инструкции для Cursor и GitHub Copilot. Главная особенность — агенты не договариваются о качестве «на словах»: требования, риск-политика, приемочные критерии и результаты проверок хранятся в репозитории и проверяются автоматически.

## Что уже настроено

- 12 ролей: девять ролей разработки и контроля плюс независимые institutional CIO/CRO, quant model-risk и market-microstructure reviewers;
- последовательность `ТЗ → глубокий экспертный аудит → план → реализация → тесты → независимые ревью → повторный аудит evidence → релизный вердикт`;
- ограничение до 4 параллельных агентов и запрет рекурсивного размножения ролей;
- отдельные машиночитаемые политики риска и согласований;
- self-check без внешних Python-зависимостей;
- фиксированный safety eval-набор для сравнения prompt/model без самообмана;
- GitHub Actions, шаблоны issue/PR и инструкция по branch protection;
- базовое ТЗ для вашего Bitget/Telegram-бота в `specs/bitget-btc-telegram-v1/`;
- live trading выключен и не может считаться готовым без отдельного ручного шлюза.

## Быстрый старт

```bash
python3 scripts/install_codex_config.py
python3 scripts/self_check.py
python3 -m unittest discover -s tests -v
```

## Первый работающий MVP

Offline Slice 01 уже выполняет путь
`Telegram-like JSONL → parser → first-leg risk → simulated LIMIT intent →
SQLite journal`. Реальные Telegram/Bitget API и биржевые ордера отсутствуют.

```bash
MVP_DB="$(mktemp -d)/state.sqlite3"
python3 -m tradebot_mvp replay \
  --input tests/fixtures/mvp_signals.jsonl \
  --config config/mvp-offline-demo.toml \
  --db "$MVP_DB"
```

Повтор той же команды с тем же `MVP_DB` возвращает duplicates и не создаёт
новые setup или intents. Test channel IDs и денежные параметры в demo-config
являются только fixtures.

Установщик копирует проверенную конфигурацию из `config/codex/` в проектную `.codex/`. Затем откройте репозиторий в Codex и дайте команду из [`prompts/start-factory.md`](prompts/start-factory.md). Проект нужно пометить доверенным, иначе локальная конфигурация и роли не загрузятся.

## Где что лежит

| Путь | Назначение |
|---|---|
| `AGENTS.md` | Общие правила всей команды и определение готовности |
| `config/codex/` | Версионируемый источник настроек и ролей Codex |
| `governance/` | Неизменяемые агентами правила риска и согласований |
| `specs/` | ТЗ, планы, задачи и приемочные контракты |
| `specs/portfolio-mandate-v1/` | Глава 1: инвестиционный мандат, machine contract, acceptance и независимый review |
| `contracts/` | Формат передачи результата между агентами |
| `evals/` | Проверочные сценарии для ролей и model-routing |
| `docs/TRADING_BOTS_CONCEPT.md` | Живая верхнеуровневая концепция экосистемы торговых ботов |
| `scripts/self_check.py` | Локальная проверка целостности фабрики |
| `.github/` | CI, issue/PR-процесс и настройка GitHub |

## Важная граница

Фабрика автономно разрабатывает и проверяет код, но не получает права самостоятельно включать торговлю реальными средствами. Переход `DRY_RUN → paper trading → limited live → live` требует подтверждения владельца на каждом финансово значимом этапе.

Подробности: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/OPERATING_MODEL.md`](docs/OPERATING_MODEL.md), [`docs/GITHUB_SETUP.md`](docs/GITHUB_SETUP.md).
