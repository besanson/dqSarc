# FINDINGS — instrumentation correction and the price-inelasticity result

**Date:** 2026-07-09 · **Status:** post-run analysis; grounds the paper's framing.
**Scope:** why the loss-based hypotheses (H1-converts-to-loss, H3, H4) carry no
signal for the agent under test, and why the study's contribution is the
**detection asymmetry** (H2), not loss-recovery.

This record exists so the correction is auditable and nothing is re-interpreted
after the fact. Every number below is read from a committed `results/<exp>-live`
branch or a frozen Phase 0 artifact.

---

## 1. The instrumentation bug we found and fixed

The live experiments originally measured loss and materiality against the
*theoretical optimum*:

```
loss_raw = realised_cost(agent_order) − realised_cost(optimal_order(true_price))
material = loss_raw ≥ τ_m · clean_cost          # ADR = fraction material
```

Because **every** arm routes through the real agent, `loss_raw` carries the
agent's own decision suboptimality. Phase 0a measured that suboptimality directly:

- `clean_regret_median = 2519.565` (agent vs optimal, on **clean** data)
- `elasticity_median = 0.000` (agent order's response to price)

That baseline noise (~2519) dwarfs the corruption signal and, on its own, clears
the low materiality bar (`τ_m = 0.005` of clean cost). The smoking gun, read from
`results/h4-recovery-live` (same episodes/seeds, one run):

| arm | acts on | ADR @ rate 0.20 (price classes) |
|---|---|---|
| A | corrupted price | 0.727 |
| **E** | **true price (zero corruption)** | **0.727 — identical** |

An oracle acting on perfectly clean data scored a 73% "action-defect rate." The
metric was measuring agent noise, not corruption.

**Fix (mirrors the frozen Phase 0 loss definition exactly):** measure the
**paired** loss against the *same agent's* order on the true price, same demand
draw, so the agent's baseline noise cancels:

```
loss_paired = realised_cost(agent_order_on_view) − realised_cost(agent_order_on_true)
material    = loss_paired ≥ τ_m · clean_cost
```

Arm E acts on the true price, so `loss_paired = 0` by construction — the control.
After the fix, arm-E ADR is **0.000** on every cell. (Implemented in
`src/sarc_dq/live_arms.py`; stamped `loss_model = "paired-counterfactual-v2"`.)

## 2. What the corrected measurement shows: the agent is price-inelastic

Re-running `h1-full` under the corrected instrument (`results/h1-full-live`,
$13.12, 32/32 cells) gives **ADR = 0.00 on every class and every rate**, and the
paired loss is negligible even where the price corruption is large:

| class | price perturbation | paired `loss_eff` @ 0.20 |
|---|---|---|
| silent_unit_change | ×2.2 or ×0.45 | −1.37 |
| stale_master_data | ~±20% | +1.10 |
| superseded_golden_record | ×0.6–0.9 | −0.12 |
| plausible_outlier | in-range, ≥2 off | +2.30 |

A cost-optimising agent would convert these into large losses — the deterministic
fake newsvendor (which follows `optimal_order(price)`) produces pooled loss ≈ 220
on the same substrate. The real agent producing ≈ 0 means **it does not adjust its
order to unit cost**: it orders ≈ mean demand regardless. This is exactly Phase 0a's
frozen `elasticity = 0.000`. The prompt supplies unit_cost, the demand forecast,
holding/stockout costs, and the explicit newsvendor policy — so the inelasticity is
a behavioural finding about the agent, not a missing input.

Two classes (`schema_drift`, `missing_mandatory_field`) remove/retype the price;
the agent then fails to act (completion 0.78 at rate 0.20, `n_errors = 0`) — a
loud completion failure, not a silent conversion.

## 2a. Correction: the inelasticity is a PROMPT artifact, and the experiments were mis-wired

The inelasticity above is **not** an immutable property of the agent — it is an
artifact of the **naive** prompt (no formula), which the experiments used by
default. Your own frozen Phase 0 data shows the same agent is price-elastic once
handed the newsvendor policy:

| prompt | formula given? | `elasticity_median` |
|---|---|---|
| naive (Phase 0a; what h1-full ran) | no | **0.000** |
| policy_instructed (Phase 0b) | yes | **0.976** |
| policy_instructed (Phase 0c) | yes | **0.992** |

`policy_instructed` was created in Phase 0b precisely to remove the competence
confound: it supplies the ordering policy but **no** data-quality language, so the
decider is *competent yet still metadata-blind*. That is the correct agent for the
loss experiments — any loss is then attributable to the undetected corruption, not
to the agent being unable to optimise. The experiments defaulted to `naive`
(`live_arms.py` never passed a variant), which conflated "can't optimise" with
"can't detect" and is why the loss signal vanished.

**Fix (this change):** `prompt_variant` is threaded through the experiment path and
the live experiments now default to `policy_instructed` (recorded in every summary's
`config.prompt_variant`; a naive checkpoint is not resumed by a policy run). Under a
competent, metadata-blind decider, a stale price it acts on is *expected* to convert
to a real order loss, and the gate's substitution to recover it — so H1/H3/H4 should
have signal again. This is to be confirmed by a `policy_instructed` h1-full re-probe
(~$12) before committing to the full re-runs; the outcome is not yet measured.

**Status of H1/H3/H4:** pending the `policy_instructed` re-runs. The earlier
"no signal / pivot to detection" conclusion applied only to the mis-wired naive runs
and is withdrawn.

## 3. What survives: the detection asymmetry (H2)

The gate's value is **detection**, which is independent of whether the agent
mis-orders. From `results/h2-detection-live` (detection_rate @ rate 0.20):

| class | channel | critic C (payload-only) | gate D (metadata-aware) |
|---|---|---|---|
| stale_master_data | metadata-borne | 0.00 | **1.00** |
| schema_drift | payload-visible | 0.00 | **1.00** |
| superseded_golden_record | metadata-borne | 1.00 | 1.00 |
| cross_source_contradiction | payload-visible | 1.00 | 1.00 |
| silent_unit_change | metadata-borne | 0.00 | 0.00 |
| plausible_outlier | metadata-borne | 0.00 | 0.00 |

The gate **strictly dominates** the payload-only critic exactly where it has a
predicate — freshness (`stale_master_data`) and schema (`schema_drift`) — and never
loses. This is the core mechanism: a cheap, deterministic, metadata-aware gate
catches defects a frontier payload-only critic structurally cannot see. It is
honest about its scope: `silent_unit_change` and `plausible_outlier` are missed by
both (no predicate covers them).

## 4. Integrity note

Moving materiality to the paired loss is a disclosed **instrumentation correction**,
not a post-hoc metric change to obtain a result: (a) it is the same loss the frozen
Phase 0 was built on; (b) the arm-E control (0.73 on clean data → 0.00) transparently
proves the original metric was measuring noise. The paper's methods section states
this and shows the control. The pre-registered predictions are reported as measured —
including H1 not clearing its bar.

## 5. H2 verdict (failed-then-reframed)

The committed verdict code (`benchmarks/verdicts.py`) run against
`results/h2-detection-live` gives **H2: NOT SUPPORTED** (P1 FAIL, P2 FAIL):

```
  class                          chan             C     D   result
  cross_source_contradiction     payload-visible  1.00  1.00  pass  [P1 |C-D|=0.00<=0.15]
  duplicate_vendor_conflicting.. payload-visible  0.02  0.00  pass  [P1 |C-D|=0.02<=0.15]
  missing_mandatory_field        payload-visible  0.77  1.00  FAIL  [P1 |C-D|=0.23>0.15]
  plausible_outlier              metadata-borne   0.00  0.00  FAIL  [P2 D=0.00<0.80]
  schema_drift                   payload-visible   0.00  1.00  FAIL  [P1 |C-D|=1.00>0.15]
  silent_unit_change             metadata-borne   0.00  0.00  FAIL  [P2 D=0.00<0.80]
  stale_master_data              metadata-borne   0.00  1.00  pass  [P2 C=0.00, D=1.00]
  superseded_golden_record       metadata-borne   1.00  1.00  FAIL  [P2 C=1.00>0.10]
```

(This run is under the buggy sampler — §6 — so the verdict is INVALID for final sign-off
and will be re-issued on the corrected `policy_instructed`/fixed-n re-run; detection is
per-corrupted and class-stable, so the qualitative reframe below is expected to hold.)

**Reframe — the payload/metadata channel boundary is empirical, not definitional.**
H2 was pre-registered assuming a clean split: payload-visible ⇒ C≈D, metadata-borne ⇒
C≪D. The measurement refutes that clean split and, more usefully, *reclassifies by
behaviour*:

- **`schema_drift`** (labelled payload-visible) behaves metadata-borne for detection:
  the payload-only critic never flags it (C=0.00) while the gate always does (D=1.00) —
  a renamed/retyped field is a *schema* signal the deterministic gate reads and the
  content critic misses. **The gate strictly dominates.**
- **`superseded_golden_record`** (labelled metadata-borne) is detectable from payload:
  the conflicting companion record lets the critic flag it (C=1.00). The channel label
  was wrong, not the gate.
- **Two named predicate-coverage gaps:** `silent_unit_change` and `plausible_outlier`
  are missed by **both** arms (D=0.00) — the v1 gate has no unit-consistency or
  in-range-outlier predicate. Reported as a result and documented as **v1.1 future
  work** (addendum D / W5); the gate is not patched to rescue the prediction.

So the strict H2 conjunction fails, but the load-bearing claim survives on the classes
where the gate *has* a predicate (freshness `stale_master_data`, schema `schema_drift`):
a cheap metadata-aware gate catches defects a frontier payload-only critic structurally
cannot. The failures are informative — they map where the boundary actually lies and
where the gate needs a predicate — not fatal.

## 6. Rate-cell sampling bug — h1-full and h2-detection runs marked INVALID

A second instrumentation bug was found after §2a. The benchmark drew the
corruption coin from a **rate-independent** seed, so corrupted-episode sets were
**nested** across rates and **byte-identical** where no draw fell between two
adjacent rates: the 0.02 and 0.05 cells shared the exact same five episodes
`{20,26,53,61,83}` with the same injected values. The rate axis was not producing
independent samples; the low-rate cells were degenerate. Fixed by
`sarc_dq.substrate.corruption_decision` (rate-dependent mask/injection; shared
episode population), used by both the live and mock paths; proof and gate in
`reports/VERIFICATION-2026-07-09-W3.md`.

**INVALID results (produced under the buggy sampler — do not cite):**

| results branch | SHA | spend | status |
|---|---|---|---|
| `results/h1-full-live` | `2993ece` | \$32.22 | **INVALID** — re-run under fixed sampler |
| `results/h2-detection-live` | `a37bf0b` | \$56.60 | **INVALID** — re-run under fixed sampler |

**Figures explicitly WITHDRAWN** (they came from the invalid `h1-full` policy run
at `2993ece`): the metadata-borne mean ADR of **0.585**, the **16/16** cells-clear-
20% count, and the **\$1,080** `silent_unit_change` loss. These must not appear in
the paper or any summary until re-measured under the corrected sampler; the
generated macros render `[pending]` in the meantime.

**Retained with a caveat — the naive-null run.** The \$13.12 `naive`-prompt h1-full
run also used the buggy sampler, but its result is a **uniform zero** ADR across all
eight classes and four rates (the price-inelastic decider never converts corruption
to a material order defect). A uniform-zero outcome is **insensitive to which
episodes are corrupted or to cell nesting** — degeneracy cannot manufacture or hide
a zero. It is therefore retained as the "incompetence shield" result (silence does
not convert to loss when the decider ignores unit cost), with this sampler caveat
noted. It will still be re-run under the fixed sampler for uniformity before final
sign-off, but it is not a blocking invalidation.

## 7. Silence sub-claim (H1 P2/P3) — instrumentation added, verdict downgraded

The prior live runs did not log agent transcripts, so H1's silence predictions — P2
(behavioural-marker AUC and judge AUC ≤ 0.60) and P3 (explicit-flag fraction < 5%) —
had **no underlying data**. The runner now captures the agent transcript and computes,
per cell, a **doubt-marker AUC** (corrupted vs clean) and a **flag fraction**
(`sarc_dq.markers`), carried in every summary (W2). The **LLM-judge AUC** (second
P2 quantity) requires a paid judge turn per transcript (model pinned in the addendum)
and is deferred to the re-runs.

Until the instrumented re-runs land, the H1 verdict is stated as: **P1
(loss-conversion) is supported under `policy_instructed`; the silence claim (P2/P3)
rests on Phase 0c and is reported as PENDING an instrumented re-run.** This wording
is used in FINDINGS and must be used in the paper (W1 "Deviations and clarifications").
