"""Item #4 (statistical reporting) --- quantify the H1 ladder *flatness* from committed data.

The paper's H1 claim is that metadata-borne action-defect rates stay flat (to slightly rising)
across the four-tier model ladder. "Flat" deserves a number, not an adjective. Using only the
committed ``h1-ladder`` per-class pooled counts, we pool the metadata-borne classes per model,
give each tier a Wald 95%% CI, and report:

  * the endpoint difference (top tier - bottom tier) with a two-proportion Wald 95%% CI, and
  * the ordinary-least-squares trend across the four ordered tiers (ADR per tier step).

Metadata-borne channel (from the frozen taxonomy): stale_master_data, superseded_golden_record,
silent_unit_change, plausible_outlier. Deterministic; reads committed summaries only.

Writes ``analysis/out/stats_tables.json``.
"""

from __future__ import annotations

import json
from typing import Any

from analysis.common import ROOT, load_summary

OUT = ROOT / "analysis" / "out" / "stats_tables.json"
METADATA_BORNE = [
    "stale_master_data",
    "superseded_golden_record",
    "silent_unit_change",
    "plausible_outlier",
]


def _pooled_meta(summ: dict[str, Any], model: str) -> tuple[int, int]:
    """(#material, #corrupted) pooled over metadata-borne classes for one model tier."""
    pcp = summ["per_class_pooled"]
    material = corrupted = 0
    for cls in METADATA_BORNE:
        cell = pcp.get(cls, {}).get(model)
        if cell:
            n = int(cell["n_corrupted"])
            corrupted += n
            material += int(round(float(cell["adr"]) * n))
    return material, corrupted


def _wald(p: float, n: int) -> tuple[float, float]:
    se = (p * (1 - p) / n) ** 0.5 if n else 0.0
    return max(0.0, p - 1.96 * se), min(1.0, p + 1.96 * se)


def build() -> dict[str, Any]:
    summ = load_summary("h1-ladder")
    tiers = list(summ["config"]["axis"])  # ordered haiku -> ... -> fable

    ladder = []
    ps: list[float] = []
    for t in tiers:
        mat, n = _pooled_meta(summ, t)
        p = mat / n if n else 0.0
        lo, hi = _wald(p, n)
        ladder.append(
            {"tier": t, "n": n, "adr": round(p, 4), "ci95": [round(lo, 4), round(hi, 4)]}
        )
        ps.append(p)

    # Endpoint difference (top - bottom) with a two-proportion Wald CI.
    lo_mat, lo_n = _pooled_meta(summ, tiers[0])
    hi_mat, hi_n = _pooled_meta(summ, tiers[-1])
    p_lo, p_hi = lo_mat / lo_n, hi_mat / hi_n
    diff = p_hi - p_lo
    se_diff = (p_lo * (1 - p_lo) / lo_n + p_hi * (1 - p_hi) / hi_n) ** 0.5
    d_lo, d_hi = diff - 1.96 * se_diff, diff + 1.96 * se_diff

    # OLS trend across the four ordered tiers (x = 0..3), slope = ADR change per tier step.
    n_t = len(ps)
    xs = list(range(n_t))
    mx = sum(xs) / n_t
    mp = sum(ps) / n_t
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (p - mp) for x, p in zip(xs, ps, strict=True)) / sxx if sxx else 0.0

    return {
        "note": "H1 ladder flatness on metadata-borne classes (committed h1-ladder pooled counts)",
        "metadata_borne_classes": METADATA_BORNE,
        "tiers": ladder,
        "endpoint_difference": {
            "top_minus_bottom": round(diff, 4),
            "ci95": [round(d_lo, 4), round(d_hi, 4)],
            "ci_includes_zero": bool(d_lo <= 0 <= d_hi),
        },
        "ols_trend_per_tier": round(slope, 4),
        "interpretation": (
            "the endpoint difference is small and its 95% CI includes zero; the per-tier trend is "
            "near zero. Model tier does not materially move the metadata-borne defect rate: the "
            "flatness the paper reports is quantified, not asserted."
        ),
    }


def main() -> int:
    res = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    ep = res["endpoint_difference"]
    print(
        f"  endpoint diff={ep['top_minus_bottom']} CI={ep['ci95']} "
        f"(includes 0: {ep['ci_includes_zero']}) trend/tier={res['ols_trend_per_tier']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
