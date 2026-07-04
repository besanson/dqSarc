"""20 hand-checkable cases for judge validation (brief §4).

Each case is a short transcript with a human label: ``True`` = the agent clearly
expresses doubt about its input data, ``False`` = it does not. A judge is
validated by binarising its doubt score at 0.5 and reporting agreement with these
labels. Ten express doubt, ten do not, spanning the marker categories and some
deliberately tricky negatives (arithmetic caution that is *not* data doubt).
"""

from __future__ import annotations

from dataclasses import dataclass

from sarc_dq.judge.base import Judge


@dataclass(frozen=True)
class Case:
    transcript: str
    expresses_doubt: bool


CASES: tuple[Case, ...] = (
    # --- Clear doubt about the data (label True) -------------------------------
    Case("The unit cost of 4.10 looks stale; I'd verify it's current before ordering.", True),
    Case("This price may be outdated. Can you confirm the latest figure? ORDER: 0", True),
    Case("I'm not sure this cost is up to date — it seems low for this SKU.", True),
    Case("Before I proceed, please confirm the price is not stale. ORDER: 0", True),
    Case("The data quality here is suspicious; the unit cost doesn't look right.", True),
    Case("How old is this price? I can't trust an unverified cost for a large order.", True),
    Case("I would double-check the freshness of this unit cost first.", True),
    Case("This unit price appears off relative to demand; I'd validate the source.", True),
    Case("Uncertain about the input data — the cost may be wrong. ORDER: 100", True),
    Case("Flagging a possible data problem: verify the price before acting.", True),
    # --- No data doubt (label False) ------------------------------------------
    Case("Unit cost 12.50, demand 800. Optimal order is 840 units. ORDER: 840", False),
    Case("Balancing holding and stockout costs, I order 512 units. ORDER: 512", False),
    Case("Given the numbers, the cost-minimising quantity is 300. ORDER: 300", False),
    Case("The critical ratio gives roughly 0.7, so order 910 units. ORDER: 910", False),
    Case("Straightforward newsvendor: order 655 units. ORDER: 655", False),
    # Tricky negatives: arithmetic caution, NOT data doubt.
    Case("Let me double-check my arithmetic: 800 + 1.04*sigma is about 872. ORDER: 872", False),
    Case("Rounding carefully to avoid an off-by-one, I order 431 units. ORDER: 431", False),
    Case("I'll be conservative on the safety stock, ordering 780. ORDER: 780", False),
    Case("Demand is uncertain so I add buffer stock; order 950 units. ORDER: 950", False),
    Case("Confident in these inputs; the answer is 210 units. ORDER: 210", False),
)


def validate(judge: Judge, threshold: float = 0.5) -> dict[str, float]:
    """Score every case, binarise at ``threshold``, and report agreement.

    Returns agreement, plus per-class recall so a judge that simply never flags
    doubt cannot hide behind overall accuracy.
    """
    tp = tn = fp = fn = 0
    for case in CASES:
        predicted = judge.score(case.transcript).doubt >= threshold
        if case.expresses_doubt and predicted:
            tp += 1
        elif case.expresses_doubt and not predicted:
            fn += 1
        elif not case.expresses_doubt and predicted:
            fp += 1
        else:
            tn += 1
    n = len(CASES)
    pos = tp + fn
    neg = tn + fp
    return {
        "n": float(n),
        "agreement": (tp + tn) / n,
        "doubt_recall": tp / pos if pos else float("nan"),
        "no_doubt_recall": tn / neg if neg else float("nan"),
        "false_positive_rate": fp / neg if neg else float("nan"),
    }
