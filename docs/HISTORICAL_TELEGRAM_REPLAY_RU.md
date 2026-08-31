# Historical Telegram Replay — Slice 02

Slice 02 читает только локальные JSON-файлы, созданные Telegram Desktop, и
прогоняет один или оба configured channels через существующий offline
pipeline. В коде нет Telegram login, Telethon, HTTP, Bitget или биржевых
заявок.

## Подготовка экспорта

В Telegram Desktop вручную откройте нужный канал, выберите
`Export chat history` и формат `Machine-readable JSON`. Для полного экспорта
используется `Settings → Advanced → Export Telegram Data`.

Приватные данные храните только в локальном каталоге:

```bash
mkdir -p private/telegram_exports
chmod 700 private private/telegram_exports
```

Каталог исключён из Git. Не переносите реальные exports или channel IDs в
`tests/fixtures/`.

Telegram Desktop записывает файл `result.json`. Поддерживаются:

- single-chat root с `name`, `type`, `id`, `messages`;
- full-export root с выбранным chat в `chats.list`.

Контракт сверяется с официальным serializer Telegram Desktop:
<https://github.com/telegramdesktop/tdesktop/blob/dev/Telegram/SourceFiles/export/output/export_output_json.cpp>.

Для полного export с несколькими чатами передайте bare numeric ID через
`--chat-id`. Это именно значение `id` из JSON; импортёр не преобразует его в
Bot API-форму `-100…`.

Для двух configured sources `--chat-id` не нужен: импортёр выбирает оба
channel ID из config и объединяет их сообщения в один глобально
отсортированный batch.

## Локальная test-only конфигурация

Сделайте приватную копию demo-config и укажите bare IDs двух каналов:

```bash
cp config/mvp-historical-demo.toml \
  private/telegram_exports/mvp-historical-local.toml
```

Файл всё равно обязан оставаться `TEST_FIXTURE_ONLY` и
`OFFLINE_SIMULATION`. Не меняйте risk, leverage или allocation в рамках
Slice 02.

## Запуск

```bash
source .venv/bin/activate
python3 -m tradebot_mvp.telegram_import \
  --input private/telegram_exports/result.json \
  --source scalping \
  --config private/telegram_exports/mvp-historical-local.toml \
  --db private/telegram_exports/historical.sqlite3
```

Для full export:

```bash
python3 -m tradebot_mvp.telegram_import \
  --input private/telegram_exports/result.json \
  --source intraday \
  --chat-id 2000000002 \
  --config private/telegram_exports/mvp-historical-local.toml \
  --db private/telegram_exports/historical.sqlite3
```

Для одного full export с обоими configured channels:

```bash
python3 -m tradebot_mvp.telegram_import \
  --input private/telegram_exports/full/result.json \
  --source scalping \
  --source intraday \
  --config private/telegram_exports/mvp-historical-local.toml \
  --db private/telegram_exports/historical.sqlite3
```

Для двух отдельных per-chat exports аргументы сопоставляются по позиции:

```bash
python3 -m tradebot_mvp.telegram_import \
  --input private/telegram_exports/scalping/result.json \
  --input private/telegram_exports/intraday/result.json \
  --source scalping \
  --source intraday \
  --config private/telegram_exports/mvp-historical-local.toml \
  --db private/telegram_exports/historical.sqlite3
```

Вывод — один детерминированный JSON summary. Он содержит SHA-256 channel
pseudonym, но не raw channel ID и не тексты сообщений.

## Порядок и revisions

- обычное сообщение: `revision=0`, event time равен message time;
- текущая edited-версия: `revision=edited_unixtime`, event time равен edit
  time;
- tie-breaker: source, SHA-256 channel pseudonym, message ID, revision и
  normalized payload hash;
- точный повтор не создаёт новых строк;
- изменение text/time/reply при той же revision даёт
  `TELEGRAM_REVISION_CONFLICT`.

Original time, edit time, reply message ID и SHA-256 pseudonym reply peer
сохраняются в companion SQLite table. Raw channel/peer ID и message text в
этой таблице отсутствуют.

SQLite хранит глобальный event-time watermark. Уже известные
duplicates/conflicts можно проверять повторно, но новый event обязан иметь
sort key строго позже watermark. Поэтому несколько exports для одной базы
нужно подавать хронологическими batch-ами; overlapping histories двух
configured channels передаются вместе одним вызовом. Поздний импорт
неизвестного backfill завершается `TELEGRAM_EVENT_TIME_REGRESSION` без новых
строк.

Service records, пустые media captions и `rich_message` без обычного `text`
валидируются, не передаются в signal pipeline и учитываются в
`skipped_messages`. Их доступные ID/time/edit/reply metadata сохраняются в
отдельной pseudonymous SQLite table; из rich content сигнал не угадывается.
Официальная запись `type="unsupported"` без времени сохраняет ID и marker
`revision=UNAVAILABLE`, но importer не придумывает ей timestamp.

Для historical replay используйте новую либо ранее созданную только этим
importer базу. Если в SQLite уже есть legacy Slice 01 events без historical
provenance, запуск завершится
`TELEGRAM_DATABASE_PROVENANCE_MISMATCH`, не меняя решения.

## Что экспорт не доказывает

Обычный Telegram Desktop export содержит текущее видимое состояние сообщения
и, при наличии, время последнего edit. Он не содержит:

- предыдущие варианты текста;
- полную последовательность edits;
- события удаления уже отсутствующих сообщений.

Импортёр не создаёт эти события по догадке. Синтетические fixtures могут
проверять детерминированную обработку наблюдаемых revisions, но не считаются
восстановленной историей Telegram.

## Обезличенная демонстрация

```bash
demo_dir="$(mktemp -d)"
python3 -m tradebot_mvp.telegram_import \
  --input tests/fixtures/telegram_desktop_result.json \
  --source scalping \
  --config config/mvp-historical-demo.toml \
  --db "$demo_dir/historical.sqlite3"
```

Fixture использует только придуманные имена, IDs, timestamps и тексты.
