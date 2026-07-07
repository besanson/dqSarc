"""DQ Pre-Action Gate (arm D) + the governed substitute buffer.

The gate evaluates the Part-1 predicate spec over the **evidence set** at the
point of action and takes the constraint's response protocol:

- ``block``                — the action is refused (no execution);
- ``degrade``              — autonomy is degraded to a conservative default;
- ``escalate``             — routed to a human (no autonomous execution);
- ``quarantine_substitute`` — the offending value is quarantined and a known-good
  value is substituted **from the governed buffer** — a downstream, versioned
  store keyed by content-addressed evidence IDs. **The gate never writes to any
  source store.** Every admitted action logs the versioned evidence set it relied
  on (Proposition 1: lineage preservation).

The gate does **not** read ground truth; it uses only the records and the buffer.
The buffer is seeded (in experiments) with governed last-known-good values,
representing a clean downstream cache — the "downstream-only remediation" design.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from sarc_dq.dq_spec import ConstraintSpec, load_spec
from sarc_dq.records import EvidenceRecord

# Response-protocol precedence: the most restrictive fired response wins.
_PRECEDENCE = {"quarantine_substitute": 0, "block": 1, "escalate": 2, "degrade": 3}


class GovernedBuffer:
    """A downstream, versioned store of known-good values (never a source store).

    Keyed by ``site_key`` (e.g. a SKU); values are the governed last-known-good.
    ``substitute`` returns ``None`` when the buffer cannot vouch for a key, so the
    gate falls back to a non-substituting response (block/escalate).
    """

    def __init__(self, values: dict[str, float] | None = None) -> None:
        self._values: dict[str, float] = dict(values or {})

    def put(self, key: str, value: float) -> None:
        self._values[key] = value

    def substitute(self, key: str) -> float | None:
        return self._values.get(key)


@dataclass(frozen=True)
class GateDecision:
    admitted: bool  # may the action execute autonomously?
    detected: bool  # did any constraint fire?
    response: str  # the winning response, or "admit" if nothing fired
    substituted_value: float | None  # governed-buffer value used, if any
    firing: tuple[str, ...]  # constraint ids that fired
    evidence_ids: tuple[str, ...]  # versioned evidence set (content-addressed)
    detail: dict[str, Any] = field(default_factory=dict)


class PreActionGate:
    """Evaluates the DQ spec at the Pre-Action verification point (PAG)."""

    def __init__(
        self,
        spec: ConstraintSpec | None = None,
        buffer: GovernedBuffer | None = None,
        *,
        site_field: str = "sku",
        value_field: str = "unit_cost",
    ) -> None:
        self.spec = spec if spec is not None else load_spec()
        self.buffer = buffer if buffer is not None else GovernedBuffer()
        self.site_field = site_field
        self.value_field = value_field

    def evaluate(self, evidence: Sequence[EvidenceRecord]) -> GateDecision:
        evidence_ids = tuple(r.evidence_id() for r in evidence)
        results = self.spec.evaluate(evidence, verif="PAG")
        fired = [(c, r) for c, r in results if not r.passed]
        if not fired:
            return GateDecision(True, False, "admit", None, (), evidence_ids)

        # Most restrictive fired response wins.
        winner = min((c for c, _ in fired), key=lambda c: _PRECEDENCE.get(c.response, 99))
        firing_ids = tuple(c.id for c, _ in fired)

        if winner.response == "quarantine_substitute":
            key = str(evidence[0].payload.get(self.site_field, evidence[0].record_id))
            sub = self.buffer.substitute(key)
            if sub is not None:
                return GateDecision(
                    True,
                    True,
                    "quarantine_substitute",
                    sub,
                    firing_ids,
                    evidence_ids,
                    {"substituted_key": key},
                )
            # No governed substitute available → fall back to block.
            return GateDecision(
                False,
                True,
                "block",
                None,
                firing_ids,
                evidence_ids,
                {"note": "no buffer substitute; blocked"},
            )
        if winner.response == "degrade":
            return GateDecision(True, True, "degrade", None, firing_ids, evidence_ids)
        # block / escalate: no autonomous execution.
        return GateDecision(False, True, winner.response, None, firing_ids, evidence_ids)
