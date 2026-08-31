from __future__ import annotations

import dataclasses
import json
import os
import sqlite3
import stat
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

from tradebot_mvp.config import ConfigError, config_from_mapping, load_config
from tradebot_mvp.contracts import RawMessage, Side, Source
from tradebot_mvp.journal import ConfigFingerprintMismatch, Journal
from tradebot_mvp.parser import EnvelopeError, SignalError, parse_envelope, parse_signal
from tradebot_mvp.replay import render_summary, run_replay, run_replay_with_config
from tradebot_mvp.service import OfflineSignalService
from tradebot_mvp.sizing import SizingError, size_first_leg


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "mvp-offline-demo.toml"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "mvp_signals.jsonl"


def event(
    message_id: int = 1,
    *,
    source: str = "scalping",
    channel_id: str | None = None,
    text: str = "BTCUSDT LONG\nENTRY 94700.0\nSTOP 92900.0\nRISK 0.5%",
) -> dict[str, object]:
    if channel_id is None:
        channel_id = "-1000000000001" if source == "scalping" else "-1000000000002"
    return {
        "source": source,
        "channel_id": channel_id,
        "message_id": message_id,
        "revision": 0,
        "timestamp": "2026-07-24T12:00:00Z",
        "text": text,
    }


class ConfigAndParserTests(unittest.TestCase):
    def test_config_is_closed_policy_bound_and_fingerprinted(self) -> None:
        config = load_config(CONFIG_PATH)
        self.assertEqual("OFFLINE_SIMULATION", config.mode)
        self.assertEqual(64, len(config.fingerprint))
        data = {
            "config_version": "x",
            "classification": "TEST_FIXTURE_ONLY",
            "mode": "OFFLINE_SIMULATION",
            "account_equity": "10000",
            "leverage": 10,
            "quantity_step": "0.001",
            "price_tick": "0.1",
            "adverse_cost_per_unit": "0",
            "scalping_allocation": "0.15",
            "intraday_allocation": "0.85",
            "scalping_channel_id": "-1000000000001",
            "intraday_channel_id": "-1000000000002",
            "first_leg_risk": "0.015",
            "max_active_setups": 5,
        }
        self.assertEqual(config_from_mapping(data), config_from_mapping(dict(reversed(list(data.items())))))
        for field, invalid in (
            ("leverage", 9),
            ("max_active_setups", 6),
            ("first_leg_risk", "0.03"),
            ("account_equity", "1e4"),
        ):
            mutated = dict(data)
            mutated[field] = invalid
            with self.subTest(field=field), self.assertRaises(ConfigError):
                config_from_mapping(mutated)
        mutated = dict(data)
        mutated["unknown"] = "x"
        with self.assertRaises(ConfigError):
            config_from_mapping(mutated)

    def test_closed_envelope_and_strict_timestamp(self) -> None:
        parsed = parse_envelope(event())
        self.assertEqual(Source.SCALPING, parsed.source)
        for mutation in (
            {"source": "unknown"},
            {"message_id": True},
            {"timestamp": "2026-02-30T12:00:00Z"},
            {"extra": "x"},
        ):
            candidate = event()
            candidate.update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(EnvelopeError):
                parse_envelope(candidate)

    def test_ru_en_grammar_and_risk_text_do_not_change_signal(self) -> None:
        english = parse_signal("BTCUSDT LONG\nENTRY 94700.0\nSTOP 92900.0\nRISK 0.5%")
        russian = parse_signal("BTC ЛОНГ\nВХОД 94700.0\nСТОП 92900.0\nРИСК 1/3")
        noisy = parse_signal("BTCUSDT LONG\nENTRY 94700.0\nSTOP 92900.0\nRISK 1%")
        self.assertEqual(english, russian)
        self.assertEqual(english, noisy)

    def test_parser_rejects_non_btc_ambiguous_stop_and_geometry(self) -> None:
        cases = {
            "SYMBOL_NOT_ALLOWED": "ETHUSDT LONG\nENTRY 100\nSTOP 90",
            "STOP_PROFILE_UNRESOLVED": "BTCUSDT LONG\nENTRY 94700\nСТОП ПОД 93050",
            "INVALID_LONG_STOP_GEOMETRY": "BTCUSDT LONG\nENTRY 94700\nSTOP 95000",
            "INVALID_SHORT_STOP_GEOMETRY": "BTCUSDT SHORT\nENTRY 94700\nSTOP 94000",
            "DUPLICATE_SIGNAL_FIELD": "BTCUSDT LONG\nENTRY 94700\nENTRY 94600\nSTOP 93000",
            "UNSUPPORTED_SIGNAL_GRAMMAR": "#BTC LONG\nENTRY 94700\nSTOP 93000",
        }
        for reason, text in cases.items():
            with self.subTest(reason=reason), self.assertRaisesRegex(SignalError, reason):
                parse_signal(text)


class SizingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config(CONFIG_PATH)

    def test_both_buckets_and_side_geometry_are_capped(self) -> None:
        cases = (
            (Source.SCALPING, parse_signal("BTCUSDT LONG\nENTRY 94700.0\nSTOP 92900.0")),
            (Source.INTRADAY, parse_signal("BTCUSDT SHORT\nENTRY 95000.0\nSTOP 97000.0")),
        )
        for source, signal in cases:
            with self.subTest(source=source):
                result = size_first_leg(signal, source, self.config)
                self.assertLessEqual(result.risk_amount, result.risk_budget)
                self.assertLessEqual(
                    result.notional,
                    result.bucket * Decimal(self.config.leverage),
                )
                self.assertEqual(Decimal("0"), result.quantity % self.config.quantity_step)

    def test_risk_limited_margin_limited_and_floor_boundaries(self) -> None:
        risk_signal = parse_signal("BTCUSDT LONG\nENTRY 100.0\nSTOP 90.0")
        risk_result = size_first_leg(risk_signal, Source.SCALPING, self.config)
        self.assertLessEqual(risk_result.risk_amount, risk_result.risk_budget)

        margin_config = dataclasses.replace(
            self.config,
            adverse_cost_per_unit=Decimal("0"),
            quantity_step=Decimal("0.001"),
        )
        margin_signal = parse_signal("BTCUSDT LONG\nENTRY 100.0\nSTOP 99.9")
        margin_result = size_first_leg(margin_signal, Source.SCALPING, margin_config)
        self.assertEqual(Decimal("150"), margin_result.quantity)
        self.assertEqual(Decimal("0"), margin_result.quantity % Decimal("0.001"))

        tiny_config = dataclasses.replace(
            self.config,
            account_equity=Decimal("1"),
            quantity_step=Decimal("1"),
        )
        with self.assertRaisesRegex(SizingError, "ZERO_QUANTITY"):
            size_first_leg(risk_signal, Source.SCALPING, tiny_config)

    def test_off_tick_prices_reject_without_rounding(self) -> None:
        signal = parse_signal("BTCUSDT LONG\nENTRY 94700.05\nSTOP 92900.0")
        with self.assertRaisesRegex(SizingError, "PRICE_OFF_TICK"):
            size_first_leg(signal, Source.SCALPING, self.config)


class JournalAndReplayTests(unittest.TestCase):
    def test_fresh_database_replay_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = run_replay(FIXTURE_PATH, CONFIG_PATH, Path(tmp) / "a.sqlite3")
            second = run_replay(FIXTURE_PATH, CONFIG_PATH, Path(tmp) / "b.sqlite3")
            self.assertEqual(render_summary(first), render_summary(second))
            self.assertEqual(2, first["accepted"])
            self.assertEqual(2, first["intents"])

    def test_same_database_replay_is_duplicate_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "state.sqlite3"
            run_replay(FIXTURE_PATH, CONFIG_PATH, db)
            second = run_replay(FIXTURE_PATH, CONFIG_PATH, db)
            self.assertEqual(0, second["accepted"])
            self.assertEqual(2, second["duplicates"])
            self.assertEqual(2, second["setups"])
            self.assertTrue(all(item["journaled"] is False for item in second["outcomes"]))

    def test_mixed_invalid_replay_rejects_again_and_duplicates_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "mixed.jsonl"
            input_path.write_text(
                json.dumps(event()) + "\n" + json.dumps({"source": "scalping"}) + "\n",
                encoding="utf-8",
            )
            db = Path(tmp) / "state.sqlite3"
            first = run_replay(input_path, CONFIG_PATH, db)
            second = run_replay(input_path, CONFIG_PATH, db)
            self.assertEqual((1, 1), (first["accepted"], first["rejected"]))
            self.assertEqual((1, 1), (second["duplicates"], second["rejected"]))
            self.assertEqual("INVALID_EVENT_ENVELOPE", second["outcomes"][1]["reason"])
            self.assertFalse(second["outcomes"][1]["journaled"])

    def test_identity_conflict_creates_no_rows(self) -> None:
        config = load_config(CONFIG_PATH)
        with tempfile.TemporaryDirectory() as tmp, Journal(
            Path(tmp) / "state.sqlite3",
            config.fingerprint,
        ) as journal:
            service = OfflineSignalService(config, journal)
            accepted = service.process_mapping(event())
            conflicting = event(text="BTCUSDT LONG\nENTRY 94600.0\nSTOP 92900.0")
            conflict = service.process_mapping(conflicting)
            self.assertEqual("accepted", accepted.disposition)
            self.assertEqual("conflict", conflict.disposition)
            self.assertEqual(1, journal.event_count())
            self.assertEqual((1, 1), journal.counts())

    def test_source_channel_allowlist_cannot_be_spoofed_or_cross_mapped(self) -> None:
        config = load_config(CONFIG_PATH)
        with tempfile.TemporaryDirectory() as tmp, Journal(
            Path(tmp) / "state.sqlite3",
            config.fingerprint,
        ) as journal:
            service = OfflineSignalService(config, journal)
            spoofed = service.process_mapping(event(channel_id="not-allowlisted"))
            crossed = service.process_mapping(
                event(
                    message_id=2,
                    source="intraday",
                    channel_id=config.scalping_channel_id,
                    text="BTCUSDT SHORT\nENTRY 95000.0\nSTOP 97000.0",
                )
            )
            accepted = service.process_mapping(event(message_id=3))
            self.assertEqual(
                ["rejected", "rejected", "accepted"],
                [spoofed.disposition, crossed.disposition, accepted.disposition],
            )
            self.assertEqual("SOURCE_CHANNEL_NOT_ALLOWED", spoofed.reason)
            self.assertEqual("SOURCE_CHANNEL_NOT_ALLOWED", crossed.reason)
            self.assertEqual((1, 1), journal.counts())

    def test_sixth_local_active_setup_is_rejected(self) -> None:
        config = load_config(CONFIG_PATH)
        with tempfile.TemporaryDirectory() as tmp, Journal(
            Path(tmp) / "state.sqlite3",
            config.fingerprint,
        ) as journal:
            service = OfflineSignalService(config, journal)
            outcomes = [service.process_mapping(event(message_id=index)) for index in range(1, 7)]
            self.assertEqual(["accepted"] * 5 + ["rejected"], [item.disposition for item in outcomes])
            self.assertEqual("MAX_ACTIVE_SETUPS_REACHED", outcomes[-1].reason)
            self.assertEqual((5, 5), journal.counts())
            self.assertEqual(6, journal.event_count())

    def test_write_failure_rolls_back_whole_decision(self) -> None:
        config = load_config(CONFIG_PATH)
        with tempfile.TemporaryDirectory() as tmp, Journal(
            Path(tmp) / "state.sqlite3",
            config.fingerprint,
        ) as journal:
            service = OfflineSignalService(config, journal)
            with mock.patch.object(journal, "insert_setup", side_effect=RuntimeError("injected")):
                with self.assertRaisesRegex(RuntimeError, "injected"):
                    service.process_mapping(event())
            self.assertEqual(0, journal.event_count())
            self.assertEqual((0, 0), journal.counts())

    def test_database_is_bound_to_config_fingerprint(self) -> None:
        config = load_config(CONFIG_PATH)
        other = dataclasses.replace(
            config,
            account_equity=Decimal("20000"),
            fingerprint="f" * 64,
        )
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "state.sqlite3"
            with Journal(db, config.fingerprint):
                pass
            with self.assertRaises(ConfigFingerprintMismatch):
                Journal(db, other.fingerprint)
            connection = sqlite3.connect(db)
            try:
                count = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
                fingerprint = connection.execute(
                    "SELECT value FROM metadata WHERE key='config_fingerprint'"
                ).fetchone()[0]
            finally:
                connection.close()
            self.assertEqual(0, count)
            self.assertEqual(config.fingerprint, fingerprint)

    def test_rejected_valid_envelope_is_journaled(self) -> None:
        config = load_config(CONFIG_PATH)
        with tempfile.TemporaryDirectory() as tmp, Journal(
            Path(tmp) / "state.sqlite3",
            config.fingerprint,
        ) as journal:
            service = OfflineSignalService(config, journal)
            result = service.process_mapping(event(text="ETHUSDT LONG\nENTRY 100\nSTOP 90"))
            self.assertEqual("rejected", result.disposition)
            self.assertTrue(result.journaled)
            self.assertEqual(1, journal.event_count())
            self.assertEqual((0, 0), journal.counts())

    def test_package_has_no_network_or_exchange_submission_path(self) -> None:
        forbidden = (
            "import aiohttp",
            "import ccxt",
            "import httpx",
            "import requests",
            "import socket",
            "import telethon",
            "urllib.request",
        )
        sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((ROOT / "tradebot_mvp").glob("*.py"))
        ).lower()
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, sources)
        self.assertNotIn("submitted", sources)
        self.assertNotIn("filled", sources)

    def test_database_is_owner_only_and_raw_private_input_is_not_persisted(self) -> None:
        config = load_config(CONFIG_PATH)
        raw_text = "BTCUSDT LONG\nENTRY 94700.0\nSTOP 92900.0\nRISK PRIVATE-MARKER"
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "state.sqlite3"
            previous_umask = os.umask(0o022)
            try:
                with Journal(db, config.fingerprint) as journal:
                    outcome = OfflineSignalService(config, journal).process_mapping(
                        event(text=raw_text)
                    )
                    stored = "\n".join(
                        str(value)
                        for table in ("events", "setups", "journal_events")
                        for row in journal.connection.execute(f"SELECT * FROM {table}")
                        for value in row
                    )
                    journal_payload = journal.connection.execute(
                        """
                        SELECT payload_json
                        FROM journal_events
                        WHERE event_type = 'SIMULATED_LIMIT_INTENT_CREATED'
                        """
                    ).fetchone()[0]
                    sidecar_modes = {
                        candidate.name: stat.S_IMODE(candidate.stat().st_mode)
                        for candidate in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm"))
                        if candidate.exists()
                    }
            finally:
                os.umask(previous_umask)
            self.assertEqual("accepted", outcome.disposition)
            self.assertEqual(0o600, stat.S_IMODE(db.stat().st_mode))
            self.assertTrue(sidecar_modes)
            self.assertTrue(all(mode == 0o600 for mode in sidecar_modes.values()))
            self.assertNotIn("PRIVATE-MARKER", stored)
            self.assertNotIn(config.scalping_channel_id, stored)
            self.assertNotIn(config.scalping_channel_id, outcome.event_identity or "")
            self.assertIn('"risk_amount":"22.2"', journal_payload)
            self.assertNotIn("22.2000", journal_payload)

    def test_database_symlink_target_is_rejected(self) -> None:
        config = load_config(CONFIG_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target.sqlite3"
            target.write_bytes(b"")
            link = Path(tmp) / "link.sqlite3"
            link.symlink_to(target)
            with self.assertRaisesRegex(OSError, "UNSAFE_DATABASE_PATH"):
                Journal(link, config.fingerprint)


if __name__ == "__main__":
    unittest.main()
