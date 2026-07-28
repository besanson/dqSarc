"""Item #10 --- a second decision process, to show the architecture ports (not that it
wins universally). Deterministic, no LLM, no API.

Domain: **B2C personalised-promotion eligibility** (deliberately not procure-to-pay). An
agent decides whether to extend a targeted offer to a customer. The economics are a binary
offer decision --- structurally different from the newsvendor order quantity --- but the
*data architecture is identical*: a payload channel the naive agent reads, and a metadata
channel (campaign validity window, audience-segment version, score freshness, consent,
model version, provenance) where the defects live.

  payload  : customer profile, purchase history, campaign id, cart value, loyalty tier
  metadata : campaign_valid_until, segment_version, score_as_of, consent, model_version, source

Six metadata-borne corruptions, mirroring the procurement taxonomy one-for-one:

  expired_campaign        (freshness)     campaign validity window has passed
  superseded_segmentation (version)       an old audience segment read instead of the current
  stale_score             (freshness)     conversion score is stale (older, higher)
  outdated_rules          (version)       eligibility ruleset version behind the current
  missing_consent         (completeness)  consent field absent
  obsolete_recommendation (freshness)     recommendation model version behind current

Economics (priced, paired): the agent offers iff its *believed* expected value is positive.
The world realises value at the *true* conversion probability and true eligibility; a metadata
defect corrupts the belief, so a wrong offer converts into a currency loss versus the clean
decision. We report the same ADR (material-divergence rate) and the gate's recovery, computed
by the SAME predicate family (``sarc_dq.dq_predicates``) --- the portability demonstration.

Writes ``analysis/out/second_domain.json``.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from typing import Any

from analysis.common import RATES, ROOT
from sarc_dq.config import TAU_M_DEFAULT
from sarc_dq.dq_predicates import complete, freshness, golden_record_unique
from sarc_dq.records import EvidenceRecord, RecordMetadata

OUT = ROOT / "analysis" / "out" / "second_domain.json"
SEED = 20260707  # same base seed family as the main study; deterministic.
N = 200
FIXED_N = 40  # corrupted per (class, rate) cell, stratified like the main study
MAX_AGE = 30  # freshness predicate window (days), matches the procurement gate
SEND_COST = 2.0  # fixed cost of extending an offer

PROMO_CLASSES = [
    "expired_campaign",
    "superseded_segmentation",
    "stale_score",
    "outdated_rules",
    "missing_consent",
    "obsolete_recommendation",
]
# Which reused predicate covers each promo class (the portability mapping).
PROMO_PREDICATE = {
    "expired_campaign": "freshness",
    "superseded_segmentation": "golden_record_unique",
    "stale_score": "freshness",
    "outdated_rules": "golden_record_unique",
    "missing_consent": "complete",
    "obsolete_recommendation": "freshness",
}


@dataclass(frozen=True)
class Promo:
    cid: str
    p_true: float  # true conversion probability
    margin: float  # profit on a conversion
    discount: float  # given up on a conversion
    now_day: int
    eligible: bool  # true campaign/consent eligibility

    def ev(self, p: float, eligible: bool) -> float:
        """Believed expected value of offering, given a believed conversion p and eligibility."""
        if not eligible:
            return -SEND_COST  # a believed-ineligible customer is not worth offering
        return p * (self.margin - self.discount) - SEND_COST

    def realised(self, offered: bool, true_eligible: bool) -> float:
        """Currency the world realises for the offer decision, priced at the TRUE state."""
        if not offered:
            return 0.0
        base = self.p_true * (self.margin - self.discount) - SEND_COST
        # Offering a truly-ineligible customer (expired campaign / withdrawn consent) is a
        # compliance loss on top of the wasted send.
        return base if true_eligible else base - 0.5 * self.margin


def _episode(i: int) -> Promo:
    rng = random.Random((SEED * 1_000_003 + i) & 0x7FFFFFFF)
    return Promo(
        cid=f"CUST-{rng.randint(10000, 99999)}",
        p_true=rng.uniform(0.05, 0.6),
        margin=rng.uniform(20.0, 200.0),
        discount=rng.uniform(5.0, 40.0),
        now_day=3000 + i,
        eligible=True,  # clean world: eligible; corruptions flip eligibility/score
    )


def _corrupted_indices(rate: float) -> list[int]:
    idxs = list(range(N))
    rate_key = int(round(rate * 1_000_000))
    random.Random((SEED * 40_503 + rate_key) & 0x7FFFFFFF).shuffle(idxs)
    return sorted(idxs[:FIXED_N])


def _clean_records(ep: Promo) -> tuple[EvidenceRecord, ...]:
    md = RecordMetadata("crm.audience", ep.now_day, ep.now_day, version=2)
    payload = {
        "customer": ep.cid,
        "score": round(ep.p_true, 4),
        "campaign": "SUMMER",
        "consent": True,
        "cart_value": round(ep.margin, 2),
    }
    return (EvidenceRecord(f"{ep.cid}:promo", payload, md),)


def _inject(
    cls: str, ep: Promo, rng: random.Random
) -> tuple[tuple[EvidenceRecord, ...], float, bool]:
    """Return (evidence_set, believed_score, believed_eligible) for a corrupted episode."""
    (clean,) = _clean_records(ep)
    p = clean.payload
    md = clean.metadata
    if cls == "expired_campaign":
        # Validity window passed: metadata age exceeds the window; belief still "valid".
        bad = EvidenceRecord(
            clean.record_id,
            dict(p),
            RecordMetadata(md.source, ep.now_day - rng.randint(40, 120), ep.now_day, md.version),
        )
        return (bad,), ep.p_true, True
    if cls == "stale_score":
        stale = min(0.95, ep.p_true * rng.uniform(1.5, 3.0))  # old, over-optimistic score
        bad = EvidenceRecord(
            clean.record_id,
            {**p, "score": round(stale, 4)},
            RecordMetadata(md.source, ep.now_day - rng.randint(40, 120), ep.now_day, md.version),
        )
        return (bad,), stale, True
    if cls == "obsolete_recommendation":
        stale = min(0.95, ep.p_true * rng.uniform(1.3, 2.5))
        bad = EvidenceRecord(
            clean.record_id,
            {**p, "score": round(stale, 4)},
            RecordMetadata(md.source, ep.now_day - rng.randint(40, 120), ep.now_day, version=1),
        )
        return (bad,), stale, True
    if cls in ("superseded_segmentation", "outdated_rules"):
        # An old (v1) segment/ruleset read alongside the current (v2) golden record.
        old = EvidenceRecord(
            clean.record_id,
            {**p, "score": round(min(0.95, ep.p_true * 2), 4)},
            RecordMetadata(md.source, ep.now_day, ep.now_day, version=1),
        )
        cur = EvidenceRecord(
            clean.record_id, dict(p), RecordMetadata(md.source, ep.now_day, ep.now_day, version=2)
        )
        return (old, cur), min(0.95, ep.p_true * 2), True
    if cls == "missing_consent":
        payload = {k: v for k, v in p.items() if k != "consent"}  # consent field dropped
        bad = EvidenceRecord(clean.record_id, payload, md)
        return (bad,), ep.p_true, True  # agent, missing the flag, assumes eligible
    raise ValueError(cls)


def _gate_detects(evidence: tuple[EvidenceRecord, ...]) -> bool:
    f = freshness(evidence, {"max_age_days": MAX_AGE})
    g = golden_record_unique(evidence, {})
    c = complete(evidence, {"required_fields": ["customer", "score", "campaign", "consent"]})
    return not (f.passed and g.passed and c.passed)


def build() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    tot_material = tot_corr = 0
    tot_loss = tot_recovered = 0.0
    for cls in PROMO_CLASSES:
        material = corr = 0
        loss_sum = recovered = 0.0
        for rate in RATES:
            for i in _corrupted_indices(rate):
                ep = _episode(i)
                rng = random.Random((SEED * 7 + i * 13 + int(rate * 1000)) & 0x7FFFFFFF)
                evidence, p_bel, elig_bel = _inject(cls, ep, rng)
                # Injected eligibility truth: expired campaign / withdrawn consent => ineligible.
                true_elig = cls not in ("expired_campaign", "missing_consent")
                # Correct action (knows the truth) vs corrupted action (acts on the belief).
                correct_offer = ep.ev(ep.p_true, true_elig) > 0
                corr_offer = ep.ev(p_bel, elig_bel) > 0
                loss = ep.realised(correct_offer, true_elig) - ep.realised(corr_offer, true_elig)
                ref = max(1.0, ep.margin)
                corr += 1
                loss_sum += loss
                if loss >= TAU_M_DEFAULT * ref:
                    material += 1
                # Gate detects the metadata defect -> substitute clean -> correct action -> loss 0.
                if _gate_detects(evidence):
                    recovered += loss
        rows.append(
            {
                "class": cls,
                "predicate": PROMO_PREDICATE[cls],
                "n_corrupted": corr,
                "adr": round(material / corr, 4) if corr else 0.0,
                "mean_loss": round(loss_sum / corr, 3) if corr else 0.0,
                "gate_recovered_fraction": round(recovered / loss_sum, 4) if loss_sum else 0.0,
            }
        )
        tot_material += material
        tot_corr += corr
        tot_loss += loss_sum
        tot_recovered += recovered

    return {
        "note": "B2C promotion-eligibility domain; same payload/metadata split + predicate family",
        "domain": "personalised_promotion_eligibility",
        "reused_predicates": ["freshness", "golden_record_unique", "complete"],
        "rows": rows,
        "portfolio_adr": round(tot_material / tot_corr, 4) if tot_corr else 0.0,
        "portfolio_gate_recovery": round(tot_recovered / tot_loss, 4) if tot_loss else 0.0,
        "interpretation": (
            "the identical predicate family detects metadata-borne promo defects and the gate "
            "recovers the induced loss --- the architecture ports to a structurally different "
            "decision. This demonstrates portability, not that the gate is universally optimal."
        ),
    }


def main() -> int:
    res = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  portfolio ADR={res['portfolio_adr']} gate recovery={res['portfolio_gate_recovery']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
