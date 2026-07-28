"""Items #4, #5, #6 --- robustness of the H4/coverage conclusions under deterministic
recomputation from committed data. No reruns, no threshold changes to the registered
verdict; every alternative is a sensitivity analysis alongside the frozen tau_m=0.005.

  #5 leave-one-class-out : portfolio recovery with each class removed -> structural dependence.
  #6 predicate ablations : recovery attainable by each predicate subset (freshness/schema/
                           lineage/completeness/combined), from per-class loss + coverage.
  #4 threshold sensitivity: oracle ADR under a sweep of materiality thresholds (the oracle
                            reproduces measured ADR to MAE 0.015, so it is a faithful,
                            fully-reproducible proxy for the logged order-delta sensitivity).
"""

from __future__ import annotations

import json
import statistics
from collections.abc import Callable
from typing import Any

from analysis.common import CLASS_PREDICATE, RATES, ROOT, load_summary, oracle_cell

OUT = ROOT / "analysis" / "out" / "robustness.json"
# Predicate -> the classes it covers (from the frozen gate design / CLASS_PREDICATE).
PRED_COVERS = {
    "freshness": [c for c, p in CLASS_PREDICATE.items() if p == "freshness"],
    "schema": [c for c, p in CLASS_PREDICATE.items() if p == "schema"],
    "completeness": [c for c, p in CLASS_PREDICATE.items() if p == "completeness"],
    "consistency": [c for c, p in CLASS_PREDICATE.items() if p == "consistency"],
    "lineage": [],  # lineage is a provenance guarantee (Prop 1), not a loss-recovery predicate
}


def _class_pool(m: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for cls in m:
        la = [x for cell in m[cls].values() for x in cell.get("A", {}).get("paired_losses", [])]
        ld = [x for cell in m[cls].values() for x in cell.get("D", {}).get("paired_losses", [])]
        out[cls] = {
            "n": len(la),
            "loss_a": statistics.mean(la) if la else 0.0,
            "loss_d": statistics.mean(ld) if ld else 0.0,
        }
    return out


def _recovery(
    pool: dict[str, dict[str, Any]],
    classes: list[str],
    loss_d_of: Callable[[str, dict[str, dict[str, Any]]], float],
) -> float:
    tot_n = sum(pool[c]["n"] for c in classes)
    if not tot_n:
        return 0.0
    num = sum(pool[c]["n"] / tot_n * (pool[c]["loss_a"] - loss_d_of(c, pool)) for c in classes)
    den = sum(pool[c]["n"] / tot_n * pool[c]["loss_a"] for c in classes)
    return num / den if den else 0.0


def build() -> dict[str, Any]:
    pool = _class_pool(load_summary("h4-recovery")["matrix"])
    classes = list(pool)

    # #5 leave-one-class-out.
    full = _recovery(pool, classes, lambda c, p: p[c]["loss_d"])
    loo: list[dict[str, Any]] = []
    for drop in classes:
        kept = [c for c in classes if c != drop]
        loo.append(
            {
                "excluded": drop,
                "recovery": round(_recovery(pool, kept, lambda c, p: p[c]["loss_d"]), 4),
            }
        )
    loo.sort(key=lambda r: -r["recovery"])

    # #6 predicate ablations: a gate with only predicate P recovers (uses loss_D) on classes
    # P covers, and leaves every other class at its ungated loss (loss_A).
    def ablate(active: set[str]) -> float:
        covered = {c for p in active for c in PRED_COVERS.get(p, [])}
        return _recovery(
            pool, classes, lambda c, p: p[c]["loss_d"] if c in covered else p[c]["loss_a"]
        )

    ablations = {
        "freshness_only": round(ablate({"freshness"}), 4),
        "schema_only": round(ablate({"schema"}), 4),
        "completeness_only": round(ablate({"completeness"}), 4),
        "consistency_only": round(ablate({"consistency"}), 4),
        "lineage_only": round(ablate({"lineage"}), 4),
        "combined_v1": round(ablate({"freshness", "schema", "completeness", "consistency"}), 4),
    }

    # #4 threshold sensitivity on the oracle conversion (priced metadata-borne classes).
    priced = [
        "silent_unit_change",
        "stale_master_data",
        "superseded_golden_record",
        "plausible_outlier",
    ]
    taus = [0.001, 0.005, 0.01, 0.02, 0.05]
    cells = {(c, r): oracle_cell(c, r, fixed_n=True) for c in priced for r in RATES}
    thr_curve = []
    for tau in taus:
        adrs = []
        for outs in cells.values():
            if outs:
                adrs.append(sum(o.paired_loss >= tau * o.clean_cost for o in outs) / len(outs))
        thr_curve.append({"tau_m": tau, "mean_oracle_adr": round(statistics.mean(adrs), 4)})

    return {
        "loo": {"full_recovery": round(full, 4), "leave_one_out": loo},
        "predicate_ablations": {"full_no_gate_baseline": 0.0, **ablations},
        "threshold_sensitivity": {
            "registered_tau_m": 0.005,
            "note": "oracle ADR vs tau_m; registered tau_m=0.005 is one point on the curve",
            "curve": thr_curve,
        },
    }


def main() -> int:
    res = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  LOO full={res['loo']['full_recovery']} top-swing={res['loo']['leave_one_out'][0]}")
    print(f"  predicate ablations={res['predicate_ablations']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
