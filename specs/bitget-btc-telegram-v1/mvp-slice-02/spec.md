# TB-001 MVP Slice 02 — Historical Telegram Replay

Status: IMPLEMENTATION_SCOPE
Parent work item: `TB-001`
Target stage: `OFFLINE_SIMULATION`
Input source: local Telegram Desktop JSON export only

## 1. Outcome

Slice 02 imports bounded local `result.json` data produced by Telegram
Desktop, normalizes messages from one or both configured channels into the
exact six-field Slice 01 envelope, and replays them through the unchanged:

`parser → sizing → simulated LIMIT intent → SQLite journal`

The result is deterministic, local and auditable. It does not connect to
Telegram or Bitget and does not introduce order, fill, paper or live behavior.

## 2. In scope

- single-chat Telegram Desktop JSON exports;
- full Telegram Desktop JSON exports with chats under `chats.list`;
- one explicitly selected channel or both fixed configured channels per run;
- one shared full export or two source-aligned per-chat exports;
- exact assignment to `scalping` or `intraday`;
- ordered reconstruction of string and formatted-fragment `text`;
- message ID, original time, last edit time and reply relationship;
- current edited snapshot as one observed revision;
- deterministic event-time replay within and across invocations, idempotency
  and revision conflicts;
- existing Slice 01 rejection, sizing, intent and journal behavior.

## 3. Out of scope

- HTML exports;
- Telegram API, Telethon login and network access;
- reconstruction of unavailable edit history or deleted messages;
- importing service actions or media-only messages as signal events;
- arbitrary-source or more-than-two-file merge architecture;
- reply-target recovery when the target is absent from the export;
- market-data timeline, fills, fees, funding or slippage;
- paper/live trading, exchange submission or Bitget credentials;
- changes to symbols, risk, leverage, channels or financial limits;
- universal multi-market or multi-export architecture.

## 4. Actual input format

The format is grounded in Telegram Desktop's official JSON serializer,
`Telegram/SourceFiles/export/output/export_output_json.cpp`, inspected on
2026-07-26.

The single-chat root is:

```json
{
  "name": "Channel",
  "type": "public_channel",
  "id": 2000000001,
  "messages": []
}
```

The full-export root stores the same chat object under:

```json
{
  "chats": {
    "list": []
  }
}
```

A supported message has numeric `id`, `type="message"`, display `date`,
decimal-string `date_unixtime`, `text`, and optionally the paired fields
`edited`/`edited_unixtime`, `reply_to_message_id` and `reply_to_peer_id`.
`text` may be a string or an ordered array containing strings and entity
objects with a string `text` field.

The official serializer may also emit `{id,type="unsupported"}` without any
time field. It is retained as timeless skipped metadata. Valid `service`,
blank/media-only and `rich_message` records retain every available
ID/time/edit/reply field but do not become signal envelopes.

The exported chat ID is Telegram Desktop's bare numeric peer ID. The importer
does not guess or convert it to a Bot API `-100…` identifier. Its decimal text
must exactly match the configured channel for the selected source.

Input must be a regular non-symlink UTF-8 file no larger than 64 MiB. One
selected chat may contain at most 100,000 messages. Duplicate JSON keys,
non-finite JSON constants, oversized numeric tokens, invalid UTF-8, unsafe
paths, excessive inputs and unsupported roots fail before SQLite is opened.

## 5. Normalization contract

Every replayable message maps to the unchanged Slice 01 envelope:

```json
{
  "source": "scalping",
  "channel_id": "2000000001",
  "message_id": 101,
  "revision": 0,
  "timestamp": "2026-07-25T12:00:00Z",
  "text": "BTCUSDT LONG\nENTRY 94700\nSTOP 92900"
}
```

`date_unixtime` and `edited_unixtime` are authoritative event instants and
are canonicalized to UTC `YYYY-MM-DDTHH:MM:SSZ`.

- An unedited message gets `revision=0` and event time equal to message time.
- An edited message gets `revision=int(edited_unixtime)` and event time equal
  to edit time.
- The final edited text is never replayed at the original message time.
- The original time, optional edit time, reply message ID and optional reply
  peer ID are retained in the companion import table.
- A missing reply target remains an unresolved ID; no target is invented.

Known `service` and `unsupported` records, media-only/blank text messages,
and the serializer's `rich_message` branch without ordinary `text` are
validated, stored in a metadata-only companion table, skipped from the signal
pipeline and counted. Rich content is not guessed into a signal. Unknown
message types and malformed message records reject the whole export.

## 6. Behavioral scenarios

1. A shuffled single-chat fixture is normalized and replayed in event-time
   order.
2. Messages sharing one event second are ordered by source, pseudonymous
   channel key, message ID, revision and normalized import hash.
3. Ordered Telegram text fragments produce the same text as their visual
   concatenation.
4. A second identical run against the same database returns only duplicates
   and creates no setup, intent or import row.
5. The same source/channel/message/revision with changed text, original/edit
   time or reply metadata returns `TELEGRAM_REVISION_CONFLICT`.
6. A later observed `edited_unixtime` is a distinct revision and traverses
   the existing Slice 01 pipeline.
7. An unseen backfill older than the database's global watermark is rejected
   before pipeline decisions, including across the two configured sources.
8. Two configured channel histories from one full export or two aligned
   per-chat exports are merged and replayed in one global order.
9. A rich/media/service record round-trips available metadata while creating
   no setup or intent; the official timeless unsupported shape stays
   timeless.
10. A core database with legacy events lacking historical provenance is
   rejected before new decisions.
11. Invalid JSON, duplicate keys, unsupported roots/types, oversized numeric
   values and malformed time fields return one controlled JSON error with
   exit status 2 and no traceback.
12. An injected write failure rolls back all event, setup, intent, journal,
   import and watermark rows from the batch.

## 7. Risk and execution rules

Slice 02 does not calculate new financial values. It passes normalized
envelopes to the frozen Slice 01 implementation and therefore retains:

- `OFFLINE_SIMULATION`;
- `TEST_FIXTURE_ONLY` configuration;
- BTCUSDT-only strict grammar;
- fixed `15% / 85%` allocations;
- first risk leg `1.5%`;
- leverage range `10..25`;
- maximum five journal-local active setups;
- one simulated LIMIT intent for an accepted revision.

A newer observed edit revision may produce a new simulated decision. Slice 02
does not infer cancellation, fill, position or setup-closing semantics.

## 8. Ordering and conflict identity

Records are fully normalized before database access and sorted by:

```text
(event_epoch, source, channel_key, message_id, revision, import_payload_hash)
```

`channel_key` is the SHA-256 channel pseudonym. One run imports one source or
both fixed configured sources, and the complete key provides a strict, stable
order without persisting the raw channel ID. The import hash covers the exact
Slice 01 envelope plus original time, edit time and reply metadata.

The importer preflights either one selected source or the two fixed configured
sources, then merges all replayable records before database access. The
companion state stores one global high-watermark for the database.
Previously known identities remain eligible for duplicate/conflict checks.
Every unseen record must sort strictly after the watermark or the complete
invocation fails with `TELEGRAM_EVENT_TIME_REGRESSION` and no new rows.
Callers must therefore supply incremental batches chronologically and must
submit overlapping histories for the two configured channels together.

Import identity is:

```text
(source, pseudonymous_channel_key, message_id, revision)
```

An identical hash is an exact repeat. A different hash under the same
identity is a conflict and creates no rows.

## 9. Atomic persistence

The companion STRICT table stores:

- source and SHA-256 channel pseudonym;
- message ID and revision;
- original, optional edit and effective event timestamps plus event epoch;
- optional reply message ID and SHA-256 reply-peer pseudonym;
- normalized import hash and fixed format marker.

It never stores the raw channel ID or message text. It has a foreign key to
the existing `events` row. A separate singleton state row stores the same
pseudonymous deterministic key components for the global watermark.

A second STRICT metadata-only table stores the same available identifiers,
times and reply fields for skipped records plus a reason and normalized
payload hash. Timeless official `unsupported` records use the explicit
`UNAVAILABLE` revision marker and NULL times. They never receive a synthetic
signal envelope.

The importer preflights every selected input before opening SQLite.
During replay one outer `BEGIN IMMEDIATE` transaction contains all existing
per-event service transactions as savepoints. Any raised write error rolls
back the complete batch.

Before the first historical decision, every pre-existing core event must have
matching historical import provenance and a consistent watermark. A legacy
JSONL-only database fails closed with
`TELEGRAM_DATABASE_PROVENANCE_MISMATCH`; a fresh historical database is the
normal migration boundary.

## 10. Privacy and fixture policy

Real exports and local configs belong under `private/telegram_exports/`,
which is excluded from Git. Repository fixtures use invented IDs, names,
texts and timestamps and are explicitly labeled anonymized test data.

Default CLI output contains only the SHA-256 channel pseudonym and the
existing pseudonymous event references, never raw channel ID or text.

## 11. Acceptance criteria

The machine-readable contract is `acceptance.toml`. Evidence consists of:

- focused Slice 02 unit and integration tests;
- full repository unittest;
- self-check and compileall;
- Ruff limited to new/changed Python files;
- a deterministic local replay of the anonymized fixture.

## 12. Open decisions

- More than the two fixed configured sources is deferred.
- General source discovery and arbitrary multi-file merge are deferred.
- Import of `left_chats` is deferred.
- A future lifecycle slice must decide how edited/deleted signal revisions
  supersede prior journal-local setups.
- Market-data event-time alignment remains a later roadmap step.

Telegram Desktop's ordinary export contains only the current visible message
and optional last-edit timestamp. It does not provide prior text versions or
deletion events. Slice 02 never presents synthetic edit/delete fixtures as
recovered Telegram history.
