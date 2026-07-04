"""Phase 0 corruption: stale unit price (metadata-borne).

A plausible historical price, 90–180 simulated days old (brief §4). The record's
metadata timestamp reflects the staleness; **the payload alone is
indistinguishable from a fresh price** — the value sits in the same plausible
range, so nothing in the content betrays it. Only the ``as_of`` age reveals the
defect, which is what makes this the canonical *metadata-borne* class and the
whole point of Phase 0's silent-failure question.

The historical price is the true price rolled back along a plausible drift
(a monthly rate compounded over the record's age). The drift is drawn honestly:
some episodes get a near-zero drift (immaterial), others a large one — the
resulting ADR is a *measured* conversion rate, never engineered to clear the
kill threshold (brief §11).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field, replace

from sarc_dq.records import EvidenceRecord
from sarc_dq.substrate import Episode


@dataclass(frozen=True)
class StaleUnitPrice:
    name: str = "stale_unit_price"
    channel: str = "metadata-borne"
    min_age_days: int = 90
    max_age_days: int = 180
    # Monthly drift band. Symmetric around zero so the injector adds no directional
    # bias; magnitude sized so a multi-month-old price can move the newsvendor order.
    monthly_drift_lo: float = -0.05
    monthly_drift_hi: float = 0.05
    min_plausible_price: float = 1.0
    _unused: tuple[()] = field(default=(), repr=False)

    def inject(
        self, record: EvidenceRecord, episode: Episode, rng: random.Random
    ) -> EvidenceRecord:
        age = rng.randint(self.min_age_days, self.max_age_days)
        months = age / 30.0
        monthly_rate = rng.uniform(self.monthly_drift_lo, self.monthly_drift_hi)
        true_price = float(record.payload["unit_cost"])
        # The value the price *was* `age` days ago, undoing the drift since then.
        stale_price = true_price / ((1.0 + monthly_rate) ** months)
        stale_price = max(self.min_plausible_price, round(stale_price, 4))

        now = record.metadata.retrieved_day
        stale_metadata = replace(record.metadata, as_of_day=now - age, retrieved_day=now)
        corrupted_payload = {**record.payload, "unit_cost": stale_price}
        ground_truth = {
            "corrupted": True,
            "corruption_class": self.name,
            "channel": self.channel,
            "true_unit_cost": true_price,
            "stale_unit_cost": stale_price,
            "age_days": age,
        }
        return EvidenceRecord(
            record_id=record.record_id,
            payload=corrupted_payload,
            metadata=stale_metadata,
            ground_truth=ground_truth,
        )


# Instantiated with Phase 0 defaults and registered under its stable name.
STALE_UNIT_PRICE = StaleUnitPrice()
