"""DQ predicate family — the evaluable core the YAML spec references by name.

Six predicates (brief §5), each **parameterized** so a taxonomy revision edits the
YAML spec, not this module:

- ``freshness(max_age_days)``          — every record is younger than max_age_days
- ``lineage_present``                  — every record carries provenance (a source)
- ``golden_record_unique``             — no superseded version readable alongside the current one
- ``cross_source_consistent(tolerance)`` — same key from different sources agrees within tolerance
- ``schema_conformant(fields)``        — the site field is present with the expected type
- ``complete(required_fields)``        — all mandatory fields present

Each predicate takes the action's **evidence set** (the records it relied on) plus
its YAML ``params`` and returns a :class:`PredicateResult`. Pure stdlib; the
predicates never mutate records and never touch source stores.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from sarc_dq.records import EvidenceRecord

PredicateFn = Callable[[Sequence[EvidenceRecord], dict[str, Any]], "PredicateResult"]


@dataclass(frozen=True)
class PredicateResult:
    predicate: str
    passed: bool
    detail: str
    offending: tuple[str, ...] = ()  # record ids that violated, if any


_REGISTRY: dict[str, PredicateFn] = {}


def register(name: str) -> Callable[[PredicateFn], PredicateFn]:
    def deco(fn: PredicateFn) -> PredicateFn:
        _REGISTRY[name] = fn
        return fn

    return deco


def get(name: str) -> PredicateFn:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(f"unknown predicate {name!r}; registered: {sorted(_REGISTRY)}") from None


def registered() -> list[str]:
    return sorted(_REGISTRY)


# --- the six predicates ----------------------------------------------------


@register("freshness")
def freshness(evidence: Sequence[EvidenceRecord], params: dict[str, Any]) -> PredicateResult:
    max_age = int(params["max_age_days"])
    stale = [r.record_id for r in evidence if r.metadata.age_days > max_age]
    return PredicateResult(
        "freshness",
        not stale,
        f"max_age_days={max_age}; {len(stale)} record(s) older"
        if stale
        else f"all within {max_age}d",
        tuple(stale),
    )


@register("lineage_present")
def lineage_present(evidence: Sequence[EvidenceRecord], params: dict[str, Any]) -> PredicateResult:
    missing = [r.record_id for r in evidence if not r.metadata.source]
    return PredicateResult(
        "lineage_present",
        not missing,
        "provenance present on all records" if not missing else f"{len(missing)} lack a source",
        tuple(missing),
    )


@register("golden_record_unique")
def golden_record_unique(
    evidence: Sequence[EvidenceRecord], params: dict[str, Any]
) -> PredicateResult:
    versions: dict[str, set[int]] = {}
    for r in evidence:
        versions.setdefault(r.record_id, set()).add(r.metadata.version)
    conflicts = [rid for rid, vs in versions.items() if len(vs) > 1]
    return PredicateResult(
        "golden_record_unique",
        not conflicts,
        "one version per record" if not conflicts else f"{len(conflicts)} key(s) with >1 version",
        tuple(conflicts),
    )


@register("cross_source_consistent")
def cross_source_consistent(
    evidence: Sequence[EvidenceRecord], params: dict[str, Any]
) -> PredicateResult:
    tol = float(params.get("tolerance", 0.02))
    field = str(params.get("field", "unit_cost"))
    by_key: dict[str, list[float]] = {}
    for r in evidence:
        val = r.payload.get(field)
        if isinstance(val, (int, float)):
            by_key.setdefault(r.record_id, []).append(float(val))
    bad = []
    for rid, vals in by_key.items():
        if len(vals) >= 2:
            lo, hi = min(vals), max(vals)
            if lo > 0 and (hi - lo) / lo > tol:
                bad.append(rid)
    return PredicateResult(
        "cross_source_consistent",
        not bad,
        f"tolerance={tol}; {len(bad)} key(s) disagree" if bad else f"agree within {tol}",
        tuple(bad),
    )


@register("schema_conformant")
def schema_conformant(
    evidence: Sequence[EvidenceRecord], params: dict[str, Any]
) -> PredicateResult:
    # params.fields: {name: "float"|"int"|"str"} expected on every record's payload.
    fields: dict[str, str] = dict(params["fields"])
    types = {"float": (int, float), "int": (int,), "str": (str,)}
    bad = []
    for r in evidence:
        for fname, ftype in fields.items():
            val = r.payload.get(fname, _MISSING)
            if val is _MISSING or not isinstance(val, types[ftype]):
                bad.append(r.record_id)
                break
    return PredicateResult(
        "schema_conformant",
        not bad,
        "site fields present + typed" if not bad else f"{len(bad)} record(s) off-schema",
        tuple(bad),
    )


@register("complete")
def complete(evidence: Sequence[EvidenceRecord], params: dict[str, Any]) -> PredicateResult:
    required = list(params["required_fields"])
    bad = [r.record_id for r in evidence if any(f not in r.payload for f in required)]
    return PredicateResult(
        "complete",
        not bad,
        f"required={required}" + ("" if not bad else f"; {len(bad)} incomplete"),
        tuple(bad),
    )


_MISSING = object()
