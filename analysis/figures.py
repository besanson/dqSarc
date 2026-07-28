"""Item #11 --- publication-quality figures, auto-generated from the committed analysis JSON.

Every figure is a deterministic render of an ``analysis/out/*.json`` file (which are themselves
deterministic recomputations of committed data). No figure introduces a new number; each one
visualises a value the corresponding module already wrote. Vector PDF (for the paper) plus a
PNG preview are emitted to ``paper/figures/analysis/``.

Requires the ``figures`` extra (matplotlib). Kept out of the core/experiment/paper-macro path.
"""

from __future__ import annotations

import json
from typing import Any

import matplotlib

matplotlib.use("Agg")  # headless; deterministic raster/vector output
import matplotlib.pyplot as plt  # noqa: E402

from analysis.common import ROOT  # noqa: E402

OUT_JSON = ROOT / "analysis" / "out"
FIGDIR = ROOT / "paper" / "figures" / "analysis"

plt.rcParams.update(
    {
        "figure.dpi": 150,
        "font.size": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "savefig.bbox": "tight",
        # Deterministic vector output: drop the per-run creation timestamp and pin the
        # SVG hash salt so `make analysis` is byte-identical on repeat runs.
        "pdf.fonttype": 42,
        "svg.hashsalt": "sarc-dq",
    }
)
_BLUE, _RED, _GREY = "#2b6cb0", "#c53030", "#718096"
# metadata=None date -> matplotlib omits the CreationDate/ModDate (otherwise non-deterministic).
_PDF_META = {"CreationDate": None}
_PNG_META = {"Software": None}


def _load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((OUT_JSON / name).read_text())
    return data


def _save(fig: plt.Figure, stem: str) -> None:
    FIGDIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGDIR / f"{stem}.pdf", metadata=_PDF_META)
    fig.savefig(FIGDIR / f"{stem}.png", metadata=_PNG_META)
    plt.close(fig)


def fig_conversion() -> None:
    d = _load("conversion_law.json")
    rows = d["rows"]
    pred = [r["predicted_oracle"] for r in rows]
    meas = [r["measured_adr"] for r in rows]
    fig, ax = plt.subplots(figsize=(3.4, 3.2))
    lo, hi = min(pred + meas + [0.0]), max(pred + meas + [1.0])
    ax.plot([lo, hi], [lo, hi], "--", color=_GREY, lw=1, label="perfect calibration")
    ax.scatter(pred, meas, s=28, color=_BLUE, zorder=3, edgecolor="white", linewidth=0.5)
    ax.set_xlabel("predicted oracle conversion")
    ax.set_ylabel("measured agent ADR")
    ax.set_title(
        f"Conversion law calibration\nMAE={d['mean_abs_error']}, "
        f"r={d['pearson_pred_vs_measured']}, CI cover {d['ci_coverage']}"
    )
    ax.legend(loc="upper left", fontsize=7, frameon=False)
    _save(fig, "conversion_calibration")


def fig_coverage() -> None:
    d = _load("coverage_accounting.json")
    rows = d["rows"]
    labels = [r["class"] for r in rows]
    den = [r["den_contribution"] for r in rows]
    colors = [_BLUE if r["covered"] else _RED for r in rows]
    fig, ax = plt.subplots(figsize=(5.0, 3.2))
    ax.barh(range(len(labels)), den, color=colors)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("weighted denominator contribution (recoverable $)")
    ax.set_title(
        f"H4 coverage accounting: {d['dominant_class']} is "
        f"{int(round(100 * d['dominant_den_share']))}% of the pool"
    )
    ax.legend(
        handles=[
            plt.Rectangle((0, 0), 1, 1, color=_BLUE, label="gate-covered"),
            plt.Rectangle((0, 0), 1, 1, color=_RED, label="uncovered gap"),
        ],
        loc="lower right",
        fontsize=7,
        frameon=False,
    )
    _save(fig, "coverage_accounting")


def fig_threshold() -> None:
    d = _load("robustness.json")["threshold_sensitivity"]
    curve = d["curve"]
    taus = [c["tau_m"] for c in curve]
    adrs = [c["mean_oracle_adr"] for c in curve]
    fig, ax = plt.subplots(figsize=(3.4, 3.0))
    ax.plot(taus, adrs, "-o", color=_BLUE)
    ax.axvline(d["registered_tau_m"], color=_RED, ls="--", lw=1, label="registered $\\tau_m$")
    ax.set_xscale("log")
    ax.set_xlabel("materiality threshold $\\tau_m$")
    ax.set_ylabel("mean oracle ADR")
    ax.set_title("Threshold sensitivity")
    ax.legend(fontsize=7, frameon=False)
    _save(fig, "threshold_sensitivity")


def fig_loo() -> None:
    d = _load("robustness.json")["loo"]
    rows = d["leave_one_out"]
    labels = [r["excluded"] for r in rows]
    rec = [r["recovery"] for r in rows]
    fig, ax = plt.subplots(figsize=(5.0, 3.2))
    colors = [_BLUE if v >= 0 else _RED for v in rec]
    ax.barh(range(len(labels)), rec, color=colors)
    ax.axvline(d["full_recovery"], color=_GREY, ls="--", lw=1, label="full portfolio")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels([f"drop {x}" for x in labels], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("portfolio recovery with class removed")
    ax.set_title("Leave-one-class-out")
    ax.legend(fontsize=7, frameon=False)
    _save(fig, "leave_one_out")


def fig_stress() -> None:
    d = _load("stress.json")
    modes = d["modes"]
    rows = d["rows"]
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    import numpy as np

    mat = np.array([[r[m] for m in modes] for r in rows])
    im = ax.imshow(mat, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(modes)))
    ax.set_xticklabels(modes, rotation=30, ha="right", fontsize=7)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r["class"] for r in rows], fontsize=7)
    for i in range(len(rows)):
        for j in range(len(modes)):
            ax.text(j, i, f"{mat[i, j]:.2f}", ha="center", va="center", fontsize=6)
    ax.grid(False)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="gate detection rate")
    ax.set_title("Metadata-degradation stress (detection)")
    _save(fig, "stress_degradation")


def fig_falsification() -> None:
    d = _load("falsification.json")["recovered_fraction"]
    labels = list(d.keys())
    vals = [d[k] for k in labels]
    colors = [_BLUE if k == "gate_real" else _GREY for k in labels]
    fig, ax = plt.subplots(figsize=(3.6, 3.0))
    ax.bar(range(len(labels)), vals, color=colors)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=25, ha="right", fontsize=7)
    ax.set_ylabel("recovered positive-loss fraction")
    ax.set_title("Falsification: same budget, different targets")
    _save(fig, "falsification")


def fig_second_domain() -> None:
    d = _load("second_domain.json")
    rows = d["rows"]
    labels = [r["class"] for r in rows]
    adr = [r["adr"] for r in rows]
    rec = [r["gate_recovered_fraction"] for r in rows]
    x = range(len(labels))
    fig, ax = plt.subplots(figsize=(5.4, 3.2))
    w = 0.4
    ax.bar([i - w / 2 for i in x], adr, w, color=_RED, label="ADR (ungated)")
    ax.bar([i + w / 2 for i in x], rec, w, color=_BLUE, label="gate recovery")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=25, ha="right", fontsize=7)
    ax.set_ylabel("rate")
    ax.set_title("Second domain: B2C promotion eligibility")
    ax.legend(fontsize=7, frameon=False)
    _save(fig, "second_domain")


FIGURES = [
    fig_conversion,
    fig_coverage,
    fig_threshold,
    fig_loo,
    fig_stress,
    fig_falsification,
    fig_second_domain,
]


def main() -> int:
    for f in FIGURES:
        f()
    names = sorted(p.name for p in FIGDIR.glob("*.pdf"))
    print(f"wrote {len(names)} figures to {FIGDIR.relative_to(ROOT)}")
    for n in names:
        print(f"  {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
