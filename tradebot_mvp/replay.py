from __future__ import annotations

import json
import stat
from pathlib import Path
from typing import Any

from .config import MvpConfig, load_config
from .contracts import Outcome
from .journal import Journal
from .service import OfflineSignalService


class DuplicateJsonKey(ValueError):
    pass


class ReplayInputError(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_LINE_BYTES = 64 * 1024
MAX_RECORDS = 10_000


def _closed_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKey(key)
        result[key] = value
    return result


def _decode_line(line: str) -> object:
    try:
        return json.loads(line, object_pairs_hook=_closed_json_object)
    except (ValueError, DuplicateJsonKey, RecursionError):
        return None


def run_replay_with_config(
    input_path: str | Path,
    config: MvpConfig,
    db_path: str | Path,
) -> dict[str, Any]:
    outcomes: list[dict[str, Any]] = []
    counters = {"accepted": 0, "conflict": 0, "duplicate": 0, "rejected": 0}

    with Journal(db_path, config.fingerprint) as journal:
        service = OfflineSignalService(config, journal)
        input_file = Path(input_path)
        input_stat = input_file.stat()
        if (
            input_file.is_symlink()
            or not stat.S_ISREG(input_stat.st_mode)
            or input_stat.st_size > MAX_INPUT_BYTES
        ):
            raise ReplayInputError("INPUT_LIMIT_EXCEEDED")
        with input_file.open("rb") as stream:
            total_bytes = 0
            for line_number, raw_line in enumerate(stream, start=1):
                total_bytes += len(raw_line)
                if (
                    line_number > MAX_RECORDS
                    or len(raw_line) > MAX_LINE_BYTES
                    or total_bytes > MAX_INPUT_BYTES
                ):
                    raise ReplayInputError("INPUT_LIMIT_EXCEEDED")
                raw_line.rstrip(b"\r\n").decode("utf-8")

            stream.seek(0)
            for line_number, raw_line in enumerate(stream, start=1):
                line = raw_line.rstrip(b"\r\n").decode("utf-8")
                mapping = _decode_line(line)
                outcome: Outcome = service.process_mapping(mapping)
                counters[outcome.disposition] += 1
                rendered = outcome.as_dict()
                rendered["line"] = line_number
                outcomes.append(rendered)

        setups, intents = journal.counts()

    return {
        "accepted": counters["accepted"],
        "config_fingerprint": config.fingerprint,
        "conflicts": counters["conflict"],
        "duplicates": counters["duplicate"],
        "intents": intents,
        "outcomes": outcomes,
        "rejected": counters["rejected"],
        "setups": setups,
        "stage": "OFFLINE_SIMULATION",
    }


def run_replay(
    input_path: str | Path,
    config_path: str | Path,
    db_path: str | Path,
) -> dict[str, Any]:
    return run_replay_with_config(input_path, load_config(config_path), db_path)


def render_summary(summary: dict[str, Any]) -> str:
    return json.dumps(
        summary,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
