"""Injector framework + the stale-price class."""

from __future__ import annotations

import random

from sarc_dq.injectors import STALE_UNIT_PRICE, get, registered
from sarc_dq.injectors.base import CHANNELS
from sarc_dq.substrate import make_episode


def test_stale_price_registered_with_legal_channel() -> None:
    assert "stale_unit_price" in registered()
    assert get("stale_unit_price").channel in CHANNELS
    assert STALE_UNIT_PRICE.channel == "metadata-borne"


def test_injection_sets_ground_truth_and_ages_metadata() -> None:
    ep = make_episode(seed=5, index=0)
    clean = ep.clean_price_record()
    corrupt = STALE_UNIT_PRICE.inject(clean, ep, random.Random(5))

    assert corrupt.ground_truth["corrupted"] is True
    assert corrupt.ground_truth["corruption_class"] == "stale_unit_price"
    assert corrupt.ground_truth["channel"] == "metadata-borne"
    # Metadata reveals the staleness ...
    assert 90 <= corrupt.metadata.age_days <= 180
    assert corrupt.metadata.as_of_day < corrupt.metadata.retrieved_day
    # ... but the clean record is fresh.
    assert clean.metadata.age_days == 0


def test_payload_view_hides_staleness() -> None:
    """The payload alone must be indistinguishable from a fresh price (metadata-borne)."""
    ep = make_episode(seed=11, index=0)
    clean = ep.clean_price_record()
    corrupt = STALE_UNIT_PRICE.inject(clean, ep, random.Random(11))
    # Same keys, same plausible shape; only the value differs — no freshness leak.
    assert set(corrupt.payload_view()) == set(clean.payload_view())
    assert "as_of" not in corrupt.payload_view()
    assert corrupt.payload["unit_cost"] > 0


def test_injection_is_deterministic() -> None:
    ep = make_episode(seed=3, index=0)
    clean = ep.clean_price_record()
    a = STALE_UNIT_PRICE.inject(clean, ep, random.Random(77))
    b = STALE_UNIT_PRICE.inject(clean, ep, random.Random(77))
    assert a.payload == b.payload
    assert a.metadata == b.metadata
