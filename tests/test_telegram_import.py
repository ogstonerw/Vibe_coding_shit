from __future__ import annotations

import contextlib
import copy
import hashlib
import inspect
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tradebot_mvp import telegram_import
from tradebot_mvp.config import load_config
from tradebot_mvp.contracts import Source
from tradebot_mvp.journal import Journal
from tradebot_mvp.parser import EVENT_FIELDS
from tradebot_mvp.service import OfflineSignalService
from tradebot_mvp.telegram_import import (
    HistoricalJournal,
    TelegramImportError,
    load_telegram_export,
    main,
    parse_telegram_export,
    render_internal_jsonl,
    run_historical_replay_with_config,
    run_historical_replays_with_config,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "telegram_desktop_result.json"
CONFIG = ROOT / "config" / "mvp-historical-demo.toml"


class TelegramDesktopFormatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.export = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_single_chat_shape_text_and_event_time_order(self) -> None:
        batch = load_telegram_export(FIXTURE, source=Source.SCALPING)

        self.assertEqual("single_chat", batch.input_shape)
        self.assertEqual(4, batch.input_messages)
        self.assertEqual(1, batch.skipped_messages)
        self.assertEqual([101, 103, 102], [record.message_id for record in batch.records])
        self.assertEqual(
            "BTCUSDT SHORT\nENTRY 94700\nSTOP 95500",
            batch.records[1].text,
        )

        edited = batch.records[2]
        self.assertEqual(1_784_981_100, edited.revision)
        self.assertEqual("2026-07-25T12:01:00Z", edited.message_timestamp)
        self.assertEqual("2026-07-25T12:05:00Z", edited.edited_timestamp)
        self.assertEqual("2026-07-25T12:05:00Z", edited.event_timestamp)
        self.assertEqual(101, edited.reply_to_message_id)
        self.assertEqual("channel2000000001", edited.reply_to_peer_id)

        envelopes = [
            json.loads(line) for line in render_internal_jsonl(batch).splitlines()
        ]
        self.assertEqual(3, len(envelopes))
        self.assertTrue(all(set(envelope) == EVENT_FIELDS for envelope in envelopes))
        self.assertEqual([101, 103, 102], [envelope["message_id"] for envelope in envelopes])

    def test_full_export_requires_deterministic_chat_selection(self) -> None:
        other = copy.deepcopy(self.export)
        other["id"] = 2_000_000_002
        other["name"] = "ANONYMIZED OTHER CHANNEL"
        other["messages"] = []
        full_export = {
            "about": "Telegram Desktop",
            "chats": {
                "about": "Exported chats",
                "list": [other, copy.deepcopy(self.export)],
            },
        }

        with self.assertRaisesRegex(
            TelegramImportError,
            "TELEGRAM_CHAT_SELECTION_REQUIRED",
        ):
            parse_telegram_export(full_export, source=Source.SCALPING)

        batch = parse_telegram_export(
            full_export,
            source=Source.SCALPING,
            chat_id="2000000001",
        )
        self.assertEqual("full_export", batch.input_shape)
        self.assertEqual("2000000001", batch.chat_id)
        self.assertEqual([101, 103, 102], [record.message_id for record in batch.records])

    def test_edited_snapshot_does_not_invent_original_revision(self) -> None:
        export = copy.deepcopy(self.export)
        export["messages"] = [export["messages"][0]]

        batch = parse_telegram_export(export, source=Source.SCALPING)

        self.assertEqual(1, len(batch.records))
        self.assertNotEqual(0, batch.records[0].revision)
        self.assertEqual(
            batch.records[0].edited_timestamp,
            batch.records[0].event_timestamp,
        )

    def test_conflicting_revision_is_rejected_during_preflight(self) -> None:
        export = copy.deepcopy(self.export)
        conflict = copy.deepcopy(export["messages"][0])
        conflict["text"] = "DIFFERENT CURRENT TEXT"
        export["messages"].append(conflict)

        with self.assertRaisesRegex(
            TelegramImportError,
            "TELEGRAM_REVISION_CONFLICT",
        ):
            parse_telegram_export(export, source=Source.SCALPING)

    def test_unknown_message_type_and_malformed_edit_pair_are_rejected(self) -> None:
        unknown = copy.deepcopy(self.export)
        unknown["messages"][0]["type"] = "future_unknown_type"
        malformed_edit = copy.deepcopy(self.export)
        del malformed_edit["messages"][0]["edited_unixtime"]

        for export, reason in (
            (unknown, "TELEGRAM_MESSAGE_TYPE_UNSUPPORTED"),
            (malformed_edit, "TELEGRAM_EDIT_TIME_INVALID"),
        ):
            with (
                self.subTest(reason=reason),
                self.assertRaisesRegex(TelegramImportError, reason),
            ):
                parse_telegram_export(export, source=Source.SCALPING)

    def test_malformed_shared_fields_and_text_are_rejected(self) -> None:
        malformed_fragment = copy.deepcopy(self.export)
        malformed_fragment["messages"][2]["text"][1]["text"] = 123
        edit_before_message = copy.deepcopy(self.export)
        edit_before_message["messages"][0]["edited_unixtime"] = "1784980859"
        malformed_service = copy.deepcopy(self.export)
        del malformed_service["messages"][1]["date_unixtime"]

        for export, reason in (
            (malformed_fragment, "TELEGRAM_MESSAGE_TEXT_INVALID"),
            (edit_before_message, "TELEGRAM_EDIT_TIME_INVALID"),
            (malformed_service, "TELEGRAM_MESSAGE_TIME_INVALID"),
        ):
            with (
                self.subTest(reason=reason),
                self.assertRaisesRegex(TelegramImportError, reason),
            ):
                parse_telegram_export(export, source=Source.SCALPING)

    def test_rich_message_is_explicitly_skipped(self) -> None:
        export = copy.deepcopy(self.export)
        rich_message = export["messages"][0]
        del rich_message["text"]
        del rich_message["text_entities"]
        rich_message["rich_message"] = {
            "blocks": [],
            "title": "ANONYMIZED RICH CONTENT",
        }
        export["messages"] = [rich_message]

        batch = parse_telegram_export(export, source=Source.SCALPING)

        self.assertEqual(0, len(batch.records))
        self.assertEqual(1, batch.skipped_messages)
        skipped = batch.skipped_records[0]
        self.assertEqual(102, skipped.message_id)
        self.assertEqual(1_784_981_100, skipped.revision)
        self.assertEqual("2026-07-25T12:01:00Z", skipped.message_timestamp)
        self.assertEqual("2026-07-25T12:05:00Z", skipped.edited_timestamp)
        self.assertEqual(101, skipped.reply_to_message_id)
        self.assertEqual("channel2000000001", skipped.reply_to_peer_id)
        self.assertEqual("TELEGRAM_RICH_MESSAGE", skipped.skip_reason)

    def test_official_unsupported_shape_is_skipped_without_invented_time(self) -> None:
        export = copy.deepcopy(self.export)
        export["messages"] = [{"id": 105, "type": "unsupported"}]

        batch = parse_telegram_export(export, source=Source.SCALPING)

        self.assertEqual(0, len(batch.records))
        self.assertEqual(1, batch.skipped_messages)
        skipped = batch.skipped_records[0]
        self.assertEqual(105, skipped.message_id)
        self.assertIsNone(skipped.revision)
        self.assertIsNone(skipped.message_timestamp)
        self.assertIsNone(skipped.event_timestamp)
        self.assertIsNone(skipped.sort_key)

    def test_exact_duplicate_inside_export_is_collapsed(self) -> None:
        export = copy.deepcopy(self.export)
        message = export["messages"][3]
        export["messages"] = [message, copy.deepcopy(message)]

        batch = parse_telegram_export(export, source=Source.SCALPING)

        self.assertEqual(1, len(batch.records))
        self.assertEqual(1, batch.exact_export_duplicates)


class HistoricalReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config(CONFIG)
        cls.export = json.loads(FIXTURE.read_text(encoding="utf-8"))

    @staticmethod
    def _write_export(directory: Path, data: object, name: str = "result.json") -> Path:
        path = directory / name
        path.write_text(
            json.dumps(data, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def _assert_controlled_error(
        self,
        input_path: Path,
        db_path: Path,
        reason: str,
        *,
        chat_id: str | None = None,
    ) -> None:
        arguments = [
            "--input",
            str(input_path),
            "--source",
            "scalping",
            "--config",
            str(CONFIG),
            "--db",
            str(db_path),
        ]
        if chat_id is not None:
            arguments.extend(("--chat-id", chat_id))
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            status = main(arguments)

        self.assertEqual(2, status)
        self.assertEqual(
            {"reason": reason, "status": "ERROR"},
            json.loads(stdout.getvalue()),
        )
        self.assertEqual("", stderr.getvalue())
        self.assertFalse(db_path.exists())

    def test_replay_reuses_pipeline_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "history.sqlite3"
            first = run_historical_replay_with_config(
                FIXTURE,
                self.config,
                db_path,
                source=Source.SCALPING,
            )
            second = run_historical_replay_with_config(
                FIXTURE,
                self.config,
                db_path,
                source=Source.SCALPING,
            )
            fresh = run_historical_replay_with_config(
                FIXTURE,
                self.config,
                Path(directory) / "fresh.sqlite3",
                source=Source.SCALPING,
            )

            self.assertEqual(
                {
                    "accepted": 2,
                    "conflicts": 0,
                    "duplicates": 0,
                    "imported_messages": 3,
                    "imported_skipped_messages": 1,
                    "intents": 2,
                    "rejected": 1,
                    "selected_messages": 3,
                    "setups": 2,
                    "skipped_messages": 1,
                },
                {
                    key: first[key]
                    for key in (
                        "accepted",
                        "conflicts",
                        "duplicates",
                        "imported_messages",
                        "imported_skipped_messages",
                        "intents",
                        "rejected",
                        "selected_messages",
                        "setups",
                        "skipped_messages",
                    )
                },
            )
            self.assertEqual(0, second["accepted"])
            self.assertEqual(0, second["rejected"])
            self.assertEqual(3, second["duplicates"])
            self.assertEqual(3, second["imported_messages"])
            self.assertEqual(1, second["imported_skipped_messages"])
            self.assertEqual(1, second["skipped_duplicates"])
            self.assertEqual(2, second["setups"])
            self.assertEqual(2, second["intents"])
            self.assertEqual(first, fresh)

            with sqlite3.connect(db_path) as connection:
                metadata = connection.execute(
                    """
                    SELECT message_timestamp, edited_timestamp, event_timestamp,
                           event_epoch, reply_to_message_id, reply_to_peer_key
                    FROM telegram_import_events
                    WHERE message_id = '102'
                    """
                ).fetchone()
                columns = {
                    row[1]
                    for row in connection.execute(
                        "PRAGMA table_info(telegram_import_events)"
                    ).fetchall()
                }
                persisted_values = "\n".join(
                    str(value)
                    for table in (
                        "metadata",
                        "events",
                        "setups",
                        "intents",
                        "journal_events",
                        "telegram_import_events",
                        "telegram_import_skipped",
                        "telegram_import_state",
                    )
                    for row in connection.execute(f"SELECT * FROM {table}").fetchall()
                    for value in row
                )
            self.assertEqual(
                (
                    "2026-07-25T12:01:00Z",
                    "2026-07-25T12:05:00Z",
                    "2026-07-25T12:05:00Z",
                    1_784_981_100,
                    "101",
                    hashlib.sha256(b"channel2000000001").hexdigest(),
                ),
                metadata,
            )
            self.assertNotIn("channel_id", columns)
            self.assertNotIn("text", columns)
            raw_markers = (
                "2000000001",
                "BTCUSDT LONG\nENTRY 94700\nSTOP 92900",
                "ANONYMIZED NON-SIGNAL UPDATE",
                "ANONYMIZED TEST CHANNEL",
            )
            rendered_summary = json.dumps(first, ensure_ascii=False, sort_keys=True)
            for marker in raw_markers:
                self.assertNotIn(marker, persisted_values)
                self.assertNotIn(marker, rendered_summary)
            for suffix in ("", "-wal", "-shm"):
                candidate = Path(str(db_path) + suffix)
                if candidate.exists():
                    self.assertEqual(0, candidate.stat().st_mode & 0o077)
                    database_bytes = candidate.read_bytes()
                    for marker in raw_markers:
                        self.assertNotIn(marker.encode(), database_bytes)

    def test_skipped_rich_metadata_round_trips_without_pipeline_decision(self) -> None:
        rich_export = copy.deepcopy(self.export)
        rich_message = rich_export["messages"][0]
        del rich_message["text"]
        del rich_message["text_entities"]
        rich_message["rich_message"] = {
            "blocks": [],
            "title": "ANONYMIZED RICH CONTENT",
        }
        rich_export["messages"] = [rich_message]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = self._write_export(root, rich_export)
            db_path = root / "history.sqlite3"

            first = run_historical_replay_with_config(
                input_path,
                self.config,
                db_path,
                source=Source.SCALPING,
            )
            second = run_historical_replay_with_config(
                input_path,
                self.config,
                db_path,
                source=Source.SCALPING,
            )

            self.assertEqual(0, first["selected_messages"])
            self.assertEqual(1, first["skipped_messages"])
            self.assertEqual(0, first["imported_messages"])
            self.assertEqual(1, first["imported_skipped_messages"])
            self.assertEqual(0, first["setups"])
            self.assertEqual(0, first["intents"])
            self.assertEqual(1, second["skipped_duplicates"])
            self.assertEqual(1, second["imported_skipped_messages"])

            with sqlite3.connect(db_path) as connection:
                metadata = connection.execute(
                    """
                    SELECT message_id, revision, message_timestamp,
                           edited_timestamp, event_timestamp,
                           reply_to_message_id, reply_to_peer_key, skip_reason
                    FROM telegram_import_skipped
                    """
                ).fetchone()
            self.assertEqual(
                (
                    "102",
                    "1784981100",
                    "2026-07-25T12:01:00Z",
                    "2026-07-25T12:05:00Z",
                    "2026-07-25T12:05:00Z",
                    "101",
                    hashlib.sha256(b"channel2000000001").hexdigest(),
                    "TELEGRAM_RICH_MESSAGE",
                ),
                metadata,
            )

            conflicting = copy.deepcopy(rich_export)
            conflicting["messages"][0]["reply_to_message_id"] = 99
            conflict_path = self._write_export(root, conflicting, "conflict.json")
            with self.assertRaisesRegex(
                TelegramImportError,
                "TELEGRAM_REVISION_CONFLICT",
            ):
                run_historical_replay_with_config(
                    conflict_path,
                    self.config,
                    db_path,
                    source=Source.SCALPING,
                )
            with sqlite3.connect(db_path) as connection:
                skipped_count = connection.execute(
                    "SELECT COUNT(*) FROM telegram_import_skipped"
                ).fetchone()[0]
            self.assertEqual(1, skipped_count)

    def test_two_configured_channels_share_one_global_sorted_batch(self) -> None:
        intraday = copy.deepcopy(self.export)
        intraday["id"] = 2_000_000_002
        intraday["name"] = "ANONYMIZED INTRADAY CHANNEL"
        intraday_message = intraday["messages"][3]
        intraday_message["id"] = 201
        intraday_message["date"] = "2026-07-25T12:03:00"
        intraday_message["date_unixtime"] = "1784980980"
        intraday_message["from_id"] = "channel2000000002"
        intraday["messages"] = [intraday_message]
        full_export = {
            "about": "Telegram Desktop",
            "chats": {
                "about": "Exported chats",
                "list": [intraday, copy.deepcopy(self.export)],
            },
        }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = self._write_export(root, full_export)
            db_path = root / "history.sqlite3"

            first = run_historical_replays_with_config(
                (input_path,),
                self.config,
                db_path,
                sources=(Source.SCALPING, Source.INTRADAY),
            )
            second = run_historical_replays_with_config(
                (input_path,),
                self.config,
                db_path,
                sources=(Source.SCALPING, Source.INTRADAY),
            )

            self.assertEqual(3, first["accepted"])
            self.assertEqual(1, first["rejected"])
            self.assertEqual(4, first["selected_messages"])
            self.assertEqual(1, first["skipped_messages"])
            self.assertEqual(3, first["setups"])
            self.assertEqual(3, first["intents"])
            self.assertEqual(
                {"intraday": "full_export", "scalping": "full_export"},
                first["input_shapes"],
            )
            self.assertEqual(4, second["duplicates"])
            self.assertEqual(1, second["skipped_duplicates"])
            self.assertEqual(3, second["setups"])
            self.assertEqual(3, second["intents"])

            with sqlite3.connect(db_path) as connection:
                decision_sources = [
                    row[0]
                    for row in connection.execute(
                        "SELECT source FROM journal_events ORDER BY sequence"
                    ).fetchall()
                ]
            self.assertEqual(
                ["scalping", "scalping", "intraday", "scalping"],
                decision_sources,
            )

            scalping_path = self._write_export(
                root,
                copy.deepcopy(self.export),
                "scalping.json",
            )
            intraday_path = self._write_export(root, intraday, "intraday.json")
            aligned = run_historical_replays_with_config(
                (scalping_path, intraday_path),
                self.config,
                root / "aligned.sqlite3",
                sources=(Source.SCALPING, Source.INTRADAY),
            )
            self.assertEqual(3, aligned["accepted"])
            self.assertEqual(first["outcomes"], aligned["outcomes"])
            self.assertEqual(
                {"intraday": "single_chat", "scalping": "single_chat"},
                aligned["input_shapes"],
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                status = main(
                    [
                        "--input",
                        str(input_path),
                        "--source",
                        "scalping",
                        "--source",
                        "intraday",
                        "--config",
                        str(CONFIG),
                        "--db",
                        str(root / "cli.sqlite3"),
                    ]
                )
            self.assertEqual(0, status)
            self.assertEqual("", stderr.getvalue())
            self.assertEqual(3, json.loads(stdout.getvalue())["accepted"])

    def test_metadata_or_text_change_under_same_revision_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db_path = root / "history.sqlite3"
            run_historical_replay_with_config(
                FIXTURE,
                self.config,
                db_path,
                source=Source.SCALPING,
            )
            changed = copy.deepcopy(self.export)
            changed["messages"][0]["reply_to_message_id"] = 99
            changed_path = self._write_export(root, changed)

            summary = run_historical_replay_with_config(
                changed_path,
                self.config,
                db_path,
                source=Source.SCALPING,
            )

            self.assertEqual(1, summary["conflicts"])
            self.assertEqual(2, summary["duplicates"])
            self.assertEqual(3, summary["imported_messages"])
            self.assertEqual(2, summary["setups"])
            self.assertEqual(2, summary["intents"])

    def test_later_edit_timestamp_is_a_new_observed_revision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db_path = root / "history.sqlite3"
            run_historical_replay_with_config(
                FIXTURE,
                self.config,
                db_path,
                source=Source.SCALPING,
            )
            later = copy.deepcopy(self.export)
            later["messages"][0]["edited"] = "2026-07-25T12:06:00"
            later["messages"][0]["edited_unixtime"] = "1784981160"
            later_path = self._write_export(root, later)

            summary = run_historical_replay_with_config(
                later_path,
                self.config,
                db_path,
                source=Source.SCALPING,
            )

            self.assertEqual(1, summary["rejected"])
            self.assertEqual(2, summary["duplicates"])
            self.assertEqual(4, summary["imported_messages"])
            with sqlite3.connect(db_path) as connection:
                revisions = connection.execute(
                    """
                    SELECT revision
                    FROM telegram_import_events
                    WHERE message_id = '102'
                    ORDER BY revision
                    """
                ).fetchall()
            self.assertEqual([("1784981100",), ("1784981160",)], revisions)

    def test_global_watermark_rejects_unseen_backfill(self) -> None:
        for source, channel_id in (
            (Source.SCALPING, 2_000_000_001),
            (Source.INTRADAY, 2_000_000_002),
        ):
            with self.subTest(source=source), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                db_path = root / "history.sqlite3"
                later = copy.deepcopy(self.export)
                later["messages"] = [later["messages"][0]]
                later_path = self._write_export(root, later, "later.json")
                run_historical_replay_with_config(
                    later_path,
                    self.config,
                    db_path,
                    source=Source.SCALPING,
                )

                earlier = copy.deepcopy(self.export)
                earlier["id"] = channel_id
                earlier["messages"] = [earlier["messages"][3]]
                earlier_path = self._write_export(root, earlier, "earlier.json")
                with self.assertRaisesRegex(
                    TelegramImportError,
                    "TELEGRAM_EVENT_TIME_REGRESSION",
                ):
                    run_historical_replay_with_config(
                        earlier_path,
                        self.config,
                        db_path,
                        source=source,
                    )

                with sqlite3.connect(db_path) as connection:
                    counts = (
                        connection.execute("SELECT COUNT(*) FROM events").fetchone()[0],
                        connection.execute(
                            "SELECT COUNT(*) FROM telegram_import_events"
                        ).fetchone()[0],
                        connection.execute(
                            "SELECT COUNT(*) FROM telegram_import_state"
                        ).fetchone()[0],
                    )
                self.assertEqual((1, 1, 1), counts)

    def test_legacy_core_database_without_import_provenance_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "legacy.sqlite3"
            with Journal(db_path, self.config.fingerprint) as journal:
                outcome = OfflineSignalService(self.config, journal).process_mapping(
                    {
                        "channel_id": "2000000001",
                        "message_id": 999,
                        "revision": 0,
                        "source": "scalping",
                        "text": "BTCUSDT LONG\nENTRY 94700\nSTOP 92900",
                        "timestamp": "2026-07-25T11:00:00Z",
                    }
                )
            self.assertEqual("accepted", outcome.disposition)

            with self.assertRaisesRegex(
                TelegramImportError,
                "TELEGRAM_DATABASE_PROVENANCE_MISMATCH",
            ):
                run_historical_replay_with_config(
                    FIXTURE,
                    self.config,
                    db_path,
                    source=Source.SCALPING,
                )

            with sqlite3.connect(db_path) as connection:
                counts = (
                    connection.execute("SELECT COUNT(*) FROM events").fetchone()[0],
                    connection.execute("SELECT COUNT(*) FROM setups").fetchone()[0],
                    connection.execute(
                        "SELECT COUNT(*) FROM telegram_import_events"
                    ).fetchone()[0],
                    connection.execute(
                        "SELECT COUNT(*) FROM telegram_import_skipped"
                    ).fetchone()[0],
                )
            self.assertEqual((1, 1, 0, 0), counts)

            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                status = main(
                    [
                        "--input",
                        str(FIXTURE),
                        "--source",
                        "scalping",
                        "--config",
                        str(CONFIG),
                        "--db",
                        str(db_path),
                    ]
                )
            self.assertEqual(2, status)
            self.assertEqual(
                {
                    "reason": "TELEGRAM_DATABASE_PROVENANCE_MISMATCH",
                    "status": "ERROR",
                },
                json.loads(stdout.getvalue()),
            )
            self.assertEqual("", stderr.getvalue())

    def test_injected_write_failure_rolls_back_entire_batch(self) -> None:
        original = HistoricalJournal.insert_import_record
        calls = 0

        def fail_second(journal: HistoricalJournal, record: object) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise sqlite3.OperationalError("injected")
            original(journal, record)  # type: ignore[arg-type]

        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "history.sqlite3"
            with (
                mock.patch.object(
                    HistoricalJournal,
                    "insert_import_record",
                    new=fail_second,
                ),
                self.assertRaisesRegex(sqlite3.OperationalError, "injected"),
            ):
                run_historical_replay_with_config(
                    FIXTURE,
                    self.config,
                    db_path,
                    source=Source.SCALPING,
                )

            with sqlite3.connect(db_path) as connection:
                counts = [
                    connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    for table in (
                        "events",
                        "setups",
                        "intents",
                        "journal_events",
                        "telegram_import_events",
                        "telegram_import_skipped",
                        "telegram_import_state",
                    )
                ]
            self.assertEqual([0, 0, 0, 0, 0, 0, 0], counts)

    def test_skipped_metadata_failure_rolls_back_pipeline_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "history.sqlite3"
            with (
                mock.patch.object(
                    HistoricalJournal,
                    "insert_skipped_record",
                    side_effect=sqlite3.OperationalError("injected skipped"),
                ),
                self.assertRaisesRegex(
                    sqlite3.OperationalError,
                    "injected skipped",
                ),
            ):
                run_historical_replay_with_config(
                    FIXTURE,
                    self.config,
                    db_path,
                    source=Source.SCALPING,
                )

            with sqlite3.connect(db_path) as connection:
                counts = [
                    connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    for table in (
                        "events",
                        "setups",
                        "intents",
                        "journal_events",
                        "telegram_import_events",
                        "telegram_import_skipped",
                        "telegram_import_state",
                    )
                ]
            self.assertEqual([0, 0, 0, 0, 0, 0, 0], counts)

    def test_invalid_export_returns_controlled_error_before_database_open(self) -> None:
        cases = (
            ("result.html", "<!doctype html><html></html>", "TELEGRAM_EXPORT_INVALID_JSON"),
            ("result.json", '{"unexpected":true}', "TELEGRAM_EXPORT_SCHEMA_UNSUPPORTED"),
            (
                "result.json",
                '{"name":"x","name":"y","type":"public_channel","id":1,"messages":[]}',
                "TELEGRAM_EXPORT_INVALID_JSON",
            ),
            (
                "result.json",
                (
                    '{"name":"x","type":"public_channel","id":2000000001,'
                    '"messages":[],"extra":NaN}'
                ),
                "TELEGRAM_EXPORT_INVALID_JSON",
            ),
            (
                "result.json",
                (
                    '{"name":"x","type":"public_channel","id":2000000001,'
                    '"messages":[],"extra":1e999}'
                ),
                "TELEGRAM_EXPORT_INVALID_JSON",
            ),
            (
                "result.json",
                (
                    '{"name":"x","type":"public_channel","id":'
                    + ("9" * 5_000)
                    + ',"messages":[]}'
                ),
                "TELEGRAM_EXPORT_INVALID_JSON",
            ),
            (
                "result.json",
                (
                    '{"name":"x","type":"public_channel","id":2000000001,'
                    '"messages":[{"id":1,"type":"message","date":"x",'
                    '"date_unixtime":"'
                    + ("9" * 5_000)
                    + '","text":"x"}]}'
                ),
                "TELEGRAM_MESSAGE_TIME_INVALID",
            ),
        )
        for name, content, reason in cases:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                input_path = root / name
                input_path.write_text(content, encoding="utf-8")
                db_path = root / "must-not-exist.sqlite3"
                self._assert_controlled_error(input_path, db_path, reason)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._assert_controlled_error(
                FIXTURE,
                root / "must-not-exist.sqlite3",
                "TELEGRAM_CHAT_ID_INVALID",
                chat_id="9" * 5_000,
            )

    def test_invalid_utf8_symlink_and_size_limit_are_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            invalid_utf8 = root / "invalid.json"
            invalid_utf8.write_bytes(b"\xff")
            symlink = root / "symlink.json"
            symlink.symlink_to(FIXTURE)
            directory_input = root / "directory.json"
            directory_input.mkdir()

            self._assert_controlled_error(
                invalid_utf8,
                root / "invalid.sqlite3",
                "TELEGRAM_EXPORT_INVALID_JSON",
            )
            self._assert_controlled_error(
                symlink,
                root / "symlink.sqlite3",
                "TELEGRAM_EXPORT_LIMIT_EXCEEDED",
            )
            self._assert_controlled_error(
                directory_input,
                root / "directory.sqlite3",
                "TELEGRAM_EXPORT_LIMIT_EXCEEDED",
            )
            with (
                mock.patch.object(telegram_import, "MAX_EXPORT_BYTES", 16),
            ):
                self._assert_controlled_error(
                    FIXTURE,
                    root / "oversize.sqlite3",
                    "TELEGRAM_EXPORT_LIMIT_EXCEEDED",
                )
            with (
                mock.patch.object(telegram_import, "MAX_EXPORT_MESSAGES", 3),
                self.assertRaisesRegex(
                    TelegramImportError,
                    "TELEGRAM_EXPORT_LIMIT_EXCEEDED",
                ),
            ):
                load_telegram_export(FIXTURE, source=Source.SCALPING)

    def test_invalid_multi_source_arguments_are_controlled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "must-not-exist.sqlite3"
            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                status = main(
                    [
                        "--input",
                        str(FIXTURE),
                        "--source",
                        "scalping",
                        "--source",
                        "scalping",
                        "--config",
                        str(CONFIG),
                        "--db",
                        str(db_path),
                    ]
                )

            self.assertEqual(2, status)
            self.assertEqual(
                {
                    "reason": "TELEGRAM_IMPORT_ARGUMENTS_INVALID",
                    "status": "ERROR",
                },
                json.loads(stdout.getvalue()),
            )
            self.assertEqual("", stderr.getvalue())
            self.assertFalse(db_path.exists())

    def test_all_multi_source_inputs_preflight_before_database_open(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            malformed = root / "intraday.json"
            malformed.write_text("<html></html>", encoding="utf-8")
            db_path = root / "must-not-exist.sqlite3"

            with self.assertRaisesRegex(
                TelegramImportError,
                "TELEGRAM_EXPORT_INVALID_JSON",
            ):
                run_historical_replays_with_config(
                    (FIXTURE, malformed),
                    self.config,
                    db_path,
                    sources=(Source.SCALPING, Source.INTRADAY),
                )
            self.assertFalse(db_path.exists())

    def test_same_export_conflict_precedes_database_open(self) -> None:
        conflict = copy.deepcopy(self.export)
        changed = copy.deepcopy(conflict["messages"][0])
        changed["text"] = "CONFLICTING TEXT"
        conflict["messages"].append(changed)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = self._write_export(root, conflict)
            db_path = root / "must-not-exist.sqlite3"
            with self.assertRaisesRegex(
                TelegramImportError,
                "TELEGRAM_REVISION_CONFLICT",
            ):
                run_historical_replay_with_config(
                    input_path,
                    self.config,
                    db_path,
                    source=Source.SCALPING,
                )
            self.assertFalse(db_path.exists())

    def test_source_channel_mismatch_precedes_database_open(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "must-not-exist.sqlite3"
            with self.assertRaisesRegex(
                TelegramImportError,
                "TELEGRAM_SOURCE_CHANNEL_NOT_ALLOWED",
            ):
                run_historical_replay_with_config(
                    FIXTURE,
                    self.config,
                    db_path,
                    source=Source.INTRADAY,
                )
            self.assertFalse(db_path.exists())

    def test_import_module_has_no_network_or_exchange_path(self) -> None:
        source = inspect.getsource(
            __import__(
                "tradebot_mvp.telegram_import",
                fromlist=["telegram_import"],
            )
        ).lower()
        for forbidden in ("telethon", "httpx", "requests", "socket", "bitget"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
