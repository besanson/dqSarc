"""DQ constraint-spec loader + evaluator (sarc-governance style).

Loads the YAML constraint spec (``specs/dq_predicates.yaml`` by default) into typed
:class:`Constraint` objects, resolving each ``predicate.name`` against the
:mod:`sarc_dq.dq_predicates` registry — **no ``eval``/``exec``**, names only. The
spec is parameterized, so a taxonomy revision is a YAML edit.

Requires PyYAML (the ``[gate]`` extra); the Phase 0 zero-dependency core never
imports this module.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

from sarc_dq import dq_predicates
from sarc_dq.records import EvidenceRecord

CLASSES = ("hard", "soft", "escalation")
VERIF_POINTS = ("PAG", "AATM", "PAA")
RESPONSES = ("block", "degrade", "escalate", "quarantine_substitute")


@dataclass(frozen=True)
class Constraint:
    id: str
    cls: str  # hard | soft | escalation
    verif: str  # PAG | AATM | PAA
    response: str  # block | degrade | escalate | quarantine_substitute
    predicate: str
    params: dict[str, Any]
    operating_point: Any
    targets: tuple[str, ...]
    description: str

    def evaluate(self, evidence: Sequence[EvidenceRecord]) -> dq_predicates.PredicateResult:
        return dq_predicates.get(self.predicate)(evidence, self.params)


@dataclass(frozen=True)
class ConstraintSpec:
    constraints: tuple[Constraint, ...]

    def by_verif(self, point: str) -> tuple[Constraint, ...]:
        return tuple(c for c in self.constraints if c.verif == point)

    def evaluate(
        self, evidence: Sequence[EvidenceRecord], *, verif: str | None = None
    ) -> list[tuple[Constraint, dq_predicates.PredicateResult]]:
        """Evaluate all constraints (optionally only those at a verification point)."""
        chosen = self.constraints if verif is None else self.by_verif(verif)
        return [(c, c.evaluate(evidence)) for c in chosen]


def _parse(raw: dict[str, Any]) -> ConstraintSpec:
    items = raw.get("constraints")
    if not isinstance(items, list) or not items:
        raise ValueError("spec must contain a non-empty 'constraints' list")
    out: list[Constraint] = []
    for i, item in enumerate(items):
        pred = item.get("predicate", {})
        c = Constraint(
            id=str(item["id"]),
            cls=str(item["class"]),
            verif=str(item["verif"]),
            response=str(item["response"]),
            predicate=str(pred["name"]),
            params=dict(pred.get("params") or {}),
            operating_point=item.get("operating_point"),
            targets=tuple(item.get("targets", ())),
            description=str(item.get("description", "")).strip(),
        )
        _validate(c, i)
        out.append(c)
    return ConstraintSpec(tuple(out))


def _validate(c: Constraint, i: int) -> None:
    where = f"constraint[{i}] id={c.id!r}"
    if c.cls not in CLASSES:
        raise ValueError(f"{where}: class {c.cls!r} not in {CLASSES}")
    if c.verif not in VERIF_POINTS:
        raise ValueError(f"{where}: verif {c.verif!r} not in {VERIF_POINTS}")
    if c.response not in RESPONSES:
        raise ValueError(f"{where}: response {c.response!r} not in {RESPONSES}")
    if c.predicate not in dq_predicates.registered():
        raise ValueError(f"{where}: unknown predicate {c.predicate!r}")


def _load_yaml(text: str) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("DQ spec loading needs PyYAML: pip install 'sarc-dq[gate]'") from exc
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("spec root must be a mapping")
    return data


def load_spec(source: str | Path | None = None) -> ConstraintSpec:
    """Load a ConstraintSpec from a YAML path, or the packaged default spec."""
    if source is None:
        text = resources.files("sarc_dq.specs").joinpath("dq_predicates.yaml").read_text("utf-8")
    else:
        text = Path(source).read_text("utf-8")
    return _parse(_load_yaml(text))
