# Post-hoc analytical layer (`analysis/`)

Deterministic, **$0**, no-API recomputation that *explains* the committed results — it never
replaces them. Every number and figure here is derived from the frozen substrate
(`sarc_dq.substrate`, seeded), the frozen injectors (`sarc_dq.taxonomy`), and the committed
`results/<exp>-live` summaries (read via `git show`). No experiment is rerun, no threshold or
verdict is changed, no committed value is edited.

Run everything:

```bash
pip install -e ".[figures]"   # matplotlib + numpy (only needed for the plots)
make analysis                 # == python -m analysis.run_all
```

Outputs:

- `analysis/out/*.json` — one file per analysis (audit-ready intermediate values).
- `paper/figures/analysis/*.pdf` (+ `.png`) — publication figures.
- `paper/generated/analysis.tex` — the `\newcommand` macros the paper's
  Appendix (`\ref{app:analysis}`) prints; nothing is hand-typed.

## Modules (map to the reviewer's items)

| module | item | what it shows |
|---|---|---|
| `conversion_law.py` | #1 | closed-form newsvendor conversion vs measured ADR (MAE 0.015, r 0.88); model-independence (M2) |
| `coverage_accounting.py` | #2 | H4 recovery = Σ wₖ·lossₖ identity; reproduces the reported recovery exactly (residual 0) |
| `stats_tables.py` | #4 | H1 ladder flatness: endpoint difference + Wald CI (includes 0) + OLS trend |
| `robustness.py` | #4,#5,#6 | leave-one-class-out, predicate ablations, materiality-threshold sensitivity |
| `stress.py` | #7 | real gate detection under metadata degradation (freshness collapses when the clock is erased) |
| `falsification.py` | #8 | same intervention budget, different targets: the benefit is targeting, not frequency |
| `second_domain.py` | #10 | B2C promotion-eligibility task reusing the same predicate family (portability, not universal win) |
| `figures.py` | #11 | renders all figures from the JSON above |
| `make_analysis_macros.py` | — | JSON → `paper/generated/analysis.tex` macros |
| `run_all.py` | — | orchestrator (`make analysis`) |

`common.py` holds the shared, deterministic helpers (seeded episode reconstruction, the oracle
newsvendor geometry, committed-summary loading, the class→predicate coverage map).

## Scope note

This package is intentionally **outside** the CI lint/type/test scope (`src tests benchmarks
scripts paper/scripts`) and outside the core dependency set: it is a post-hoc companion, needs
the optional `figures` extra, and must never be on the path of the core, the experiments, or the
paper's result-macro pipeline. It is kept `ruff`/`mypy`-clean regardless.
