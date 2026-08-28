#!/usr/bin/env python3
"""Validate the non-operational Product Graph bootstrap deterministically."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
import tomllib
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOOTSTRAP = REPOSITORY_ROOT / "docs" / "product" / "PRODUCT_GRAPH_BOOTSTRAP.toml"
EXPECTED_HEAD = "bd0027c316087a11193ca6662c27861adc87030f"

STATUS_VOCABULARY = frozenset(
    {
        "DONE",
        "READY",
        "ACTIVE",
        "PLANNED",
        "PROPOSED",
        "EXPERIMENT",
        "NEEDS_OWNER",
        "BLOCKED",
        "LOCKED",
        "SUPERSEDED",
        "UNKNOWN_FRONTIER",
    }
)
DOMAIN_AUTHORITY_VOCABULARY = frozenset(
    {
        "SPECIFICATION_ONLY",
        "FACTORY_001A_ONLY",
        "CAPITAL_LOCKED",
        "OFFLINE_MANDATE_AUTHORING_SPEC_ONLY_CAPITAL_LOCKED",
        "OFFLINE_RELEASE_SPEC_ONLY",
        "PROPOSAL_ONLY",
        "NO_AUTHORITY",
    }
)
WAVE_AUTHORITY_VOCABULARY = frozenset(
    {
        "DOCUMENTATION_AND_APPROVED_OFFLINE_WORK_ONLY",
        "ENVIRONMENT_SCOPED_AND_SEPARATELY_GATED",
        "FACTORY_001A_ONLY",
        "NEEDS_OWNER",
        "NEEDS_OWNER_LIVE_GATE",
        "NO_IMPLICIT_AUTHORITY",
        "OFFLINE_ONLY",
        "PROPOSAL_ONLY_BY_DEFAULT",
        "RELEASED_OFFLINE_MAXIMUM",
        "SHADOW_ONLY_UNTIL_SEPARATE_OWNER_GATE",
    }
)
DEPENDENCY_TYPES = frozenset(
    {"SCHEMA_INTERFACE", "READINESS", "ARTIFACT_EVIDENCE", "OPERATIONAL_SERVICE", "AUTHORITY"}
)
DEPENDENCY_KINDS = frozenset(
    {"WAVE", "EPIC", "CAPABILITY", "TASK", "WORK_UNIT", "AUTHORITY_GATE", "CROSS_SCOPE"}
)
PRODUCT_CYCLE = (
    "OWNER_INTENT",
    "KNOWLEDGE",
    "RESEARCH",
    "HYPOTHESIS",
    "STRATEGY",
    "BOT",
    "PROVE",
    "RELEASE",
    "OPERATE",
    "OBSERVE",
    "LEARN",
    "EVOLVE",
)

TOP_SCALAR_SCHEMA = {
    "schema_version": int,
    "artifact_id": str,
    "title": str,
    "classification": str,
    "operational": bool,
    "writable_runtime_truth": bool,
    "created_on": str,
    "current_software_factory_runtime_registry": str,
    "future_product_graph_runtime_truth": str,
    "semantics_source": str,
    "sequence_source": str,
    "migration_target": str,
    "migration_rule": str,
}
TABLE_SCHEMAS: dict[str, tuple[dict[str, type], dict[str, type]]] = {
    "product": (
        {"id": str, "name": str, "owner_model": str, "status": str, "north_star": str, "cycle": list},
        {},
    ),
    "baseline": (
        {
            "id": str,
            "status": str,
            "git_head": str,
            "source_branch": str,
            "evidence_refs": list,
            "note": str,
        },
        {},
    ),
    "authority": (
        {
            "capital_authority": bool,
            "paper_authority": bool,
            "limited_live_authority": bool,
            "live_authority": bool,
            "current_factory_stage": str,
            "current_product_change_scope": str,
            "product_change_levels": list,
            "capital_mandate_level_namespace": str,
        },
        {},
    ),
    "bootstrap_policy": (
        {
            "dependency_graph_must_be_acyclic": bool,
            "dependency_references_must_resolve": bool,
            "ids_must_be_globally_unique": bool,
            "done_objects_require_evidence": bool,
            "duplicate_runtime_registry_prohibited": bool,
            "ui_is_projection_only": bool,
        },
        {},
    ),
    "dependency_semantics": (
        {
            "default_dependency_type": str,
            "allowed_dependency_types": list,
            "allowed_kinds": list,
            "note": str,
        },
        {},
    ),
}
COLLECTION_SCHEMAS: dict[str, tuple[dict[str, type], dict[str, type]]] = {
    "locks": (
        {"id": str, "subject": str, "status": str, "locked": bool, "reason": str},
        {},
    ),
    "authority_gates": (
        {
            "id": str,
            "subject": str,
            "status": str,
            "locked": bool,
            "owner_required": bool,
            "grants_authority": bool,
        },
        {},
    ),
    "factory_autonomy": (
        {"id": str, "title": str, "status": str, "locked": bool},
        {"evidence_refs": list},
    ),
    "domains": (
        {"id": str, "title": str, "status": str, "current_authority": str, "wave_ids": list},
        {},
    ),
    "waves": (
        {"id": str, "number": int, "title": str, "status": str, "authority_state": str},
        {"evidence_refs": list},
    ),
    "epics": (
        {"id": str, "wave_id": str, "title": str, "status": str, "domain_ids": list},
        {"evidence_refs": list},
    ),
    "capabilities": (
        {"id": str, "epic_id": str, "title": str, "status": str},
        {"evidence_refs": list},
    ),
    "tasks": (
        {
            "id": str,
            "capability_id": str,
            "title": str,
            "status": str,
            "acceptance_contract_required": bool,
            "non_operational": bool,
        },
        {},
    ),
    "work_units": (
        {
            "id": str,
            "task_id": str,
            "title": str,
            "status": str,
            "requires_previous_pass": bool,
            "non_operational": bool,
        },
        {},
    ),
    "dependencies": (
        {"id": str, "source_id": str, "depends_on": str, "kind": str, "dependency_type": str},
        {},
    ),
    "unknown_frontier": (
        {"id": str, "title": str, "status": str},
        {},
    ),
}
EXPECTED_TOP_LEVEL_KEYS = frozenset(TOP_SCALAR_SCHEMA) | frozenset(TABLE_SCHEMAS) | frozenset(
    COLLECTION_SCHEMAS
)

DEPENDENCY_NODE_COLLECTIONS = (
    "waves",
    "epics",
    "capabilities",
    "tasks",
    "work_units",
    "authority_gates",
)
KIND_BY_COLLECTION = {
    "waves": "WAVE",
    "epics": "EPIC",
    "capabilities": "CAPABILITY",
    "tasks": "TASK",
    "work_units": "WORK_UNIT",
    "authority_gates": "AUTHORITY_GATE",
}
MANDATORY_DEPENDENCIES = {
    ("W1", "W0"): ("WAVE", "READINESS"),
    ("W2", "W1"): ("WAVE", "READINESS"),
    ("W3", "W2"): ("WAVE", "READINESS"),
    ("W4", "W3"): ("WAVE", "READINESS"),
    ("W5", "W4"): ("WAVE", "READINESS"),
    ("W6", "W5"): ("WAVE", "READINESS"),
    ("W7", "W6"): ("WAVE", "READINESS"),
    ("W8", "W7"): ("WAVE", "READINESS"),
    ("W9", "W8"): ("WAVE", "READINESS"),
    ("W10", "W9"): ("WAVE", "READINESS"),
    ("W11", "W10"): ("WAVE", "OPERATIONAL_SERVICE"),
    ("W12", "W11"): ("WAVE", "READINESS"),
    ("EPIC-W1-CANONICAL-PRODUCT-GRAPH", "EPIC-W0-FACTORY-BASELINE"): (
        "EPIC",
        "READINESS",
    ),
    ("EPIC-W1-OWNER-HQ", "EPIC-W1-CANONICAL-PRODUCT-GRAPH"): (
        "EPIC",
        "OPERATIONAL_SERVICE",
    ),
    ("CAP-W7-PAPER-ENVIRONMENT", "CAP-W6-BOUNDED-OPS-SAFETY"): (
        "CAPABILITY",
        "OPERATIONAL_SERVICE",
    ),
    ("CAP-W7-PAPER-ENVIRONMENT", "CAP-W6-OFFLINE-RELEASE-ROLLBACK"): (
        "CAPABILITY",
        "ARTIFACT_EVIDENCE",
    ),
    ("CAP-W9-SHADOW-PORTFOLIO", "CAP-W7-PAPER-ENVIRONMENT"): (
        "CAPABILITY",
        "ARTIFACT_EVIDENCE",
    ),
    ("CAP-W10-FLEET-OPERATIONS", "CAP-W6-BOUNDED-OPS-SAFETY"): (
        "CAPABILITY",
        "OPERATIONAL_SERVICE",
    ),
    ("WU-W1-OWNER-HQ-ACCEPTANCE", "WU-W1-GRAPH-MIGRATION-CONTRACT"): (
        "WORK_UNIT",
        "READINESS",
    ),
    ("CAP-W7-PAPER-ENVIRONMENT", "GATE-PAPER-OWNER"): ("CROSS_SCOPE", "AUTHORITY"),
    ("CAP-W8-LIMITED-LIVE-ENVIRONMENT", "CAP-W7-PAPER-ENVIRONMENT"): (
        "CAPABILITY",
        "ARTIFACT_EVIDENCE",
    ),
    ("CAP-W8-LIMITED-LIVE-ENVIRONMENT", "GATE-LIMITED-LIVE-OWNER"): (
        "CROSS_SCOPE",
        "AUTHORITY",
    ),
}

REQUIRED_LOCKS = {
    "FACTORY-001B": ("LOCK-FACTORY-001B", "NEEDS_OWNER", True),
    "FACTORY-001C": ("LOCK-FACTORY-001C", "LOCKED", True),
    "FACTORY-001D": ("LOCK-FACTORY-001D", "LOCKED", True),
    "FACTORY-001E": ("LOCK-FACTORY-001E", "LOCKED", True),
    "PAPER": ("LOCK-PAPER", "LOCKED", True),
    "LIMITED_LIVE": ("LOCK-LIMITED-LIVE", "LOCKED", True),
    "LIVE": ("LOCK-LIVE", "LOCKED", True),
    "CAPITAL_AUTHORITY": ("LOCK-CAPITAL-AUTHORITY", "LOCKED", True),
}
REQUIRED_GATES = {
    "PAPER": "GATE-PAPER-OWNER",
    "LIMITED_LIVE": "GATE-LIMITED-LIVE-OWNER",
    "LIVE": "GATE-LIVE-OWNER",
}
REQUIRED_FACTORY_STAGES = {
    "FACTORY-001A": ("DONE", False),
    "FACTORY-001B": ("NEEDS_OWNER", True),
    "FACTORY-001C": ("LOCKED", True),
    "FACTORY-001D": ("LOCKED", True),
    "FACTORY-001E": ("LOCKED", True),
}


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    path: str
    message: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.path}: {self.message}"


def _issue(issues: list[ValidationIssue], code: str, path: str, message: str) -> None:
    issues.append(ValidationIssue(code, path, message))


def _type_matches(value: Any, expected: type) -> bool:
    return type(value) is expected


def _validate_closed_object(
    value: Any,
    path: str,
    required: dict[str, type],
    optional: dict[str, type],
    issues: list[ValidationIssue],
) -> dict[str, Any] | None:
    if type(value) is not dict:
        _issue(issues, "E_OBJECT_TYPE", path, "must be a TOML table")
        return None

    allowed = frozenset(required) | frozenset(optional)
    for field in sorted(set(value) - allowed):
        _issue(issues, "E_FIELD_UNKNOWN", f"{path}.{field}", "field is not allowed")
    for field in sorted(set(required) - set(value)):
        _issue(issues, "E_FIELD_MISSING", f"{path}.{field}", "required field is missing")
    for field, expected in {**required, **optional}.items():
        if field not in value:
            continue
        field_value = value[field]
        if not _type_matches(field_value, expected):
            _issue(
                issues,
                "E_FIELD_TYPE",
                f"{path}.{field}",
                f"must be {expected.__name__}, got {type(field_value).__name__}",
            )
        elif expected is str and not field_value:
            _issue(issues, "E_STRING_EMPTY", f"{path}.{field}", "must be non-empty")
    return value


def _validate_string_list(
    value: Any,
    path: str,
    issues: list[ValidationIssue],
    *,
    allow_empty: bool,
) -> list[str]:
    if type(value) is not list:
        _issue(issues, "E_FIELD_TYPE", path, f"must be list, got {type(value).__name__}")
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if type(item) is not str or not item:
            _issue(issues, "E_LIST_ITEM_TYPE", f"{path}[{index}]", "must be a non-empty string")
        else:
            result.append(item)
    if not allow_empty and not result:
        _issue(issues, "E_LIST_EMPTY", path, "must contain at least one non-empty string")
    if len(result) != len(set(result)):
        _issue(issues, "E_LIST_DUPLICATE", path, "must not contain duplicate values")
    return result


def load_bootstrap(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def validate_graph(data: Any) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if type(data) is not dict:
        _issue(issues, "E_ROOT_TYPE", "$", "TOML root must be a table")
        return issues

    for key in sorted(set(data) - EXPECTED_TOP_LEVEL_KEYS):
        _issue(issues, "E_TOP_LEVEL_UNKNOWN", key, "top-level object is not allowed")
    for key in sorted(EXPECTED_TOP_LEVEL_KEYS - set(data)):
        _issue(issues, "E_TOP_LEVEL_MISSING", key, "required top-level object is missing")

    for field, expected in TOP_SCALAR_SCHEMA.items():
        if field not in data:
            continue
        value = data[field]
        if not _type_matches(value, expected):
            _issue(
                issues,
                "E_FIELD_TYPE",
                field,
                f"must be {expected.__name__}, got {type(value).__name__}",
            )
        elif expected is str and not value:
            _issue(issues, "E_STRING_EMPTY", field, "must be non-empty")

    tables: dict[str, dict[str, Any]] = {}
    for name, (required, optional) in TABLE_SCHEMAS.items():
        if name not in data:
            continue
        table = _validate_closed_object(data[name], name, required, optional, issues)
        if table is not None:
            tables[name] = table

    collections: dict[str, list[dict[str, Any]]] = {}
    for name, (required, optional) in COLLECTION_SCHEMAS.items():
        if name not in data:
            continue
        value = data[name]
        if type(value) is not list:
            _issue(issues, "E_COLLECTION_TYPE", name, "must be an array of tables")
            collections[name] = []
            continue
        valid_items: list[dict[str, Any]] = []
        for index, item in enumerate(value):
            obj = _validate_closed_object(item, f"{name}[{index}]", required, optional, issues)
            if obj is not None:
                valid_items.append(obj)
        collections[name] = valid_items

    def items(name: str) -> list[dict[str, Any]]:
        return collections.get(name, [])

    expected_top_values = {
        "schema_version": 1,
        "artifact_id": "PRODUCT-GRAPH-BOOTSTRAP-V1",
        "classification": "NON_OPERATIONAL_PRODUCT_GRAPH_BOOTSTRAP",
        "operational": False,
        "writable_runtime_truth": False,
        "current_software_factory_runtime_registry": "factory/registry.toml",
        "future_product_graph_runtime_truth": "UNASSIGNED_UNTIL_W1_MIGRATION",
        "semantics_source": "docs/product/PRODUCT_MASTER_SPEC.md",
        "sequence_source": "docs/product/MASTER_ROADMAP.md",
        "migration_target": "W1_CANONICAL_PRODUCT_GRAPH",
        "migration_rule": "MIGRATE_OR_INGEST_ONCE_THEN_RETIRE_AS_WRITABLE_INPUT",
    }
    for field, expected in expected_top_values.items():
        if data.get(field) != expected or type(data.get(field)) is not type(expected):
            _issue(issues, "E_BOOTSTRAP_AUTHORITY", field, f"must equal {expected!r}")

    product = tables.get("product", {})
    if product:
        if product.get("id") != "PRODUCT-AITOS":
            _issue(issues, "E_PRODUCT_ID", "product.id", "must be PRODUCT-AITOS")
        if product.get("owner_model") != "ONE_OWNER":
            _issue(issues, "E_PRODUCT_OWNER", "product.owner_model", "must be ONE_OWNER")
        cycle = _validate_string_list(product.get("cycle"), "product.cycle", issues, allow_empty=False)
        if tuple(cycle) != PRODUCT_CYCLE:
            _issue(issues, "E_PRODUCT_CYCLE", "product.cycle", "must match the canonical product cycle")

    authority = tables.get("authority", {})
    if authority:
        for field in (
            "capital_authority",
            "paper_authority",
            "limited_live_authority",
            "live_authority",
        ):
            if authority.get(field) is not False:
                _issue(issues, "E_AUTHORITY_STATE", f"authority.{field}", "must be false")
        if authority.get("current_factory_stage") != "FACTORY-001A":
            _issue(
                issues,
                "E_AUTHORITY_STATE",
                "authority.current_factory_stage",
                "must be FACTORY-001A",
            )
        if authority.get("current_product_change_scope") != "DOCUMENTATION_ONLY":
            _issue(
                issues,
                "E_AUTHORITY_STATE",
                "authority.current_product_change_scope",
                "must be DOCUMENTATION_ONLY",
            )
        levels = _validate_string_list(
            authority.get("product_change_levels"),
            "authority.product_change_levels",
            issues,
            allow_empty=False,
        )
        if levels != ["PRODUCT_CHANGE_LEVEL_A", "PRODUCT_CHANGE_LEVEL_B", "PRODUCT_CHANGE_LEVEL_C"]:
            _issue(
                issues,
                "E_AUTHORITY_VOCABULARY",
                "authority.product_change_levels",
                "must contain the documented Product Change levels in order",
            )
        if authority.get("capital_mandate_level_namespace") != "SEPARATE_FROM_PRODUCT_CHANGE_LEVELS":
            _issue(
                issues,
                "E_AUTHORITY_STATE",
                "authority.capital_mandate_level_namespace",
                "must remain separate from Product Change levels",
            )

    policy = tables.get("bootstrap_policy", {})
    if policy:
        for field in TABLE_SCHEMAS["bootstrap_policy"][0]:
            if policy.get(field) is not True:
                _issue(issues, "E_BOOTSTRAP_POLICY", f"bootstrap_policy.{field}", "must be true")

    semantics = tables.get("dependency_semantics", {})
    if semantics:
        dependency_types = _validate_string_list(
            semantics.get("allowed_dependency_types"),
            "dependency_semantics.allowed_dependency_types",
            issues,
            allow_empty=False,
        )
        dependency_kinds = _validate_string_list(
            semantics.get("allowed_kinds"),
            "dependency_semantics.allowed_kinds",
            issues,
            allow_empty=False,
        )
        if semantics.get("default_dependency_type") != "READINESS":
            _issue(
                issues,
                "E_DEPENDENCY_VOCABULARY",
                "dependency_semantics.default_dependency_type",
                "must be READINESS",
            )
        if set(dependency_types) != DEPENDENCY_TYPES:
            _issue(
                issues,
                "E_DEPENDENCY_VOCABULARY",
                "dependency_semantics.allowed_dependency_types",
                "must equal the documented dependency type vocabulary",
            )
        if set(dependency_kinds) != DEPENDENCY_KINDS:
            _issue(
                issues,
                "E_DEPENDENCY_VOCABULARY",
                "dependency_semantics.allowed_kinds",
                "must equal the documented dependency kind vocabulary",
            )

    identified: list[tuple[str, dict[str, Any]]] = []
    for name in ("product", "baseline"):
        if name in tables:
            identified.append((name, tables[name]))
    for name in COLLECTION_SCHEMAS:
        identified.extend((f"{name}[{index}]", item) for index, item in enumerate(items(name)))

    seen_ids: dict[str, str] = {}
    for path, item in identified:
        item_id = item.get("id")
        if type(item_id) is str and item_id:
            previous = seen_ids.get(item_id)
            if previous is not None:
                _issue(issues, "E_ID_DUPLICATE", f"{path}.id", f"duplicates {item_id} from {previous}")
            else:
                seen_ids[item_id] = path
        status = item.get("status")
        if type(status) is str and status not in STATUS_VOCABULARY:
            _issue(issues, "E_STATUS_INVALID", f"{path}.status", f"unknown status {status}")
        if "evidence_refs" in item:
            evidence = _validate_string_list(
                item.get("evidence_refs"), f"{path}.evidence_refs", issues, allow_empty=False
            )
        else:
            evidence = []
        if status == "DONE" and not evidence:
            _issue(issues, "E_EVIDENCE_REQUIRED", path, "DONE object requires evidence_refs")

    for index, domain in enumerate(items("domains")):
        authority_value = domain.get("current_authority")
        if type(authority_value) is str and authority_value not in DOMAIN_AUTHORITY_VOCABULARY:
            _issue(
                issues,
                "E_AUTHORITY_INVALID",
                f"domains[{index}].current_authority",
                f"unknown authority value {authority_value}",
            )
        _validate_string_list(domain.get("wave_ids"), f"domains[{index}].wave_ids", issues, allow_empty=True)
    for index, wave in enumerate(items("waves")):
        authority_value = wave.get("authority_state")
        if type(authority_value) is str and authority_value not in WAVE_AUTHORITY_VOCABULARY:
            _issue(
                issues,
                "E_AUTHORITY_INVALID",
                f"waves[{index}].authority_state",
                f"unknown authority value {authority_value}",
            )
    for index, epic in enumerate(items("epics")):
        _validate_string_list(epic.get("domain_ids"), f"epics[{index}].domain_ids", issues, allow_empty=False)
    for collection in ("tasks", "work_units"):
        for index, item in enumerate(items(collection)):
            if item.get("non_operational") is not True:
                _issue(
                    issues,
                    "E_BOOTSTRAP_AUTHORITY",
                    f"{collection}[{index}].non_operational",
                    "bootstrap planning objects must remain non-operational",
                )

    if len(items("domains")) != 21:
        _issue(issues, "E_GRAPH_SHAPE", "domains", "must contain exactly 21 domains")
    if len(items("waves")) != 13:
        _issue(issues, "E_GRAPH_SHAPE", "waves", "must contain exactly 13 waves")
    if len(items("epics")) != 14:
        _issue(issues, "E_GRAPH_SHAPE", "epics", "must contain exactly 14 epics")

    waves = items("waves")
    wave_ids = {item.get("id") for item in waves if type(item.get("id")) is str}
    numbers = sorted(item.get("number") for item in waves if type(item.get("number")) is int)
    if numbers != list(range(13)):
        _issue(issues, "E_WAVE_NUMBERING", "waves", f"numbers must be exactly 0..12, got {numbers}")
    for index, wave in enumerate(waves):
        number = wave.get("number")
        if type(number) is int and wave.get("id") != f"W{number}":
            _issue(
                issues,
                "E_WAVE_NUMBERING",
                f"waves[{index}]",
                f"id must be W{number}",
            )

    domain_ids = {item.get("id") for item in items("domains") if type(item.get("id")) is str}
    epic_ids = {item.get("id") for item in items("epics") if type(item.get("id")) is str}
    capability_ids = {
        item.get("id") for item in items("capabilities") if type(item.get("id")) is str
    }
    task_ids = {item.get("id") for item in items("tasks") if type(item.get("id")) is str}

    for index, domain in enumerate(items("domains")):
        for wave_id in _validate_string_list(
            domain.get("wave_ids"), f"domains[{index}].wave_ids", [], allow_empty=True
        ):
            if wave_id not in wave_ids:
                _issue(
                    issues,
                    "E_REFERENCE_MISSING",
                    f"domains[{index}].wave_ids",
                    f"missing wave {wave_id}",
                )
    for index, epic in enumerate(items("epics")):
        epic_wave_id = epic.get("wave_id")
        if type(epic_wave_id) is not str or epic_wave_id not in wave_ids:
            _issue(
                issues,
                "E_REFERENCE_MISSING",
                f"epics[{index}].wave_id",
                f"missing wave {epic_wave_id}",
            )
        for domain_id in _validate_string_list(
            epic.get("domain_ids"), f"epics[{index}].domain_ids", [], allow_empty=True
        ):
            if domain_id not in domain_ids:
                _issue(
                    issues,
                    "E_REFERENCE_MISSING",
                    f"epics[{index}].domain_ids",
                    f"missing domain {domain_id}",
                )
    for index, capability in enumerate(items("capabilities")):
        capability_epic_id = capability.get("epic_id")
        if type(capability_epic_id) is not str or capability_epic_id not in epic_ids:
            _issue(
                issues,
                "E_REFERENCE_MISSING",
                f"capabilities[{index}].epic_id",
                f"missing epic {capability_epic_id}",
            )
    for index, task in enumerate(items("tasks")):
        task_capability_id = task.get("capability_id")
        if type(task_capability_id) is not str or task_capability_id not in capability_ids:
            _issue(
                issues,
                "E_REFERENCE_MISSING",
                f"tasks[{index}].capability_id",
                f"missing capability {task_capability_id}",
            )
    for index, work_unit in enumerate(items("work_units")):
        work_unit_task_id = work_unit.get("task_id")
        if type(work_unit_task_id) is not str or work_unit_task_id not in task_ids:
            _issue(
                issues,
                "E_REFERENCE_MISSING",
                f"work_units[{index}].task_id",
                f"missing task {work_unit_task_id}",
            )

    dependency_node_ids: set[str] = set()
    dependency_node_collection: dict[str, str] = {}
    for collection in DEPENDENCY_NODE_COLLECTIONS:
        for item in items(collection):
            item_id = item.get("id")
            if type(item_id) is str and item_id:
                dependency_node_ids.add(item_id)
                dependency_node_collection.setdefault(item_id, collection)

    adjacency: dict[str, list[str]] = {node_id: [] for node_id in dependency_node_ids}
    edge_metadata: dict[tuple[str, str], dict[str, Any]] = {}
    for index, dependency in enumerate(items("dependencies")):
        source = dependency.get("source_id")
        target = dependency.get("depends_on")
        pair = (source, target)
        if type(source) is str and type(target) is str:
            if pair in edge_metadata:
                _issue(
                    issues,
                    "E_DEPENDENCY_PAIR_DUPLICATE",
                    f"dependencies[{index}]",
                    f"duplicates dependency pair {source}->{target}",
                )
            else:
                edge_metadata[pair] = dependency
        dependency_type = dependency.get("dependency_type")
        if type(dependency_type) is str and dependency_type not in DEPENDENCY_TYPES:
            _issue(
                issues,
                "E_DEPENDENCY_TYPE_INVALID",
                f"dependencies[{index}].dependency_type",
                f"unknown dependency type {dependency_type}",
            )
        source_resolves = type(source) is str and source in dependency_node_ids
        target_resolves = type(target) is str and target in dependency_node_ids
        if not source_resolves:
            _issue(
                issues,
                "E_DEPENDENCY_SOURCE_MISSING",
                f"dependencies[{index}].source_id",
                f"unresolved source {source}",
            )
        if not target_resolves:
            _issue(
                issues,
                "E_DEPENDENCY_TARGET_MISSING",
                f"dependencies[{index}].depends_on",
                f"unresolved target {target}",
            )
        if source_resolves and target_resolves:
            source_collection = dependency_node_collection[source]
            target_collection = dependency_node_collection[target]
            expected_kind = (
                KIND_BY_COLLECTION[source_collection]
                if source_collection == target_collection
                else "CROSS_SCOPE"
            )
            if dependency.get("kind") != expected_kind:
                _issue(
                    issues,
                    "E_DEPENDENCY_KIND_INVALID",
                    f"dependencies[{index}].kind",
                    f"must be {expected_kind} for {source_collection}->{target_collection}",
                )
            adjacency[source].append(target)

    visiting: set[str] = set()
    visited: set[str] = set()
    reported_cycles: set[tuple[str, ...]] = set()

    def visit(node_id: str, path: list[str]) -> None:
        if node_id in visiting:
            start = path.index(node_id) if node_id in path else 0
            cycle = tuple(path[start:] + [node_id])
            if cycle not in reported_cycles:
                reported_cycles.add(cycle)
                _issue(issues, "E_DEPENDENCY_CYCLE", "dependencies", " -> ".join(cycle))
            return
        if node_id in visited:
            return
        visiting.add(node_id)
        path.append(node_id)
        for target in adjacency.get(node_id, []):
            visit(target, path)
        path.pop()
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in sorted(dependency_node_ids):
        visit(node_id, [])

    for pair, expected in MANDATORY_DEPENDENCIES.items():
        metadata = edge_metadata.get(pair)
        if metadata is None:
            _issue(
                issues,
                "E_MANDATORY_DEPENDENCY_MISSING",
                "dependencies",
                f"missing mandatory dependency {pair[0]}->{pair[1]}",
            )
        elif (metadata.get("kind"), metadata.get("dependency_type")) != expected:
            _issue(
                issues,
                "E_MANDATORY_DEPENDENCY_INVALID",
                "dependencies",
                f"{pair[0]}->{pair[1]} must be {expected[0]}/{expected[1]}",
            )

    lock_by_subject: dict[str, dict[str, Any]] = {}
    for index, lock in enumerate(items("locks")):
        subject = lock.get("subject")
        if type(subject) is not str:
            continue
        if subject in lock_by_subject:
            _issue(
                issues,
                "E_LOCK_SUBJECT_DUPLICATE",
                f"locks[{index}].subject",
                f"duplicate lock subject {subject}",
            )
        else:
            lock_by_subject[subject] = lock
    if set(lock_by_subject) != set(REQUIRED_LOCKS):
        _issue(
            issues,
            "E_LOCK_SUBJECT_SET",
            "locks",
            "lock subjects must exactly match the required factory and capital locks",
        )
    for subject, (expected_id, expected_status, expected_locked) in REQUIRED_LOCKS.items():
        lock = lock_by_subject.get(subject)
        if lock is None:
            continue
        if (
            lock.get("id") != expected_id
            or lock.get("status") != expected_status
            or lock.get("locked") is not expected_locked
        ):
            _issue(
                issues,
                "E_LOCK_STATE",
                f"locks.{subject}",
                f"must be id={expected_id}, status={expected_status}, locked={expected_locked}",
            )

    gate_by_subject: dict[str, dict[str, Any]] = {}
    for index, gate in enumerate(items("authority_gates")):
        subject = gate.get("subject")
        if type(subject) is not str:
            continue
        if subject in gate_by_subject:
            _issue(
                issues,
                "E_GATE_SUBJECT_DUPLICATE",
                f"authority_gates[{index}].subject",
                f"duplicate authority gate subject {subject}",
            )
        else:
            gate_by_subject[subject] = gate
    if set(gate_by_subject) != set(REQUIRED_GATES):
        _issue(
            issues,
            "E_GATE_SUBJECT_SET",
            "authority_gates",
            "authority gate subjects must exactly match Paper, Limited Live and Live",
        )
    for subject, expected_id in REQUIRED_GATES.items():
        gate = gate_by_subject.get(subject)
        if gate is None:
            continue
        if (
            gate.get("id") != expected_id
            or gate.get("status") != "LOCKED"
            or gate.get("locked") is not True
            or gate.get("owner_required") is not True
            or gate.get("grants_authority") is not False
        ):
            _issue(
                issues,
                "E_GATE_STATE",
                f"authority_gates.{subject}",
                "must remain locked, Owner-required and non-granting",
            )

    factory_by_id = {
        item.get("id"): item
        for item in items("factory_autonomy")
        if type(item.get("id")) is str
    }
    if set(factory_by_id) != set(REQUIRED_FACTORY_STAGES):
        _issue(
            issues,
            "E_FACTORY_STAGE_SET",
            "factory_autonomy",
            "must exactly contain FACTORY-001A through FACTORY-001E",
        )
    for stage, (expected_status, expected_locked) in REQUIRED_FACTORY_STAGES.items():
        item = factory_by_id.get(stage)
        if item is None:
            continue
        if item.get("status") != expected_status or item.get("locked") is not expected_locked:
            _issue(
                issues,
                "E_FACTORY_STATE",
                f"factory_autonomy.{stage}",
                f"must be status={expected_status}, locked={expected_locked}",
            )
        if stage != "FACTORY-001A":
            lock = lock_by_subject.get(stage)
            if lock is not None and (
                lock.get("status") != item.get("status") or lock.get("locked") is not item.get("locked")
            ):
                _issue(
                    issues,
                    "E_FACTORY_LOCK_MISMATCH",
                    f"factory_autonomy.{stage}",
                    "factory stage and lock record must agree",
                )

    baseline = tables.get("baseline", {})
    if baseline:
        if (
            baseline.get("id") != "BASELINE-FACTORY-001A-ACCEPTED"
            or baseline.get("status") != "DONE"
            or baseline.get("git_head") != EXPECTED_HEAD
            or baseline.get("source_branch") != "feature/factory-001a-control-plane"
        ):
            _issue(
                issues,
                "E_BASELINE_STATE",
                "baseline",
                "must represent the accepted FACTORY-001A source baseline at the exact HEAD",
            )
    factory_a = factory_by_id.get("FACTORY-001A")
    if factory_a is not None:
        factory_a_evidence = factory_a.get("evidence_refs")
        has_exact_head = (
            type(factory_a_evidence) is list
            and all(type(reference) is str for reference in factory_a_evidence)
            and any(EXPECTED_HEAD in reference for reference in factory_a_evidence)
        )
        if not has_exact_head:
            _issue(
                issues,
                "E_BASELINE_EVIDENCE",
                "factory_autonomy.FACTORY-001A.evidence_refs",
                "must reference the exact accepted HEAD",
            )

    by_id = {
        item.get("id"): item
        for name in ("domains", "waves", "epics", "capabilities")
        for item in items(name)
        if type(item.get("id")) is str
    }
    required_locked_objects = {
        "W7": {"status": "LOCKED", "authority_state": "NEEDS_OWNER"},
        "W8": {"status": "LOCKED", "authority_state": "NEEDS_OWNER_LIVE_GATE"},
        "EPIC-W7-PAPER": {"status": "LOCKED"},
        "EPIC-W8-LIMITED-LIVE": {"status": "LOCKED"},
        "CAP-W7-PAPER-ENVIRONMENT": {"status": "LOCKED"},
        "CAP-W8-LIMITED-LIVE-ENVIRONMENT": {"status": "LOCKED"},
        "DOM-PORTFOLIO-HQ": {"status": "LOCKED", "current_authority": "CAPITAL_LOCKED"},
        "DOM-OPERATIONS-CENTER": {"status": "LOCKED", "current_authority": "CAPITAL_LOCKED"},
    }
    for object_id, expected_fields in required_locked_objects.items():
        item = by_id.get(object_id)
        if item is None or any(item.get(field) != expected for field, expected in expected_fields.items()):
            expected_description = ", ".join(
                f"{field}={expected}" for field, expected in expected_fields.items()
            )
            _issue(
                issues,
                "E_AUTHORITY_CROSS_FIELD",
                object_id,
                f"must remain {expected_description}",
            )

    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_BOOTSTRAP)
    args = parser.parse_args()
    try:
        data = load_bootstrap(args.path)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        print(f"PRODUCT_GRAPH_BOOTSTRAP: FAIL\n- [E_TOML_PARSE] {args.path}: {exc}", file=sys.stderr)
        return 1

    try:
        issues = validate_graph(data)
    except Exception as exc:  # Fail closed without a malformed-input traceback.
        print(
            "PRODUCT_GRAPH_BOOTSTRAP: FAIL\n"
            f"- [E_VALIDATOR_INTERNAL] validation: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1
    if issues:
        print("PRODUCT_GRAPH_BOOTSTRAP: FAIL", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1

    print(
        "PRODUCT_GRAPH_BOOTSTRAP: PASS "
        f"domains={len(data['domains'])} "
        f"waves={len(data['waves'])} "
        f"epics={len(data['epics'])} "
        f"dependencies={len(data['dependencies'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
