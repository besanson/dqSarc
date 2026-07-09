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

**Consequence.** If price corruption does not change the agent's action, it cannot
convert to an order loss. So:

- **H1 "silence converts to loss" (ADR ≥ 20%)** — not supported. The agent is
  silent *and* inelastic; the danger is silent propagation of bad data, not a
  mis-costed order.
- **H3 (loss-avoided frontier), H4 (recovery ratio)** — no loss signal to avoid or
  recover. Re-running would confirm ≈ 0, not rescue the claim; they are not fired.

Two classes (`schema_drift`, `missing_mandatory_field`) remove/retype the price;
the agent then fails to act (completion 0.78 at rate 0.20, `n_errors = 0`) — a
loud completion failure, not a silent conversion.

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
