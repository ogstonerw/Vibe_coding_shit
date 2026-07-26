from __future__ import annotations

import contextlib
import dataclasses
import io
import tempfile
import unittest
from decimal import Context, DefaultContext, Inexact, Rounded, localcontext
from pathlib import Path

from tradebot_mvp.__main__ import main
from tradebot_mvp.config import MAX_CONFIG_BYTES, ConfigError, load_config
from tradebot_mvp.contracts import Source
from tradebot_mvp.journal import ConfigFingerprintMismatch, Journal
from tradebot_mvp.parser import parse_signal
from tradebot_mvp.replay import run_replay, run_replay_with_config
from tradebot_mvp.service import OfflineSignalService
from tradebot_mvp.sizing import size_first_leg


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "mvp-offline-demo.toml"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "mvp_signals.jsonl"


def event(message_id: int) -> dict[str, object]:
    return {
        "source": "scalping",
        "channel_id": "-1000000000001",
        "message_id": message_id,
        "revision": 0,
        "timestamp": "2026-07-24T12:00:00Z",
        "text": "BTCUSDT LONG\nENTRY 94700.0\nSTOP 92900.0",
    }


class AdversarialRegressionTests(unittest.TestCase):
    def test_tick_validation_is_independent_of_ambient_decimal_context(self) -> None:
        config = load_config(CONFIG_PATH)
        signal = parse_signal(event(1)["text"])
        baseline = size_first_leg(signal, Source.SCALPING, config)

        with localcontext(Context(prec=5)):
            adversarial = size_first_leg(signal, Source.SCALPING, config)

        self.assertEqual(baseline, adversarial)

    def test_sizing_is_independent_of_mutated_default_context_traps(self) -> None:
        config = load_config(CONFIG_PATH)
        signal = parse_signal(event(1)["text"])
        baseline = size_first_leg(signal, Source.SCALPING, config)
        original_traps = dict(DefaultContext.traps)
        try:
            DefaultContext.traps[Inexact] = True
            DefaultContext.traps[Rounded] = True
            mutated = size_first_leg(signal, Source.SCALPING, config)
        finally:
            for condition, enabled in original_traps.items():
                DefaultContext.traps[condition] = enabled

        self.assertEqual(baseline, mutated)

    def test_config_fingerprint_mismatch_precedes_input_access(self) -> None:
        config = load_config(CONFIG_PATH)
        other = dataclasses.replace(config, fingerprint="f" * 64)
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "state.sqlite3"
            with Journal(db, config.fingerprint):
                pass

            with self.assertRaises(ConfigFingerprintMismatch):
                run_replay_with_config(Path(tmp) / "missing.jsonl", other, db)

    def test_contract_permitted_nonnegative_integer_can_be_journaled(self) -> None:
        config = load_config(CONFIG_PATH)
        with tempfile.TemporaryDirectory() as tmp, Journal(
            Path(tmp) / "state.sqlite3", config.fingerprint
        ) as journal:
            service = OfflineSignalService(config, journal)
            outcome = service.process_mapping(event(2**63 - 1))
            rejected = service.process_mapping(event(2**63))

        self.assertEqual("accepted", outcome.disposition)
        self.assertEqual("rejected", rejected.disposition)
        self.assertEqual("INVALID_EVENT_ENVELOPE", rejected.reason)
        self.assertFalse(rejected.journaled)

    def test_json_identity_integer_has_no_implicit_runtime_digit_ceiling(self) -> None:
        message_id = "1" * 4301
        line = (
            '{"source":"scalping","channel_id":"-1001","message_id":'
            + message_id
            + ',"revision":0,"timestamp":"2026-07-24T12:00:00Z",'
            '"text":"BTCUSDT LONG\\nENTRY 94700.0\\nSTOP 92900.0"}\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "input.jsonl"
            input_path.write_text(line, encoding="utf-8")
            summary = run_replay(input_path, CONFIG_PATH, Path(tmp) / "state.sqlite3")

        self.assertEqual(0, summary["accepted"])
        self.assertEqual(1, summary["rejected"])
        self.assertEqual("INVALID_EVENT_ENVELOPE", summary["outcomes"][0]["reason"])

    def test_corrupt_sqlite_is_a_deterministic_cli_database_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "corrupt.sqlite3"
            db.write_bytes(b"not a sqlite database")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                status = main(
                    [
                        "replay",
                        "--input",
                        str(FIXTURE_PATH),
                        "--config",
                        str(CONFIG_PATH),
                        "--db",
                        str(db),
                    ]
                )

        self.assertEqual(2, status)
        self.assertEqual(
            '{"reason":"INPUT_OR_DATABASE_ERROR","status":"ERROR"}\n',
            stdout.getvalue(),
        )

    def test_surrogate_event_and_nested_toml_fail_deterministically(self) -> None:
        surrogate_line = (
            '{"source":"scalping","channel_id":"\\ud800","message_id":1,'
            '"revision":0,"timestamp":"2026-07-24T12:00:00Z",'
            '"text":"BTCUSDT LONG\\nENTRY 94700.0\\nSTOP 92900.0"}\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "surrogate.jsonl"
            input_path.write_text(surrogate_line, encoding="utf-8")
            summary = run_replay(input_path, CONFIG_PATH, Path(tmp) / "state.sqlite3")
            nested_config = Path(tmp) / "nested.toml"
            nested_config.write_text("x = " + "[" * 1000 + "0" + "]" * 1000, encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "CONFIG_READ_OR_PARSE_FAILED"):
                load_config(nested_config)

        self.assertEqual(1, summary["rejected"])
        self.assertEqual("INVALID_EVENT_ENVELOPE", summary["outcomes"][0]["reason"])

    def test_deep_json_is_rejected_without_recursion_error(self) -> None:
        deep_json = "[" * 10_000 + "0" + "]" * 10_000 + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "deep.jsonl"
            input_path.write_text(deep_json, encoding="utf-8")
            summary = run_replay(input_path, CONFIG_PATH, Path(tmp) / "state.sqlite3")

        self.assertEqual(1, summary["rejected"])
        self.assertEqual("INVALID_EVENT_ENVELOPE", summary["outcomes"][0]["reason"])

    def test_oversized_config_is_rejected_by_bounded_reader(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "oversized.toml"
            config_path.write_bytes(b"x" * (MAX_CONFIG_BYTES + 1))
            with self.assertRaisesRegex(ConfigError, "CONFIG_READ_OR_PARSE_FAILED"):
                load_config(config_path)

    def test_input_line_limit_is_a_deterministic_cli_error(self) -> None:
        oversized_line = b"{" + (b"x" * (64 * 1024)) + b"}\n"
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "oversized.jsonl"
            input_path.write_bytes(oversized_line)
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                status = main(
                    [
                        "replay",
                        "--input",
                        str(input_path),
                        "--config",
                        str(CONFIG_PATH),
                        "--db",
                        str(Path(tmp) / "state.sqlite3"),
                    ]
                )

        self.assertEqual(2, status)
        self.assertEqual(
            '{"reason":"INPUT_LIMIT_EXCEEDED","status":"ERROR"}\n',
            stdout.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()
