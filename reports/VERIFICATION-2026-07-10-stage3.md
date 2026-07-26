# VERIFICATION — 2026-07-10 — Stage 3 (exp-h4-recovery, corrected re-run) — **FAIL**

Source: `results/h4-recovery-live` @ `701c38e` (run 29113332323), on merged base `fa3b6af`.

## STATUS: STAGE 3 FAIL — run INVALID (API spend cap truncated it mid-run).
Per the FIRING_PLAN FAILURE PROTOCOL: stop, commit this report, spend nothing,
**do not fire stage 4**. The recovery ratio in this summary (portfolio 6.14) is an
artifact of empty cells and must not be reported as a result.

## What the summary claims vs. what actually ran
The committed summary *looks* complete — `cells_done=96/96`, `stopped_early=None`,
`config_hash=0d606d9b7730cc95` (matches addendum B: `policy_instructed`, `rate`,
`paired-counterfactual-v2`, seed `20260707`, sonnet-5/opus-4-8). But only **2 of 8
corruption classes actually called the model**:

```
class (registration order)              cells with real API spend
1  cross_source_contradiction           12/12   ✓ ran
2  duplicate_vendor_conflicting_terms   11/12   ← cap hit during the 12th cell
3  missing_mandatory_field               0/12   ✗ zero API calls
4  plausible_outlier                     0/12   ✗
5  schema_drift                          0/12   ✗
6  silent_unit_change                    0/12   ✗
7  stale_master_data                     0/12   ✗
8  superseded_golden_record              0/12   ✗
total_usd = $23.07  (all of it on classes 1–2)
```

A **perfect prefix cutoff in registration order**: everything up to duplicate_vendor's
last cell ran; everything after it got **0 input tokens, 0 output tokens, $0**. That is
the signature of an Anthropic **spend/credit cap** being reached ~$23 into the run
(stages 1–2 had already spent ~$158: h1 $35 + h2 $123), not a science bug.

## Why it looked like a "recovery ratio anomaly"
For the 6 capped classes every corrupted episode returned `completed=False` (agent never
acted), so `eff_losses` recorded `0.0` for all of them (experiments.py:181). Arms A/D/E
all read 0.0 → recovery `(effA−effD)/(effA−effE)` is `0/0` (undefined) for 6 classes,
and the 2 classes that *did* run (duplicate's large ±1000 paired noise) dominate the
portfolio pool → nonsensical pooled ratio **6.14**. Nothing was wrong with the estimator;
75% of its input was silently missing.

## Proof it is the cap, not a code/injector defect
- **Same code, offline, all 8 classes build a valid agent view.** `fa3b6af`'s `src/` is
  byte-identical to current HEAD (`git diff --stat fa3b6af HEAD -- src/` = empty).
  Reproducing every corrupted episode of silent_unit_change / plausible_outlier /
  stale_master_data / superseded_golden_record offline: **0 KeyErrors, valid `unit_cost`
  in every payload** (schema_drift & missing_field legitimately raise KeyError — they
  carry no numeric price — and are 0 in h1-full too, as expected).
- **Fake pipeline (`--fake`, $0) under current code completes 8/8 classes** with the
  expected losses (silent_unit_change loss_eff ≈ 2080, ADR 0.75), matching the strong
  h1-full signal for those classes. So the harness, injectors, sampler and recovery fill
  are all correct.
- **The signature is a class-boundary cutoff**, not stochastic refusals: an infra outage,
  not model behaviour.

## Harness hole this exposed (fabrication-by-omission risk)
When the API raises (cap/credit/transport), `agent/anthropic_agent.py:103-108` swallows
the exception into `AgentDecision(outcome=OUTCOME_ERROR, usd=0)` **and does not re-raise**.
The runner's worker only counts an error when the call *raises* (`experiments.py:143`), so
`errors_total` stays 0, `error_budget=16` never trips, `stopped_early` stays `None`, and a
total API outage is committed as "96 cells, recovery 6.14." This must be hardened before
any re-fire: an API-transport error must be counted (so `error_budget` aborts and the run
resumes from the cap point) rather than recorded as a silent zero-loss cell. This is a
**runner-robustness** fix only — it touches no predicate, prompt, loss definition, or
threshold, so it is outside the addendum-D science freeze.

## Required before re-running (human)
1. Raise / reset the Anthropic API spend cap (console.anthropic.com) so a full stage can
   complete — h4 needs ~$105, and stages 1–2 already show the workspace budget is the
   binding constraint.
2. Apply the runner-robustness fix (count transport errors) so a future cap **aborts
   visibly and resumes**, and never commits a masquerading-complete summary.
3. Re-fire `exp-h4-recovery`; this branch's summary is **INVALID** and retained for audit.

## Ledger note
This $23.07 is real spend on an INVALID run (2/8 classes). It is retained on the branch
for audit like the first-wave INVALIDs (FINDINGS §6). The campaign envelope must be
re-assessed after the cap is raised.
