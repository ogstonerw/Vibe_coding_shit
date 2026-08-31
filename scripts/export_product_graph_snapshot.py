"""Export the canonical Product Graph as the read-only Owner HQ projection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product_graph import Lock, ProductGraph, Wave


CANONICAL_SOURCE = ROOT / "docs" / "product" / "PRODUCT_GRAPH_BOOTSTRAP.toml"
DEFAULT_OUTPUT = (
    ROOT
    / "apps"
    / "bot-farm-ui"
    / "src"
    / "data"
    / "generated"
    / "productGraphSnapshot.json"
)


def _wave_projection(wave: Wave, *, next_wave_id: str | None) -> dict[str, Any]:
    if wave.status == "DONE":
        display_state = "DONE"
    elif wave.status == "ACTIVE":
        display_state = "CURRENT"
    elif wave.id == next_wave_id:
        display_state = "NEXT"
    elif wave.status == "LOCKED":
        display_state = "LOCKED"
    else:
        display_state = "PLANNED"

    return {
        "display_state": display_state,
        "id": wave.id,
        "status": wave.status,
        "title": wave.title,
    }


def build_owner_hq_snapshot(
    graph: ProductGraph,
    *,
    source_path: Path = CANONICAL_SOURCE,
) -> dict[str, Any]:
    """Derive only the Product Graph fields consumed by Owner HQ."""

    if not graph.is_read_only_snapshot:
        raise ValueError("Owner HQ projection requires the read-only Product Graph bootstrap")

    try:
        canonical_path = source_path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        canonical_path = source_path.resolve().as_posix()

    waves = graph.waves()
    domains = graph.domains()
    epics = graph.epics()
    current_wave = graph.current_wave()
    next_wave = graph.next_wave()
    explicit_locks = tuple(item for item in graph.locked() if isinstance(item, Lock))
    lock_by_subject = {item.subject: item for item in explicit_locks}

    authority_subjects = (
        ("PAPER", "Paper"),
        ("LIMITED_LIVE", "Limited Live"),
        ("LIVE", "Live"),
    )
    missing_authority_locks = [
        subject for subject, _ in authority_subjects if subject not in lock_by_subject
    ]
    if missing_authority_locks:
        raise ValueError(
            "Owner HQ projection is missing authority locks: "
            + ", ".join(missing_authority_locks)
        )

    return {
        "schema_version": 1,
        "source": {
            "classification": graph.source_classification,
            "generated_from": canonical_path,
            "name": source_path.stem,
            "operational": graph.source_operational,
            "projection": "READ_ONLY",
            "writable_runtime_truth": graph.source_writable_runtime_truth,
        },
        "product": {
            "name": graph.product.name,
            "north_star": graph.product.north_star,
        },
        "development": {
            "current_wave_id": current_wave.id if current_wave else None,
            "next_wave_id": next_wave.id if next_wave else None,
            "waves": [
                _wave_projection(
                    wave,
                    next_wave_id=next_wave.id if next_wave else None,
                )
                for wave in waves
            ],
        },
        "summary": {
            "domain_count": len(domains),
            "epic_count": len(epics),
            "locked_object_count": len(graph.locked()),
            "wave_count": len(waves),
        },
        "authority": {
            "capital_authority": graph.capital_authority,
            "environments": [
                {
                    "label": label,
                    "locked": lock_by_subject[subject].locked,
                    "reason": lock_by_subject[subject].reason,
                    "status": lock_by_subject[subject].status,
                    "subject": subject,
                }
                for subject, label in authority_subjects
            ],
        },
        "owner_decisions_required": [
            {
                "id": item.id,
                "reason": item.reason,
                "status": item.status,
                "subject": item.subject,
            }
            for item in explicit_locks
            if item.status == "NEEDS_OWNER"
        ],
    }


def export_owner_hq_snapshot(
    source_path: Path = CANONICAL_SOURCE,
    output_path: Path = DEFAULT_OUTPUT,
) -> bytes:
    graph = ProductGraph.load(source_path)
    snapshot = build_owner_hq_snapshot(graph, source_path=source_path)
    rendered = (
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(rendered)
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=CANONICAL_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    export_owner_hq_snapshot(args.source, args.output)
    print(f"OWNER_HQ_PRODUCT_GRAPH_SNAPSHOT: PASS ({args.output})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
