# Relationship to Green SARC

[Green SARC](https://github.com/besanson/greensarc) applies the SARC four-site
architecture to cost + carbon: a predictive Pre-Action Gate that forecasts an
action's token/USD/carbon cost before it fires. SARC-DQ borrows Green SARC's
**engineering discipline and its environment**, and shares its headline thesis
(*enforcement placement beats model intelligence*).

What SARC-DQ reuses:

- **The IBP environment** — Green SARC's `benchmarks/ibp.py` is a fan-out
  replenishment workload, but it is a **pure token-cost simulation: no LLM is
  called**. SARC-DQ extends the *domain* into a real, LLM-driven decision: a
  priced single-period newsvendor order whose quality depends on a corruptible
  unit price (`sarc_dq.substrate`). Same domain, opposite emphasis — Green SARC
  prices the *tokens*, SARC-DQ prices the *decision*.
- **Reproducibility patterns** — `make reproduce` / `make verify`, a checked-in
  reference summary with per-metric tolerance checks, seeded config hashes, and
  CI running verify on every push are mirrored directly (`reports/reference_smoke.json`,
  `benchmarks/phase0_smoke.py --verify`).
- **Paired-bootstrap statistics** — the paired-seed bootstrap CI in
  `sarc_dq.metrics` follows Green SARC's `benchmarks/reproduce.py`.
- **Conformal calibrators** — Green SARC's split/adaptive conformal calibrators
  will back the Phase 4 staleness-bound coverage result (nominal 95%).

The shared narrative: Green SARC found that most savings come from *where*
enforcement sits, not from rejection. SARC-DQ tests the analogous claim for
evidence quality — that a cheap **metadata-aware** gate beats a frontier-class
**payload-only** critic, because the discriminating signal was never in the
model's context to begin with.
