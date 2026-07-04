"""Evidence records: the payload / metadata split that the whole thesis rests on.

A record the agent reads has two channels:

- **payload** — the content a naive agent sees: the actual field values
  (``unit_price``, ``vendor``, ...). A ``payload-visible`` defect is detectable
  from here alone.
- **metadata** — freshness / lineage / provenance: ``as_of`` timestamp, source
  system, record version, retrieval time. A ``metadata-borne`` defect is
  detectable *only* here — the payload alone is indistinguishable from clean.

The channel split is load-bearing for H2 (detection asymmetry): the arm-C critic
gets a **payload-only view** by construction, so it structurally cannot see a
metadata-borne defect, while the arm-D metadata gate can.

Every admitted action logs a *versioned evidence set* — the exact records +
metadata it relied on — via :meth:`EvidenceRecord.evidence_id`, giving full
lineage from action back to source (brief §2, downstream-only remediation).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from typing import Any


@dataclass(frozen=True)
class RecordMetadata:
    """Freshness / lineage / provenance for one record.

    ``as_of_day`` is the simulated day the value was true (staleness is
    ``now_day - as_of_day``). ``version`` distinguishes a superseded golden
    record from its replacement. Everything here is *metadata-borne*: it never
    appears in :class:`EvidenceRecord.payload`.
    """

    source: str  # source system id, e.g. "erp.pricing"
    as_of_day: int  # simulated day the payload value was valid
    retrieved_day: int  # simulated day the agent read it ("now")
    version: int = 1
    lineage: tuple[str, ...] = ()  # upstream record ids this was derived from

    @property
    def age_days(self) -> int:
        return self.retrieved_day - self.as_of_day


@dataclass(frozen=True)
class EvidenceRecord:
    """One record the agent reads: a payload plus its metadata.

    ``ground_truth`` is *never* shown to any agent, critic, judge or gate — it is
    the injector's private label for scoring (brief §5: "a ground-truth tag
    written to the run log"). It rides on the record only so the run log can pair
    each defect with the value it corrupted.
    """

    record_id: str
    payload: dict[str, Any]
    metadata: RecordMetadata
    ground_truth: dict[str, Any] = field(default_factory=dict)

    def payload_view(self) -> dict[str, Any]:
        """What a payload-only consumer (arm-C critic) sees: content, no metadata."""
        return dict(self.payload)

    def full_view(self) -> dict[str, Any]:
        """What a metadata-aware consumer (arm-D gate) sees: payload + metadata."""
        return {
            "payload": dict(self.payload),
            "metadata": {
                "source": self.metadata.source,
                "as_of_day": self.metadata.as_of_day,
                "retrieved_day": self.metadata.retrieved_day,
                "age_days": self.metadata.age_days,
                "version": self.metadata.version,
                "lineage": list(self.metadata.lineage),
            },
        }

    def evidence_id(self) -> str:
        """Content-addressed id over payload + metadata (excludes ground truth).

        This is the versioned evidence-set handle: two reads of the same value at
        the same version/as-of hash equal; any change to what was relied on
        changes the id. Ground truth is excluded so the evidence id reflects only
        what the agent actually saw.
        """
        blob = json.dumps(self.full_view(), sort_keys=True, default=str)
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    def with_payload(self, **updates: Any) -> EvidenceRecord:
        """Return a copy with payload fields replaced (used by the injector)."""
        return replace(self, payload={**self.payload, **updates})
