"""Corruption taxonomy v0 — eight classes (Phase 1 scaffolding).

Labeled **v0** everywhere: this list is scaffolding the human revises from
enterprise experience (``reports/TAXONOMY_REVISION_GUIDE.md``); it is explicitly
not the intellectual contribution. Each class is a frozen dataclass declaring its
detection ``channel`` and injection ``site``, and an ``inject`` that returns an
:class:`~sarc_dq.taxonomy.base.InjectionResult` with a ground-truth tag.

Channel tags (load-bearing for H2):
  1. stale_master_data                 — metadata-borne
  2. superseded_golden_record          — metadata-borne
  3. silent_unit_change                — metadata-borne (unit not printed in payload)
  4. duplicate_vendor_conflicting_terms — payload-visible
  5. cross_source_contradiction        — payload-visible
  6. schema_drift                      — payload-visible
  7. missing_mandatory_field           — payload-visible
  8. plausible_outlier                 — metadata-borne (only lineage reveals)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, replace

from sarc_dq.records import EvidenceRecord
from sarc_dq.substrate import Episode
from sarc_dq.taxonomy.base import CorruptionClass, InjectionResult, base_ground_truth

_KG_LB = 2.2046226218  # kg <-> lb, the canonical silent-unit-change factor


def _price(record: EvidenceRecord) -> float:
    return float(record.payload["unit_cost"])


@dataclass(frozen=True)
class StaleMasterData:
    name: str = "stale_master_data"
    channel: str = "metadata-borne"
    site: str = "unit_price"
    default_rate: float = 0.10
    min_age_days: int = 90
    max_age_days: int = 180

    def inject(
        self, record: EvidenceRecord, episode: Episode, rng: random.Random
    ) -> InjectionResult:
        age = rng.randint(self.min_age_days, self.max_age_days)
        months = age / 30.0
        rate = rng.uniform(-0.05, 0.05)
        true_p = _price(record)
        stale_p = max(1.0, round(true_p / ((1.0 + rate) ** months), 4))
        now = record.metadata.retrieved_day
        meta = replace(record.metadata, as_of_day=now - age, retrieved_day=now)
        primary = EvidenceRecord(
            record.record_id,
            {**record.payload, "unit_cost": stale_p},
            meta,
            base_ground_truth(
                self, true_unit_cost=true_p, observed_unit_cost=stale_p, age_days=age
            ),
        )
        return InjectionResult(primary, (), dict(primary.ground_truth))


@dataclass(frozen=True)
class SupersededGoldenRecord:
    name: str = "superseded_golden_record"
    channel: str = "metadata-borne"
    site: str = "unit_price"
    default_rate: float = 0.05

    def inject(
        self, record: EvidenceRecord, episode: Episode, rng: random.Random
    ) -> InjectionResult:
        true_p = _price(record)
        old_p = max(1.0, round(true_p * rng.uniform(0.6, 0.9), 4))  # the superseded value
        now = record.metadata.retrieved_day
        # Primary = the OLD superseded record the agent mistakenly reads (v1, older).
        primary = EvidenceRecord(
            record.record_id,
            {**record.payload, "unit_cost": old_p},
            replace(record.metadata, version=1, as_of_day=now - rng.randint(30, 120)),
            base_ground_truth(self, true_unit_cost=true_p, observed_unit_cost=old_p),
        )
        # Companion = the current golden (v2) carrying the true value.
        companion = EvidenceRecord(
            record.record_id,
            {**record.payload, "unit_cost": true_p},
            replace(record.metadata, version=2, as_of_day=now),
            {"role": "current_golden"},
        )
        return InjectionResult(primary, (companion,), dict(primary.ground_truth))


@dataclass(frozen=True)
class SilentUnitChange:
    name: str = "silent_unit_change"
    channel: str = "metadata-borne"
    site: str = "unit_price"
    default_rate: float = 0.05

    def inject(
        self, record: EvidenceRecord, episode: Episode, rng: random.Random
    ) -> InjectionResult:
        true_p = _price(record)
        factor = _KG_LB if rng.random() < 0.5 else 1.0 / _KG_LB
        observed = round(true_p * factor, 4)  # recorded in the wrong unit; label unchanged
        primary = EvidenceRecord(
            record.record_id,
            {**record.payload, "unit_cost": observed},
            record.metadata,
            base_ground_truth(
                self,
                true_unit_cost=true_p,
                observed_unit_cost=observed,
                unit_factor=round(factor, 6),
            ),
        )
        return InjectionResult(primary, (), dict(primary.ground_truth))


@dataclass(frozen=True)
class DuplicateVendorConflictingTerms:
    name: str = "duplicate_vendor_conflicting_terms"
    channel: str = "payload-visible"
    site: str = "vendor_terms"
    default_rate: float = 0.05

    def inject(
        self, record: EvidenceRecord, episode: Episode, rng: random.Random
    ) -> InjectionResult:
        true_p = _price(record)
        conflict_p = max(1.0, round(true_p * rng.uniform(1.15, 1.6), 4))
        # The agent keys on the conflicting duplicate row (vendor-B); the true-terms
        # row (vendor-A) is the companion.
        companion = EvidenceRecord(
            record.record_id + ":alt",
            {**record.payload, "unit_cost": true_p, "vendor": "vendor-A"},
            record.metadata,
            {"role": "true_terms"},
        )
        primary = EvidenceRecord(
            record.record_id,
            {**record.payload, "unit_cost": conflict_p, "vendor": "vendor-B"},
            replace(record.metadata, source="erp.pricing.altvendor"),
            base_ground_truth(self, true_unit_cost=true_p, observed_unit_cost=conflict_p),
        )
        return InjectionResult(primary, (companion,), dict(primary.ground_truth))


@dataclass(frozen=True)
class CrossSourceContradiction:
    name: str = "cross_source_contradiction"
    channel: str = "payload-visible"
    site: str = "unit_price"
    default_rate: float = 0.05
    tolerance: float = 0.02

    def inject(
        self, record: EvidenceRecord, episode: Episode, rng: random.Random
    ) -> InjectionResult:
        true_p = _price(record)
        other_p = max(1.0, round(true_p * rng.uniform(1.1, 1.5), 4))  # beyond tolerance
        # Companion carries the authoritative (true) value; the primary the agent
        # keys on carries the contradicting one, so acting on it converts.
        other = EvidenceRecord(
            record.record_id,
            {**record.payload, "unit_cost": true_p},
            replace(record.metadata, source="contract.authoritative"),
            {"role": "authoritative_source"},
        )
        primary = EvidenceRecord(
            record.record_id,
            {**record.payload, "unit_cost": other_p},
            replace(record.metadata, source="dwh.pricing"),
            base_ground_truth(self, true_unit_cost=true_p, observed_unit_cost=other_p),
        )
        return InjectionResult(primary, (other,), dict(primary.ground_truth))


@dataclass(frozen=True)
class SchemaDrift:
    name: str = "schema_drift"
    channel: str = "payload-visible"
    site: str = "unit_price"
    default_rate: float = 0.05

    def inject(
        self, record: EvidenceRecord, episode: Episode, rng: random.Random
    ) -> InjectionResult:
        true_p = _price(record)
        payload = {k: v for k, v in record.payload.items() if k != "unit_cost"}
        # Field renamed AND retyped (float -> string): the canonical schema drift.
        payload["unitCost"] = f"{true_p:.4f}"
        primary = EvidenceRecord(
            record.record_id,
            payload,
            record.metadata,
            base_ground_truth(
                self, true_unit_cost=true_p, drifted_field="unit_cost->unitCost:str"
            ),
        )
        return InjectionResult(primary, (), dict(primary.ground_truth))


@dataclass(frozen=True)
class MissingMandatoryField:
    name: str = "missing_mandatory_field"
    channel: str = "payload-visible"
    site: str = "unit_price"
    default_rate: float = 0.05

    def inject(
        self, record: EvidenceRecord, episode: Episode, rng: random.Random
    ) -> InjectionResult:
        true_p = _price(record)
        payload = {k: v for k, v in record.payload.items() if k != "unit_cost"}  # drop mandatory
        primary = EvidenceRecord(
            record.record_id,
            payload,
            record.metadata,
            base_ground_truth(self, true_unit_cost=true_p, missing_field="unit_cost"),
        )
        return InjectionResult(primary, (), dict(primary.ground_truth))


@dataclass(frozen=True)
class PlausibleOutlier:
    name: str = "plausible_outlier"
    channel: str = "metadata-borne"  # wrong but in-range; only lineage reveals
    site: str = "unit_price"
    default_rate: float = 0.05

    def inject(
        self, record: EvidenceRecord, episode: Episode, rng: random.Random
    ) -> InjectionResult:
        true_p = _price(record)
        # An in-range but wrong value (e.g. another SKU's price mis-joined). Same
        # 8..22 band the substrate draws from, so the payload looks entirely normal.
        wrong = round(rng.uniform(8.0, 22.0), 4)
        while abs(wrong - true_p) < 2.0:
            wrong = round(rng.uniform(8.0, 22.0), 4)
        primary = EvidenceRecord(
            record.record_id,
            {**record.payload, "unit_cost": wrong},
            record.metadata,
            base_ground_truth(self, true_unit_cost=true_p, observed_unit_cost=wrong),
        )
        return InjectionResult(primary, (), dict(primary.ground_truth))


# Taxonomy v0 — instantiated with scaffolding defaults, in declared order.
TAXONOMY_V0: tuple[CorruptionClass, ...] = (
    StaleMasterData(),
    SupersededGoldenRecord(),
    SilentUnitChange(),
    DuplicateVendorConflictingTerms(),
    CrossSourceContradiction(),
    SchemaDrift(),
    MissingMandatoryField(),
    PlausibleOutlier(),
)
