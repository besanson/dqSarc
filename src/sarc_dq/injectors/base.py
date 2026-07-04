"""Injector framework: corruption classes that declare a detection channel.

Each corruption class declares (brief §5):

- ``channel`` — ``payload-visible`` (detectable from record content alone) or
  ``metadata-borne`` (detectable only from freshness / lineage / provenance).
  This tag is load-bearing for H2 (detection asymmetry).
- an ``inject`` operation that transforms a clean record into a corrupted one and
  writes a **ground-truth tag** into the record's ``ground_truth`` (brief §5:
  "a ground-truth tag written to the run log"). The tag is never shown to any
  agent, critic, judge, or gate.

Phase 0 uses exactly one class (``stale_unit_price``). The full taxonomy v0 is a
Phase 1 deliverable behind the next hard-stop gate, so this framework is kept
minimal-but-extensible: register a class, and the harness can drive it.
"""

from __future__ import annotations

import random
from typing import Protocol, runtime_checkable

from sarc_dq.records import EvidenceRecord
from sarc_dq.substrate import Episode

# A channel is one of these two literals; kept as a module constant tuple so the
# harness can assert a class tags itself with a legal value.
CHANNELS = ("payload-visible", "metadata-borne")


@runtime_checkable
class CorruptionClass(Protocol):
    """A named corruption with a declared detection channel.

    ``name`` and ``channel`` are read-only so a frozen-dataclass corruption class
    (with immutable fields) satisfies the protocol.
    """

    @property
    def name(self) -> str: ...

    @property
    def channel(self) -> str: ...

    def inject(
        self, record: EvidenceRecord, episode: Episode, rng: random.Random
    ) -> EvidenceRecord:
        """Return a corrupted copy of ``record`` with a ground-truth tag set."""
        ...


_REGISTRY: dict[str, CorruptionClass] = {}


def register(cls: CorruptionClass) -> CorruptionClass:
    """Register a corruption class by its ``name`` (raises on a bad channel)."""
    if cls.channel not in CHANNELS:
        raise ValueError(f"{cls.name}: channel {cls.channel!r} not in {CHANNELS}")
    _REGISTRY[cls.name] = cls
    return cls


def get(name: str) -> CorruptionClass:
    """Look up a registered corruption class by name."""
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(
            f"unknown corruption class {name!r}; registered: {sorted(_REGISTRY)}"
        ) from None


def registered() -> list[str]:
    """Names of all registered corruption classes."""
    return sorted(_REGISTRY)
