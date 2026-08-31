"""Minimal in-process reader for validated Product Graph snapshots."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import Any, Mapping, TypeAlias

from scripts.check_product_graph_bootstrap import validate_graph


class ProductGraphValidationError(ValueError):
    """Raised when snapshot data violates the Product Graph contract."""


class ProductGraphNotFound(KeyError):
    """Raised when a requested graph object ID does not exist."""


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    owner_model: str
    status: str
    north_star: str
    cycle: tuple[str, ...]


@dataclass(frozen=True)
class Domain:
    id: str
    title: str
    status: str
    current_authority: str
    wave_ids: tuple[str, ...]


@dataclass(frozen=True)
class Wave:
    id: str
    number: int
    title: str
    status: str
    authority_state: str
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class Epic:
    id: str
    wave_id: str
    title: str
    status: str
    domain_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class Dependency:
    id: str
    source_id: str
    depends_on: str
    kind: str
    dependency_type: str


@dataclass(frozen=True)
class Lock:
    id: str
    subject: str
    status: str
    locked: bool
    reason: str


GraphObject: TypeAlias = Product | Domain | Wave | Epic | Dependency | Lock
StatusObject: TypeAlias = Product | Domain | Wave | Epic | Lock


class ProductGraph:
    """Immutable query view over a validated, non-operational graph snapshot."""

    def __init__(self, data: dict[str, Any], *, source_path: Path | None) -> None:
        product = data["product"]
        self._product = Product(
            id=product["id"],
            name=product["name"],
            owner_model=product["owner_model"],
            status=product["status"],
            north_star=product["north_star"],
            cycle=tuple(product["cycle"]),
        )
        self._domains = tuple(
            Domain(
                id=item["id"],
                title=item["title"],
                status=item["status"],
                current_authority=item["current_authority"],
                wave_ids=tuple(item["wave_ids"]),
            )
            for item in data["domains"]
        )
        self._waves = tuple(
            Wave(
                id=item["id"],
                number=item["number"],
                title=item["title"],
                status=item["status"],
                authority_state=item["authority_state"],
                evidence_refs=tuple(item.get("evidence_refs", ())),
            )
            for item in data["waves"]
        )
        self._epics = tuple(
            Epic(
                id=item["id"],
                wave_id=item["wave_id"],
                title=item["title"],
                status=item["status"],
                domain_ids=tuple(item["domain_ids"]),
                evidence_refs=tuple(item.get("evidence_refs", ())),
            )
            for item in data["epics"]
        )
        self._dependencies = tuple(
            Dependency(
                id=item["id"],
                source_id=item["source_id"],
                depends_on=item["depends_on"],
                kind=item["kind"],
                dependency_type=item["dependency_type"],
            )
            for item in data["dependencies"]
        )
        self._locks = tuple(
            Lock(
                id=item["id"],
                subject=item["subject"],
                status=item["status"],
                locked=item["locked"],
                reason=item["reason"],
            )
            for item in data["locks"]
        )
        objects: tuple[GraphObject, ...] = (
            (self._product,)
            + self._domains
            + self._waves
            + self._epics
            + self._dependencies
            + self._locks
        )
        self._by_id = {item.id: item for item in objects}
        self._status_objects: tuple[StatusObject, ...] = (
            (self._product,) + self._domains + self._waves + self._epics + self._locks
        )
        self._capital_authority = data["authority"]["capital_authority"]
        self.source_path = source_path
        self.source_classification = data["classification"]
        self.source_operational = data["operational"]
        self.source_writable_runtime_truth = data["writable_runtime_truth"]

    @classmethod
    def load(cls, source: str | Path | Mapping[str, Any]) -> ProductGraph:
        """Load and validate a TOML path or an in-memory snapshot mapping."""

        source_path: Path | None = None
        if isinstance(source, (str, Path)):
            source_path = Path(source)
            try:
                with source_path.open("rb") as handle:
                    data = tomllib.load(handle)
            except (OSError, tomllib.TOMLDecodeError) as exc:
                raise ProductGraphValidationError(f"cannot load Product Graph: {exc}") from exc
        elif isinstance(source, Mapping):
            data = deepcopy(dict(source))
        else:
            raise TypeError("source must be a TOML path or mapping")

        try:
            issues = validate_graph(data)
        except Exception as exc:  # The graph reader fails closed on malformed validator input.
            raise ProductGraphValidationError(
                f"Product Graph validation failed internally: {type(exc).__name__}: {exc}"
            ) from exc
        if issues:
            detail = "; ".join(str(issue) for issue in issues)
            raise ProductGraphValidationError(f"invalid Product Graph: {detail}")
        return cls(data, source_path=source_path)

    @property
    def product(self) -> Product:
        return self._product

    @property
    def capital_authority(self) -> bool:
        return self._capital_authority

    @property
    def is_read_only_snapshot(self) -> bool:
        return (
            self.source_classification == "NON_OPERATIONAL_PRODUCT_GRAPH_BOOTSTRAP"
            and not self.source_operational
            and not self.source_writable_runtime_truth
        )

    def get(self, object_id: str) -> GraphObject:
        try:
            return self._by_id[object_id]
        except KeyError as exc:
            raise ProductGraphNotFound(object_id) from exc

    def domains(self) -> tuple[Domain, ...]:
        return self._domains

    def waves(self) -> tuple[Wave, ...]:
        return self._waves

    def epics(self) -> tuple[Epic, ...]:
        return self._epics

    def by_status(self, status: str) -> tuple[StatusObject, ...]:
        return tuple(item for item in self._status_objects if item.status == status)

    def dependencies(self, object_id: str) -> tuple[Dependency, ...]:
        self.get(object_id)
        return tuple(item for item in self._dependencies if item.source_id == object_id)

    def dependents(self, object_id: str) -> tuple[Dependency, ...]:
        self.get(object_id)
        return tuple(item for item in self._dependencies if item.depends_on == object_id)

    def locked(self) -> tuple[StatusObject, ...]:
        return tuple(
            item
            for item in self._status_objects
            if item.status == "LOCKED" or (isinstance(item, Lock) and item.locked)
        )

    def current_wave(self) -> Wave | None:
        active = tuple(wave for wave in self._waves if wave.status == "ACTIVE")
        if active:
            return active[0] if len(active) == 1 else None

        completed = {wave.id for wave in self._waves if wave.status == "DONE"}
        frontier = tuple(
            wave
            for wave in self._waves
            if wave.id in completed
            and not any(
                dependency.kind == "WAVE"
                and dependency.depends_on == wave.id
                and dependency.source_id in completed
                for dependency in self._dependencies
            )
        )
        return frontier[0] if len(frontier) == 1 else None

    def next_wave(self) -> Wave | None:
        waves_by_id = {wave.id: wave for wave in self._waves}
        candidates: list[Wave] = []
        for wave in self._waves:
            if wave.status not in {"READY", "PLANNED"}:
                continue
            readiness = tuple(
                dependency
                for dependency in self._dependencies
                if dependency.kind == "WAVE"
                and dependency.dependency_type == "READINESS"
                and dependency.source_id == wave.id
            )
            if readiness and all(
                waves_by_id[dependency.depends_on].status == "DONE"
                for dependency in readiness
            ):
                candidates.append(wave)
        return candidates[0] if len(candidates) == 1 else None
