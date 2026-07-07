"""DQ predicate spec: loading, validation, and taxonomy↔predicate detection."""

from __future__ import annotations

import random

import pytest

from sarc_dq.dq_spec import Constraint, load_spec
from sarc_dq.substrate import make_episode
from sarc_dq.taxonomy import get


def test_spec_loads_and_resolves_predicates() -> None:
    spec = load_spec()
    ids = [c.id for c in spec.constraints]
    assert "c_freshness" in ids and "c_complete" in ids
    for c in spec.constraints:
        assert isinstance(c, Constraint)
        assert c.cls in ("hard", "soft", "escalation")
        assert c.verif in ("PAG", "AATM", "PAA")
        assert c.response in ("block", "degrade", "escalate", "quarantine_substitute")


def test_clean_evidence_passes_every_constraint() -> None:
    spec = load_spec()
    ep = make_episode(123, 0)
    results = spec.evaluate([ep.clean_price_record()])
    assert all(r.passed for _, r in results)


# The five taxonomy-v0 classes with clear v0 predicate coverage → the constraint
# that must fail on them. (silent_unit_change, duplicate_vendor_conflicting_terms,
# and plausible_outlier are known v0 gaps — see TAXONOMY_REVISION_GUIDE.md.)
_DETECTION = {
    "stale_master_data": "c_freshness",
    "superseded_golden_record": "c_golden_unique",
    "cross_source_contradiction": "c_cross_source",
    "schema_drift": "c_schema",
    "missing_mandatory_field": "c_complete",
}


@pytest.mark.parametrize("cls_name,constraint_id", list(_DETECTION.items()))
def test_predicate_detects_its_target_class(cls_name: str, constraint_id: str) -> None:
    spec = load_spec()
    ep = make_episode(42, 0)
    injected = get(cls_name).inject(ep.clean_price_record(), ep, random.Random(7))
    failing = {c.id for c, r in spec.evaluate(injected.evidence_set()) if not r.passed}
    assert constraint_id in failing, f"{cls_name}: expected {constraint_id} to fire, got {failing}"


def test_spec_rejects_unknown_predicate() -> None:
    from sarc_dq.dq_spec import _parse

    bad = {
        "constraints": [
            {
                "id": "x",
                "class": "hard",
                "verif": "PAG",
                "response": "block",
                "predicate": {"name": "nope"},
            }
        ]
    }
    with pytest.raises(ValueError, match="unknown predicate"):
        _parse(bad)


def test_spec_rejects_bad_enum() -> None:
    from sarc_dq.dq_spec import _parse

    bad = {
        "constraints": [
            {
                "id": "x",
                "class": "HARD",
                "verif": "PAG",
                "response": "block",
                "predicate": {"name": "lineage_present"},
            }
        ]
    }
    with pytest.raises(ValueError, match="class"):
        _parse(bad)
