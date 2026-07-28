"""Item #2 --- the H4 coverage accounting identity.

Replaces the qualitative H4 story with an exact decomposition that reproduces the committed
portfolio recovery from per-class terms:

    portfolio_recovery = (L_A - L_D) / (L_A - L_E),   L_x = sum_c w_c * loss_x,c

where w_c = n_corrupted,c / N is the class weight, loss_x,c is arm x's mean paired loss on
class c, and L_E = 0 by construction (the oracle). Each class contributes
w_c*(loss_A,c - loss_D,c) to the recovered numerator and w_c*loss_A,c to the denominator.
A class is *covered* iff the v1 gate has a predicate for it (CLASS_PREDICATE); an uncovered
class has loss_D,c ~= loss_A,c (no recovery) yet still loads the denominator by its magnitude.

The point: the observed portfolio recovery is *predicted by coverage accounting* --- it is
low because the single uncovered, high-magnitude class (silent_unit_change) dominates the
denominator. Writes ``analysis/out/coverage_accounting.json``.
"""

from __future__ import annotations

import json
import statistics
from typing import Any

from analysis.common import CLASS_PREDICATE, ROOT, load_summary

OUT = ROOT / "analysis" / "out" / "coverage_accounting.json"


def _pool(matrix: dict[str, Any], cls: str, arm: str) -> tuple[list[float], int]:
    vals: list[float] = []
    for cell in matrix[cls].values():
        a = cell.get(arm)
        if a:
            vals += a.get("paired_losses", [])
    return vals, len(vals)


def build() -> dict[str, Any]:
    h4 = load_summary("h4-recovery")
    m = h4["matrix"]
    classes = list(m.keys())

    per_class = {}
    tot_n = 0
    for cls in classes:
        la, na = _pool(m, cls, "A")
        ld, _ = _pool(m, cls, "D")
        mean_a = statistics.mean(la) if la else 0.0
        mean_d = statistics.mean(ld) if ld else 0.0
        per_class[cls] = {"n": na, "loss_a": mean_a, "loss_d": mean_d}
        tot_n += na

    # Weights and the exact pooled identity (weighted by n = magnitude of each class's
    # contribution to the pool).
    num = den = 0.0
    rows = []
    for cls in classes:
        pc = per_class[cls]
        w = pc["n"] / tot_n if tot_n else 0.0
        contrib_num = w * (pc["loss_a"] - pc["loss_d"])  # recovered $ (weighted)
        contrib_den = w * pc["loss_a"]  # recoverable $ (weighted), since L_E=0
        num += contrib_num
        den += contrib_den
        covered = CLASS_PREDICATE.get(cls) is not None
        rows.append(
            {
                "class": cls,
                "n": pc["n"],
                "weight": round(w, 4),
                "loss_a": round(pc["loss_a"], 2),
                "loss_d": round(pc["loss_d"], 2),
                "predicate": CLASS_PREDICATE.get(cls),
                "covered": covered,
                "num_contribution": round(contrib_num, 3),
                "den_contribution": round(contrib_den, 3),
            }
        )
    recovery_identity = num / den if den else None

    # Cross-check against the committed portfolio pooled means.
    all_a = [x for cls in classes for x in _pool(m, cls, "A")[0]]
    all_d = [x for cls in classes for x in _pool(m, cls, "D")[0]]
    mean_a_all, mean_d_all = statistics.mean(all_a), statistics.mean(all_d)
    recovery_direct = (mean_a_all - mean_d_all) / mean_a_all if mean_a_all else None

    # Which class dominates the denominator (the recoverable pool)?
    dominant = max(rows, key=lambda r: abs(r["den_contribution"]))
    return {
        "note": "H4 portfolio recovery decomposed by class weight x baseline loss x coverage",
        "rows": sorted(rows, key=lambda r: -abs(r["den_contribution"])),
        "recovery_from_identity": round(recovery_identity, 4) if recovery_identity else None,
        "recovery_direct_pooled": round(recovery_direct, 4) if recovery_direct else None,
        "residual": (
            round(abs(recovery_identity - recovery_direct), 6)
            if (recovery_identity is not None and recovery_direct is not None)
            else None
        ),
        "dominant_class": dominant["class"],
        "dominant_den_share": (
            round(
                abs(dominant["den_contribution"]) / sum(abs(r["den_contribution"]) for r in rows),
                4,
            )
            if any(r["den_contribution"] for r in rows)
            else None
        ),
    }


def main() -> int:
    res = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(
        f"  identity recovery={res['recovery_from_identity']} "
        f"direct={res['recovery_direct_pooled']} residual={res['residual']} "
        f"dominant={res['dominant_class']} ({res['dominant_den_share']} of denominator)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
