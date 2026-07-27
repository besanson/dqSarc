# VERIFICATION — 2026-07-13 — Stage 3 re-run (exp-h4-recovery, hardened harness)

Source: `results/h4-recovery-live` @ `a9a4b38` (run 30282599910), on hardened `main`
(`81e09d4`). Supersedes the INVALID cap-truncated run (`701c38e`, FINDINGS §8).

## STATUS: run VALID; **H4 (P1 recovery ≥ 0.80) NOT SUPPORTED** — reported per the
covered-vs-coverage-gap decomposition (as H2). No further H4 spend (user decision).

## V-run mechanical checks — ALL PASS (the hardening worked)
- config_hash `0d606d9b7730cc95` (matches addendum B); `instrumentation=api-error-aware-v1`.
- `policy_instructed`, `sampling=rate`, `fixed_n=None`, `paired-counterfactual-v2`, seed `20260707`.
- 96/96 cells, `stopped_early=None`, **`n_api_errors=0` in every cell**, all 8 classes
  called the model (each \$11–13 of spend). The cap-truncation failure mode is gone.
- Validity: 344 corrupted episodes scored across the matrix; completion 1.0 on the
  priceable classes; `missing_field`/`schema_drift` decline with rate (0.98→0.76) because
  their corrupted payloads carry no numeric price — a legitimate can't-price outcome, not
  an error, matching h1-full.
- No two rate cells byte-identical (sampler fix holds on real data).
- Spend **\$99.12** (within cap; on the \$92 grounded estimate).

## H4 result — P1 fails at the pre-registered portfolio endpoint
Registered (frozen): **P1 recovery = (loss_A − loss_D)/(loss_A − loss_E) ≥ 0.80**, reported
at the portfolio level (addendum C). Measured:

```
portfolio pooled (n=344 corrupted episodes):  loss_A = 283.9   loss_D = 295.6   loss_E = 0
portfolio recovery = (283.9 − 295.6) / (283.9 − 0) = −0.04     (target ≥ 0.80)  → NOT MET
```
The gate recovers essentially none of the *portfolio* loss (D ≈ A within noise). P2 (zero
source writes) and P3 (lineage completeness) hold by construction (the gate never writes to
source; every admitted action carries its evidence-set id), but the conjunctive H4 verdict
fails on P1.

## Why — the decomposition (this is the honest contribution, mirrors H2)
Per-class pooled loss with 95% paired-bootstrap CIs (n=43/class):

```
class                 loss_A [95% CI]           loss_D            reads as
silent_unit_change    2420 [1392, 3666]  ≠0     2421             uncovered gap — dominates the pool
stale_master_data      134 [ −30,  299]         −0.5 [−4, 2]     freshness: gate fully recovers (D→0)
superseded            −186 [−588,  169]           3              A not ≠0 — no loss to recover
plausible_outlier     −101 [−687,  477]         −99              coverage gap; A not ≠0
cross_source           −35 [−451,  390]           0              A not ≠0
duplicate_vendor        39 [−472,  556]          41              A not ≠0
missing_field / schema_drift   0                  0              can't price → no action → no loss
```

Two honest facts drive the portfolio miss:
1. **The dominant loss is a pre-registered coverage gap.** `silent_unit_change` (a
   within-payload unit rescaling with clean metadata) is the **only** class whose ungated
   loss is clearly non-zero (CI excludes 0), and it is exactly the defect the metadata-aware
   gate has **no predicate** for (unit-consistency is v1.1 future work, addendum D). Its
   magnitude (~\$2.4k) swamps the magnitude-weighted portfolio pool, so recovery ≈ 0. This is
   **structural, not statistical** — more episodes cannot move it.
2. **n=100 (rate axis) is underpowered for the covered classes.** Every other class's `loss_A`
   CI spans 0, so there is no established loss to recover. Where the gate *does* have a
   predicate (freshness → `stale_master_data`) it visibly zeroes the loss (D: 134 → −0.5), but
   that is the only covered class with even marginal signal at this n.

## Reported conclusion (paper wording)
H4 as registered ("the gate recovers ≥ 80% of downstream loss") is **not supported**. The
defensible result, consistent with the H2 channel-boundary reframe: **the gate fully recovers
the loss it covers (freshness) and is transparent about its named coverage gaps (unit-scaling,
outliers) — which happen to carry the largest raw magnitude.** The decomposition, not an 80%
headline, is the contribution. To be stated verbatim in the paper's Results and the
"Deviations and clarifications" section; no threshold or endpoint was altered.

## Next
Proceed to stage 4 (`exp-h3-frontier`) — a distinct hypothesis (loss-avoided vs false-block
frontier), unaffected by the H4 outcome. Ledger after this stage: h4 re-run overwrote the
\$23 INVALID with \$99; running committed total re-checked before the ladder.
