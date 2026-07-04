"""Corruption injector framework (brief §5) and the Phase 0 class registry."""

from __future__ import annotations

from sarc_dq.injectors.base import (
    CHANNELS,
    CorruptionClass,
    get,
    register,
    registered,
)
from sarc_dq.injectors.stale_price import STALE_UNIT_PRICE, StaleUnitPrice

# Register the single Phase 0 class. Taxonomy v0 (the remaining classes) is a
# Phase 1 deliverable gated behind the next hard stop, and lands here.
register(STALE_UNIT_PRICE)

__all__ = [
    "CHANNELS",
    "CorruptionClass",
    "StaleUnitPrice",
    "STALE_UNIT_PRICE",
    "get",
    "register",
    "registered",
]
