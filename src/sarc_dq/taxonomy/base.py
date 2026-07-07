"""Generalized corruption-injector framework (taxonomy v0, Phase 1).

This is the *generalized* successor to the frozen Phase 0 injector
(``sarc_dq.injectors``, which is extend-only and untouched). Every corruption
class declares (brief §5):

- ``channel`` — ``payload-visible`` | ``metadata-borne`` (load-bearing for H2);
- ``site`` — which field / record the corruption attacks;
- ``default_rate`` — the class's default injection rate (fraction of episodes),
  a scaffolding default the human revises;

and produces an :class:`InjectionResult`: the (possibly modified) primary record,
zero or more *companion* records (some defects — duplicates, cross-source
contradictions, superseded goldens — are multi-record by nature), and a
**ground-truth tag** written to the run log and never shown to any agent, critic,
judge, or gate.

Taxonomy v0 is explicitly *scaffolding for human revision* — see
``reports/TAXONOMY_V0.md``. It is not the intellectual contribution.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from sarc_dq.records import EvidenceRecord
from sarc_dq.substrate import Episode

CHANNELS = ("payload-visible", "metadata-borne")


@dataclass(frozen=True)
class InjectionResult:
    """What a corruption class produced for one episode.

    ``primary`` is the record the agent's decision keys on (the corrupted price).
    ``companions`` are additional records that make some defects visible (a
    duplicate vendor row, a contradicting second source, a superseded golden).
    The full evidence set the DQ gate evaluates is ``[primary, *companions]``.
    """

    primary: EvidenceRecord
    companions: tuple[EvidenceRecord, ...] = ()
    ground_truth: dict[str, Any] = field(default_factory=dict)

    def evidence_set(self) -> tuple[EvidenceRecord, ...]:
        return (self.primary, *self.companions)


@runtime_checkable
class CorruptionClass(Protocol):
    """A named corruption with a declared detection channel and injection site."""

    @property
    def name(self) -> str: ...

    @property
    def channel(self) -> str: ...

    @property
    def site(self) -> str: ...

    @property
    def default_rate(self) -> float: ...

    def inject(
        self, record: EvidenceRecord, episode: Episode, rng: random.Random
    ) -> InjectionResult:
        """Return an :class:`InjectionResult` with a ground-truth tag set."""
        ...


_REGISTRY: dict[str, CorruptionClass] = {}


def register(cls: CorruptionClass) -> CorruptionClass:
    """Register a corruption class by ``name`` (validates channel)."""
    if cls.channel not in CHANNELS:
        raise ValueError(f"{cls.name}: channel {cls.channel!r} not in {CHANNELS}")
    _REGISTRY[cls.name] = cls
    return cls


def get(name: str) -> CorruptionClass:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(f"unknown corruption class {name!r}; registered: {registered()}") from None


def registered() -> list[str]:
    return sorted(_REGISTRY)


def base_ground_truth(cls: CorruptionClass, **extra: Any) -> dict[str, Any]:
    """Common ground-truth fields every class stamps, plus class-specific extras."""
    return {"corrupted": True, "corruption_class": cls.name, "channel": cls.channel, **extra}
