# VERIFICATION — 2026-07-13 — Stage 4 (exp-h3-frontier, hardened harness)

Source: `results/h3-frontier-live` @ `9bfff1f` (run 30296664147), on hardened `main`.
Supersedes the first-wave INVALID run (`0a6f545`).

## STATUS: run VALID; **H3 P1 (D Pareto-dominant over B/C/F) NOT SUPPORTED as written**.
The fair, defensible finding — D dominates the realistic payload-only critic C — holds and
is reported. No threshold or endpoint altered.

## V-run mechanical checks — ALL PASS
- config_hash `32c0c09dd052f859`; `instrumentation=api-error-aware-v1`.
- `policy_instructed`, `sampling=rate` (correct for H3 per addendum C), `paired-counterfactual-v2`,
  seed `20260707`, axis `[C, D, F]`.
- 96/96 cells, `stopped_early=None`, **`n_api_errors=0` in every cell**, all 8 classes ran
  (\$13–15 each), no two rate cells byte-identical. Spend **\$115.16** (on the ~\$120 estimate).

## H3 result — the frontier at n=100
Portfolio-pooled per arm (residual loss on corrupted; false-block on clean):

```
arm                     mean_residual_loss   false_block   detection   completion
C (payload critic)              311.41          0.000         0.314        0.946
D (DQ pre-action gate)          293.95          0.000         0.625        0.960
F (velocity-clean, v=0.5)       143.49          0.000         0.000        0.987
```

**Two reasons the literal P1 (D Pareto-dominant over B, C, and F(v)) is not supported:**

1. **The false-block axis is degenerate.** Every arm false-blocks at 0.000 — no arm ever
   blocks a clean episode — so there is no frontier to trace; the comparison collapses to
   residual loss alone. D never false-blocking is a genuine precision-1.0 property, but it
   means no operating-point sweep emerges at this n.
2. **F beats D on residual loss, but F is a partial oracle — not a fair competitor.** Arm F
   ("reactive cleaning at velocity v") substitutes the **true price** (`unit_cost = true_p`,
   `live_arms.py`) on 50% of corrupted episodes. It therefore has ground-truth access for the
   fraction it cleans, including `silent_unit_change`, the defect no detector can catch. Its
   lowest residual loss is blind laundering of the uncatchable dominant loss using the answer
   key; requiring the gate to dominate a half-oracle is not a fair test. F is best read as an
   upper reference, not a realistic baseline.

## The fair, defensible finding (reported)
Against the **realistic** baseline — C, the payload-only critic with no ground truth — **D
dominates**: lower residual loss (293.9 vs 311.4), **2× detection** (0.625 vs 0.314), at the
same zero false-block. Per class, D fully zeroes the freshness loss C cannot see
(`stale_master_data`: C 134.5 → D −1.3). This is the same metadata-channel advantage as H2 —
the gate acts on freshness/provenance the payload-only critic is structurally blind to.

As with H4, the residual-loss axis is dominated by `silent_unit_change` (the pre-registered
coverage gap the gate has no predicate for), which is why neither realistic arm drives the
portfolio residual to zero.

## Reported conclusion (paper wording)
H3 as registered (D Pareto-dominant over B/C/F(v) on the loss-avoided vs false-block frontier)
is **not supported**: the false-block axis is degenerate (all arms 0), and F(v) as implemented
is a partial oracle. The defensible result is that **the pre-action gate dominates the
realistic payload-only critic (lower residual loss, 2× detection, zero false-block), driven by
the metadata channel** — consistent with H2 and H4 — while the portfolio residual remains
dominated by the named `silent_unit_change` coverage gap. Reported verbatim in Results and
"Deviations and clarifications."

## Next
Stage 5 (`exp-h1-ladder`) — silence vs capability, a distinct hypothesis. Re-check the ledger
(h3 committed \$115) and decide full-scale vs Fable-trim before firing.
