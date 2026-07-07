# GIGO-Bench

**GIGO-Bench** ("garbage in, garbage out") measures how injected data corruption
converts into agent **action defects** and **financial loss**, and how much of
that loss each mitigation strategy recovers. It is the empirical instrument
behind the paper's H1–H4 claims. The frozen, authoritative specification is
[`benchmarks/gigo/SPEC.md`](../benchmarks/gigo/SPEC.md); this page is the
orientation.

## What it measures

The unit of observation is an **episode**: a priced newsvendor replenishment
decision (see [architecture.md](architecture.md)) run against evidence that may
carry an injected defect. For each corrupted episode the realised currency loss
is measured against the **same-seed clean counterfactual**, so loss is causal —
the difference the corruption made, not noise between runs.

The headline outcome is the **Action-Defect Rate (ADR)**: the fraction of
corrupted, completed episodes whose loss exceeds a materiality threshold
(τ_m = 0.5% of clean cost). ADR is what turns "the data was wrong" into "the
agent did something wrong."

## The conditions matrix

**corruption class × corruption rate × mitigation arm** = 8 × 4 × 6 = **192 cells**.

- **8 corruption classes** (taxonomy v0), each tagged `payload-visible` or
  `metadata-borne` — the split that makes H2 (detection asymmetry) falsifiable.
- **4 rates**: {2%, 5%, 10%, 20%} of episodes carry the defect.
- **6 arms**: A no-gate · B prompt-advisory · C payload-only critic ·
  D DQ Pre-Action Gate · E oracle clean source · F(v) upstream cleaning.

Every arm sees the **same** corrupted/clean assignment for a given episode index
(seeds derive deterministically from the episode index), so arms are compared on
identical workloads. A workload-level `split_of(seed) ∈ {train, calibration,
test}` keeps trajectories from crossing a split boundary.

## What each hypothesis reads

| hypothesis | what the matrix shows |
|---|---|
| **H1** (harm) | ADR and loss rise with rate under arm A; the gate (D) flattens them. |
| **H2** (detection asymmetry) | the payload-only critic (C) cannot detect metadata-borne defects; the metadata-aware gate (D) can. |
| **H3** (frontier) | loss-avoided vs false-block trades off across arms; D dominates B/C. |
| **H4** (recovery) | `recovery_ratio = (effA − effD)/(effA − effE)` — the fraction of avoidable loss the gate recovers (target ≥ 0.80). |

## Running it

```bash
make gigo-reproduce   # run the matrix, write benchmarks/gigo/reference_summary.json
make gigo-verify      # re-run and check every cell against the frozen reference
```

`gigo-verify` exits non-zero on any cell drifting past tolerance (rates/ratios
abs 0.02, losses rel 0.02); CI runs it on every push.

## Mock vs. live

The checked-in `reference_summary.json` is the **deterministic mock** matrix: a
pipeline reference proving the 192 cells run and the metrics wire up end-to-end at
**$0**. It is *not* a scientific result — the mock agent, critic, and judge are
fixed stand-ins. The live H1–H4 numbers come from the Part-4 experiment kits
(`.github/workflows/exp-*.yml`), which wire real Claude models into the arms,
print spend, and write `results/<exp>-live` branches that feed the paper macros.
Injector rates and patterns are calibrated to Tier-2 empirical data per
[`benchmarks/gigo/CALIBRATION.md`](../benchmarks/gigo/CALIBRATION.md).
