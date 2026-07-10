# VERIFICATION — 2026-07-10 — Stage 2 (exp-h2-detection, corrected re-run)

Source: `results/h2-detection-live` @ `aac7518` (run 29101951327).

## V-run checks — ALL PASS
- Config stamp: `policy_instructed`, `fixed_n=25`, `paired-counterfactual-v2`,
  `config_hash=b52ba463e0e1b9b4` (self-consistent). 96/96 cells; `stopped=None`.
- Validity: 0 errors → 100% scored (≥ 80% floor).
- Non-degenerate: no two rate-label cells byte-identical.

## H2 verdict (committed verdict code) — NOT SUPPORTED, reframed (as FINDINGS §5)
```
schema_drift              pv    C0.00 D1.00  FAIL P1 (gate strictly dominates)
missing_mandatory_field   pv    C0.72 D1.00  FAIL P1 (|C-D|=0.28)
plausible_outlier         META  C0.00 D0.00  FAIL P2 (coverage gap)
silent_unit_change        META  C0.00 D0.00  FAIL P2 (coverage gap)
superseded_golden_record  META  C1.00 D1.00  FAIL P2 (payload-detectable; mislabeled)
stale_master_data         META  C0.00 D1.00  pass P2 (gate catches freshness, critic can't)
cross_source, duplicate   pv                 pass P1
```
Strict conjunction fails; the reframe (empirical channel boundary; gate dominates on
schema/freshness; two named coverage gaps) is confirmed on corrected data.

## BUDGET FLAG — estimates running low; Fable-trim now mandatory
h2 actual **$122.93** vs $69 estimate (1.8x; opus critic + long prompts). True money
spent (incl. overwritten invalid runs, ~$88.82) ≈ **$475**. Remaining re-runs
(h4 ~$105, h3 ~$130, ladder ~$325 untrimmed) → projected **~$1,035 untrimmed
(BREACH)** / **~$948 with the C.1 Fable-trim**. Per addendum C.1 the Fable-trim is
required; margin is thin (±30% estimate uncertainty), so re-assess the ledger before
h3 and the ladder, and if halving Fable once is insufficient, STOP and report.

## STATUS: STAGE 2 PASS. Budget tight — proceed to stage 3 (exp-h4-recovery), re-assess after.
