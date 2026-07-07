"""Taxonomy v0: registration, channels, ground-truth tags, determinism."""

from __future__ import annotations

import random

from sarc_dq.substrate import make_episode
from sarc_dq.taxonomy import CHANNELS, TAXONOMY_V0, get, registered
from sarc_dq.taxonomy.base import InjectionResult


def test_eight_classes_registered_with_legal_channels() -> None:
    names = registered()
    assert len(names) == 8
    assert "stale_master_data" in names
    for cls in TAXONOMY_V0:
        assert cls.channel in CHANNELS
        assert get(cls.name) is cls
        assert 0.0 < cls.default_rate <= 1.0


def test_every_class_stamps_ground_truth() -> None:
    ep = make_episode(5, 0)
    clean = ep.clean_price_record()
    for cls in TAXONOMY_V0:
        res = cls.inject(clean, ep, random.Random(11))
        assert isinstance(res, InjectionResult)
        gt = res.ground_truth
        assert gt["corrupted"] is True
        assert gt["corruption_class"] == cls.name
        assert gt["channel"] == cls.channel
        assert gt["true_unit_cost"] == clean.payload["unit_cost"]
        # Evidence set always contains at least the primary record.
        assert res.evidence_set()[0] is res.primary


def test_injection_is_deterministic() -> None:
    ep = make_episode(3, 0)
    clean = ep.clean_price_record()
    for cls in TAXONOMY_V0:
        a = cls.inject(clean, ep, random.Random(99))
        b = cls.inject(clean, ep, random.Random(99))
        assert a.primary.payload == b.primary.payload
        assert a.primary.metadata == b.primary.metadata
        assert [c.payload for c in a.companions] == [c.payload for c in b.companions]


def test_multi_record_classes_emit_companions() -> None:
    ep = make_episode(8, 0)
    clean = ep.clean_price_record()
    for name in (
        "superseded_golden_record",
        "duplicate_vendor_conflicting_terms",
        "cross_source_contradiction",
    ):
        res = get(name).inject(clean, ep, random.Random(1))
        assert len(res.companions) >= 1, name


def test_metadata_borne_payload_looks_plausible() -> None:
    """A metadata-borne defect must not betray itself in the payload value alone."""
    ep = make_episode(4, 0)
    clean = ep.clean_price_record()
    res = get("plausible_outlier").inject(clean, ep, random.Random(2))
    # In-range, positive, still a float in the same band — nothing lexically off.
    v = res.primary.payload["unit_cost"]
    assert isinstance(v, float) and 8.0 <= v <= 22.0
