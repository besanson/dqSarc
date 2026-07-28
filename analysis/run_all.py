"""Orchestrator for the post-hoc analytical layer (``make analysis``).

Runs every deterministic, $0 recomputation module in order, writing its JSON to
``analysis/out/``, then renders the publication figures and emits the paper macro file
``paper/generated/analysis.tex``. No experiment is rerun, no committed value is altered,
no network or API is touched: every number is recomputed from the frozen substrate,
frozen injectors, and committed result summaries.
"""

from __future__ import annotations

from analysis import (
    conversion_law,
    coverage_accounting,
    falsification,
    figures,
    make_analysis_macros,
    robustness,
    second_domain,
    stats_tables,
    stress,
    transcript,
)
from analysis.common import ROOT

STAGES = [
    ("conversion law (#1)", conversion_law.main),
    ("H4 coverage accounting (#2)", coverage_accounting.main),
    ("statistical reporting: H1/H2/H3/H4 intervals (#4)", stats_tables.main),
    ("robustness: LOO / ablations / threshold (#4,#5,#6)", robustness.main),
    ("metadata-degradation stress (#7)", stress.main),
    ("falsification controls (#8)", falsification.main),
    ("second domain: B2C promotion (#10)", second_domain.main),
    ("verbatim transcript excerpt + provenance", transcript.main),
    ("publication figures (#11)", figures.main),
    ("paper macros -> generated/analysis.tex", make_analysis_macros.main),
]


def main() -> int:
    print(f"post-hoc analytical layer (deterministic, $0) --- root={ROOT}")
    for label, fn in STAGES:
        print(f"\n== {label} ==")
        rc = fn()
        if rc != 0:
            print(f"stage failed: {label}")
            return rc
    print("\nall analysis stages complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
