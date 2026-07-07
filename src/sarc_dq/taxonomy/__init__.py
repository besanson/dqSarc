"""Generalized corruption taxonomy (v0) — framework + registered classes."""

from __future__ import annotations

from sarc_dq.taxonomy.base import (
    CHANNELS,
    CorruptionClass,
    InjectionResult,
    get,
    register,
    registered,
)
from sarc_dq.taxonomy.classes import TAXONOMY_V0

for _cls in TAXONOMY_V0:
    register(_cls)

__all__ = [
    "CHANNELS",
    "CorruptionClass",
    "InjectionResult",
    "TAXONOMY_V0",
    "get",
    "register",
    "registered",
]
