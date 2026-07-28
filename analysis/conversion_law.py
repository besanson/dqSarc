"""Item #1 --- the analytical conversion law and its calibration against measurement.

Oracle layer (closed form, model-independent): the newsvendor optimum for the *shown*
price gives, per corrupted episode, a decision shift, an induced paired loss, and a
materiality flag. The per-cell mean is the predicted oracle conversion probability.

Agent layer: the measured LLM policy has decision elasticity eta ~= 0.99 (Phase 0c), so it
tracks the shown price nearly as faithfully as the oracle. We therefore predict the measured
metadata-borne ADR by the oracle conversion, and *calibrate* (not force-fit) the two.

Model tier does not enter the oracle equation at all --- the corrupted price the agent is
shown is the same regardless of model --- which is the analytical form of M2.

Writes ``analysis/out/conversion_law.json`` (calibration table + errors + CI overlap).
Deterministic; reads committed data only.
"""

from __future__ import annotations

import json
import statistics
from typing import Any

from analysis.common import ROOT, load_summary, oracle_conversion

OUT = ROOT / "analysis" / "out" / "conversion_law.json"
# Metadata-borne classes carry a priced corruption; the two structural classes
# (schema_drift, missing_mandatory_field) carry no numeric price -> no conversion geometry.
PRICED_META = [
    "silent_unit_change",
    "stale_master_data",
    "superseded_golden_record",
    "plausible_outlier",
]
RATE_KEYS = ["0.02", "0.05", "0.10", "0.20"]


def _measured_cells(
    summ: dict[str, Any], arm_or_model: str
) -> dict[tuple[str, str], dict[str, Any]]:
    m = summ["matrix"]
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for cls, rates in m.items():
        for rk, per in rates.items():
            cell = per.get(arm_or_model)
            if cell is not None:
                out[(cls, rk)] = cell
    return out


def build() -> dict[str, Any]:
    # Measured agent ADR: h1-full (arm A) is the primary single-model reference.
    h1 = load_summary("h1-full")
    measured = _measured_cells(h1, "A")

    rows: list[dict[str, Any]] = []
    preds: list[float] = []
    meas: list[float] = []
    for cls in PRICED_META:
        for rk in RATE_KEYS:
            cell = measured.get((cls, rk))
            if cell is None:
                continue
            pred = oracle_conversion(cls, float(rk), fixed_n=True)
            adr = float(cell["adr"])
            n = int(cell["n_corrupted"])
            # Wald 95% CI on the measured ADR (n corrupted, binomial).
            se = (adr * (1 - adr) / n) ** 0.5 if n else 0.0
            lo, hi = max(0.0, adr - 1.96 * se), min(1.0, adr + 1.96 * se)
            rows.append(
                {
                    "class": cls,
                    "rate": rk,
                    "n": n,
                    "predicted_oracle": round(pred, 4),
                    "measured_adr": round(adr, 4),
                    "abs_error": round(abs(pred - adr), 4),
                    "rel_error": round(abs(pred - adr) / adr, 4) if adr else None,
                    "ci95": [round(lo, 4), round(hi, 4)],
                    "ci_covers_prediction": bool(lo <= pred <= hi),
                }
            )
            preds.append(pred)
            meas.append(adr)

    # Aggregate calibration diagnostics.
    n = len(rows)
    mae = round(statistics.mean(float(r["abs_error"]) for r in rows), 4) if rows else None
    covered = sum(1 for r in rows if r["ci_covers_prediction"])
    # Pearson correlation between prediction and measurement.
    if n >= 2:
        mp, mm = statistics.mean(preds), statistics.mean(meas)
        cov = sum((p - mp) * (q - mm) for p, q in zip(preds, meas, strict=True))
        sp = sum((p - mp) ** 2 for p in preds) ** 0.5
        sm = sum((q - mm) ** 2 for q in meas) ** 0.5
        pearson = round(cov / (sp * sm), 4) if sp and sm else None
    else:
        pearson = None
    return {
        "note": "oracle conversion (closed-form newsvendor) vs measured agent ADR, h1-full arm A",
        "elasticity_bridge": "agent eta ~= 0.99 (Phase 0c): agent tracks shown price near-oracle",
        "rows": rows,
        "n_cells": n,
        "mean_abs_error": mae,
        "ci_coverage": f"{covered}/{n}",
        "pearson_pred_vs_measured": pearson,
    }


def main() -> int:
    res = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(
        f"  cells={res['n_cells']} MAE={res['mean_abs_error']} "
        f"CI-coverage={res['ci_coverage']} r={res['pearson_pred_vs_measured']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
