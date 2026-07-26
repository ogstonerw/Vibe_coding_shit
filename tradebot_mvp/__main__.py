from __future__ import annotations

import argparse
import json
import sqlite3
from collections.abc import Sequence

from .config import ConfigError
from .journal import ConfigFingerprintMismatch
from .replay import ReplayInputError, render_summary, run_replay


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 -m tradebot_mvp")
    subparsers = parser.add_subparsers(dest="command", required=True)
    replay = subparsers.add_parser("replay", help="replay an offline JSONL fixture")
    replay.add_argument("--input", required=True)
    replay.add_argument("--config", required=True)
    replay.add_argument("--db", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = run_replay(args.input, args.config, args.db)
    except ConfigFingerprintMismatch:
        print(
            json.dumps(
                {"reason": "CONFIG_FINGERPRINT_MISMATCH", "status": "ERROR"},
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 2
    except ConfigError as exc:
        print(
            json.dumps(
                {"reason": exc.reason, "status": "ERROR"},
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 2
    except ReplayInputError as exc:
        print(
            json.dumps(
                {"reason": exc.reason, "status": "ERROR"},
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 2
    except (OSError, UnicodeDecodeError, UnicodeEncodeError, sqlite3.Error):
        print(
            json.dumps(
                {"reason": "INPUT_OR_DATABASE_ERROR", "status": "ERROR"},
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 2
    print(render_summary(summary), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
