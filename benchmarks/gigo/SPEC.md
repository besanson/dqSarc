# GIGO-Bench — Specification (frozen)

**GIGO-Bench** measures how injected data corruption converts into agent action
defects and financial loss, across mitigation strategies. This spec is frozen;
changes are versioned.

## Conditions matrix

**corruption class × corruption rate × mitigation arm**

- **classes (8, taxonomy v0):** `stale_master_data`, `superseded_golden_record`,
  `silent_unit_change`, `duplicate_vendor_conflicting_terms`,
  `cross_source_contradiction`, `schema_drift`, `missing_mandatory_field`,
  `plausible_outlier` (channel tags in `reports/TAXONOMY_V0.md`).
- **rates:** {2%, 5%, 10%, 20%} — fraction of episodes carrying the class's defect.
- **arms (6):** A no-gate · B prompt-advisory · C payload-only critic
  (⟨CRITIC_MODEL⟩=claude-opus-4-8) · D DQ Pre-Action Gate · E oracle clean source ·
  F(v) upstream cleaning at velocity v.

8 × 4 × 6 = **192 cells**. The reference is `reference_summary.json`.

## Seeds

Per-episode seed `= (base_seed × 1_000_003 + i) mod 2³¹`, `base_seed = 20260707`.
The corruption draw, the injection draw, and the arm draw derive from it
(`seed`, `seed+1`, `seed+2`) so every arm sees the **same** corrupted/clean
assignment for a given episode index — arms are compared on identical workloads.
**Workload-level split:** `split_of(seed) ∈ {train, calibration, test}` by
`seed mod 3`; trajectories from one workload never cross a split boundary.

## Metrics (per cell)

| metric | definition |
|---|---|
| `adr` | fraction of corrupted+completed episodes with material loss (≥ τ_m = 0.5% of clean cost) |
| `loss_mean_corrupted` / `loss_quantiles` | realised currency loss vs the same-seed clean counterfactual (median/P90/P99/mean) |
| `loss_eff_corrupted` | mean loss over **all** corrupted episodes (blocked/escalated = avoided = 0) — the basis for recovery |
| `detection_rate` | fraction of corrupted episodes the arm flagged |
| `false_block_rate` | fraction of **clean** episodes the arm refused (false positive) |
| `completion_rate` | fraction of all episodes that executed an autonomous action |
| `recovery_ratio` (arm D) | `(effA − effD)/(effA − effE)`, effE ≈ 0 — H4 target ≥ 0.80 |
| gate overhead latency | wall-clock per gate decision (measured live; the mock is O(µs)) |
| staleness-bound coverage | conformal empirical coverage at nominal 95% (Part 4 `h4`/conformal) |

## Scoring

`python -m benchmarks.gigo.reproduce` runs the matrix and writes the summary;
`--verify <ref>` re-runs and checks every cell against the reference (rates/ratios
abs tol 0.02, losses rel tol 0.02), exiting 2 on drift. CI runs verify on every
push (`make gigo-verify`).

## reference_summary.json schema

```
{ "config": {n_episodes, base_seed, tau_m, velocity, rates[], arms[]},
  "matrix": { "<class>": { "<rate>": { "<arm>": {
      adr, detection_rate, false_block_rate, completion_rate,
      loss_mean_corrupted, loss_eff_corrupted,
      loss_quantiles:{median,p90,p99,mean}, recovery_ratio, n_corrupted } } } } }
```

## Status

The checked-in `reference_summary.json` is the **deterministic mock** matrix — a
pipeline reference proving the conditions run and the metrics wire up, **not** a
scientific result. The live H1–H4 numbers come from the Part-4 experiment kits
(`.github/workflows/exp-*.yml`) and land on `results/<exp>-live` branches.
Injector rates and patterns are calibrated to Tier-2 empirical data per
`CALIBRATION.md`.
