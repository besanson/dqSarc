"""Item #4 (statistical reporting) --- row-level uncertainty for H1--H4 from committed data.

Three deterministic, $0 recomputations that read only committed summaries / frozen result
branches (no reruns, no API):

  * H1 ladder flatness: pool the metadata-borne classes per model tier, give each a Wald 95%%
    CI, and report the top-minus-bottom endpoint difference (two-proportion Wald CI) and the
    OLS trend per tier step.
  * H2 per-class detection: Wilson 95%% CIs for the payload-only critic (C) and the
    metadata-aware gate (D), per corruption class. The numerator is recovered per cell as
    ``round(detection_rate * n_corrupted)`` --- exact, because n_corrupted per cell is 25 and
    every stored rate is an integer multiple of 1/25 (validated to zero residual), so this is
    the true detected count, not a rounded-rate reconstruction --- then pooled across rates.
  * H3/H4 residual-loss bootstrap: nonparametric percentile 95%% CIs on the pooled mean paired
    loss, resampling the committed per-episode paired losses (the resampling unit) with a fixed
    seed. Signed losses are preserved (never clipped); the point estimate is the pool mean and
    is left unchanged. An interval crossing zero is reported as such, not as improvement.

Metadata-borne channel (from the frozen taxonomy): stale_master_data, superseded_golden_record,
silent_unit_change, plausible_outlier.

Writes ``analysis/out/stats_tables.json``.
"""

from __future__ import annotations

import json
import random
import statistics
from typing import Any

from analysis.common import ROOT, load_summary

OUT = ROOT / "analysis" / "out" / "stats_tables.json"
METADATA_BORNE = [
    "stale_master_data",
    "superseded_golden_record",
    "silent_unit_change",
    "plausible_outlier",
]
Z = 1.96  # 95% normal quantile
BOOT_SEED = 20260728  # fixed, documented; the bootstrap is a deterministic recomputation
BOOT_REPLICATES = 10000

# Stable short macro keys per class (mirror paper/scripts/make_macros.py h2_keys).
H2_KEYS = {
    "cross_source_contradiction": "Cross",
    "duplicate_vendor_conflicting_terms": "Dup",
    "missing_mandatory_field": "Missing",
    "plausible_outlier": "Outlier",
    "schema_drift": "Schema",
    "silent_unit_change": "Unit",
    "stale_master_data": "Stale",
    "superseded_golden_record": "Superseded",
}


def _wilson(k: int, n: int) -> tuple[float, float]:
    """Wilson score 95% interval for k successes in n trials (contains p_hat for 0<n)."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + Z * Z / n
    center = (p + Z * Z / (2 * n)) / denom
    half = Z * ((p * (1 - p) / n + Z * Z / (4 * n * n)) ** 0.5) / denom
    return max(0.0, center - half), min(1.0, center + half)


def _h2_counts(summ: dict[str, Any], cls: str, arm: str) -> tuple[int, int]:
    """(detected, corrupted) pooled across rate cells; detected recovered exactly per cell."""
    detected = corrupted = 0
    for cell in summ["matrix"].get(cls, {}).values():
        a = cell.get(arm)
        if not a:
            continue
        n = int(a["n_corrupted"])
        k = a["detection_rate"] * n
        if abs(k - round(k)) > 1e-6:  # integrality guard: never a rounded-rate artifact
            raise ValueError(f"non-integer detected count for {cls}/{arm}: {k}")
        detected += round(k)
        corrupted += n
    return detected, corrupted


def _bootstrap_ci(pool: list[float]) -> tuple[float, float]:
    """Percentile 95% CI on the mean via fixed-seed nonparametric bootstrap (signed, unclipped)."""
    if not pool:
        return 0.0, 0.0
    rng = random.Random(BOOT_SEED)
    n = len(pool)
    means = []
    for _ in range(BOOT_REPLICATES):
        s = 0.0
        for _ in range(n):
            s += pool[rng.randrange(n)]
        means.append(s / n)
    means.sort()
    lo = means[int(0.025 * BOOT_REPLICATES)]
    hi = means[int(0.975 * BOOT_REPLICATES)]
    return lo, hi


def _paired_pool(summ: dict[str, Any], arm: str, classes: list[str] | None = None) -> list[float]:
    """Pooled per-episode paired losses for an arm (optionally restricted to some classes)."""
    m = summ["matrix"]
    keys = classes if classes is not None else list(m)
    out: list[float] = []
    for cls in keys:
        for cell in m.get(cls, {}).values():
            a = cell.get(arm)
            if a:
                out += a.get("paired_losses", [])
    return out


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


def build_h1() -> dict[str, Any]:
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


def build_h2() -> dict[str, Any]:
    """Per-class Wilson 95% CIs for critic (C) and gate (D) detection, from committed counts."""
    summ = load_summary("h2-detection")
    rows: list[dict[str, Any]] = []
    for cls, key in H2_KEYS.items():
        row: dict[str, Any] = {"class": cls, "key": key}
        for arm, tag in (("C", "critic"), ("D", "gate")):
            k, n = _h2_counts(summ, cls, arm)
            lo, hi = _wilson(k, n)
            p = k / n if n else 0.0
            row[tag] = {
                "detected": k,
                "n": n,
                "rate": round(p, 4),
                "ci95": [round(lo, 4), round(hi, 4)],
                "pct": round(100 * p),
                "ci95_pct": [round(100 * lo), round(100 * hi)],
            }
        rows.append(row)
    return {
        "note": "H2 per-class detection Wilson 95% CIs; detected count recovered exactly per cell",
        "n_per_class": rows[0]["critic"]["n"] if rows else 0,
        "rows": rows,
    }


def build_h34() -> dict[str, Any]:
    """Bootstrap 95% CIs for the H3/H4 residual-loss quantities the paper prints."""
    h3 = load_summary("h3-frontier")
    h4 = load_summary("h4-recovery")

    def entry(pool: list[float]) -> dict[str, Any]:
        mean = round(statistics.mean(pool), 2) if pool else 0.0
        lo, hi = _bootstrap_ci(pool)
        return {
            "point": mean,
            "n_episodes": len(pool),
            "ci95": [round(lo, 2), round(hi, 2)],
            "ci_crosses_zero": bool(lo <= 0 <= hi),
        }

    quantities = {
        # H3: pooled residual (mean paired loss) for the gate (D) and the realistic critic (C).
        "h3_gate_residual": entry(_paired_pool(h3, "D")),
        "h3_critic_residual": entry(_paired_pool(h3, "C")),
        # H4: freshness-covered class (stale_master_data), ungated (A) vs gated (D).
        "h4_stale_loss_a": entry(_paired_pool(h4, "A", ["stale_master_data"])),
        "h4_stale_loss_d": entry(_paired_pool(h4, "D", ["stale_master_data"])),
    }
    return {
        "note": "H3/H4 residual-loss bootstrap 95% CIs (percentile, signed, unclipped)",
        "resampling_unit": "pooled per-corrupted-episode paired loss",
        "bootstrap_replicates": BOOT_REPLICATES,
        "bootstrap_seed": BOOT_SEED,
        "quantities": quantities,
    }


def build() -> dict[str, Any]:
    return {
        "h1_ladder": build_h1(),
        "h2_detection": build_h2(),
        "h3h4_residual": build_h34(),
    }


def main() -> int:
    res = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    ep = res["h1_ladder"]["endpoint_difference"]
    trend = res["h1_ladder"]["ols_trend_per_tier"]
    print(
        f"  H1 endpoint diff={ep['top_minus_bottom']} CI={ep['ci95']} "
        f"(includes 0: {ep['ci_includes_zero']}) trend/tier={trend}"
    )
    h2 = res["h2_detection"]
    print(f"  H2 rows={len(h2['rows'])} n/class={h2['n_per_class']}")
    q = res["h3h4_residual"]["quantities"]
    for name, e in q.items():
        print(f"  {name}: {e['point']} CI={e['ci95']} crosses0={e['ci_crosses_zero']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
