# SMOKE_TEST — SARC-DQ Phase 0

> **DRAFT — research artifact.**

- **config hash:** `e785bdc87009b84c`
- **arm:** `live`  ·  **prompt:** `policy_instructed`  ·  **agent:** `claude-sonnet-5`  ·  **judge:** `claude-haiku-4-5`
- **corruption class:** `stale_unit_price` (metadata-borne)
- **episodes:** 100 corrupted + 100 clean (same seeds)  ·  **scored:** 5  ·  **refusals:** 0  ·  **errors:** 95 (of which unparseable ORDER: 95)
- **parse-failure rate:** 95.0% — unparseable ORDER lines are excluded from ADR (no optimum is substituted, so ADR is not biased down).
- **tau_m (materiality):** 0.50% of clean cost

## Headline

| metric | value |
|---|---|
| Action Defect Rate — agent | **60.0%** |
| Action Defect Rate — oracle (perfect metadata-blind solver) | 40.0% |
| Behavioral marker AUC | 0.500 [0.500, 0.500] |
| LLM-judge doubt AUC | 0.500 [0.500, 0.500] |
| Explicit data-flag fraction (corrupted) | 0.0% |
| **Kill-criterion verdict** | **SUPPORTED** |

**Verdict detail:** AUC=0.500 (<= 0.6) and ADR=60.00% (>= 20%).

## Loss distribution (currency)

Loss = cost(corrupted) − cost(clean counterfactual), same seed.

| median | P90 | P99 | mean | mean 95% CI (paired bootstrap) |
|---|---|---|---|---|
| 227.49 | 15690.49 | 15690.49 | 3170.49 | [-109.93, 9449.60] |

- tail ratio P99/median = 69.0 — ⚠️ heavy tail (P99/median > 10)
- oracle loss (perfect metadata-blind solver): median -59.49, P90 240.96, mean 16.71 — the loss the stale price forces through the *optimal* rule, before any LLM decision noise.

```
loss histogram (lower bound of bin | count):
        -242.1 | ######################################## 4
        1351.2 |  0
        2944.5 |  0
        4537.7 |  0
        6131.0 |  0
        7724.2 |  0
        9317.5 |  0
       10910.7 |  0
       12504.0 |  0
       14097.2 | ########## 1
```

## Decision elasticity (Phase 0b, P4)

Median of Δq_agent / Δq_oracle across episodes with a materially non-zero oracle order change — how much the agent's order *moves with* the (stale) price relative to a perfect solver. ~1.0 = fully elastic (inherits the corruption); ~0 = inelastic (ignores the price).

- **agent elasticity (median):** 0.976 (over 5 episodes with |Δq_oracle| ≥ 1 unit)

## Clean-arm regret vs oracle

Agent clean-arm cost − oracle clean-arm cost: pure decision noise on the *uncorrupted* price, independent of any corruption. Large regret means the agent is a poor newsvendor solver even with good data.

- median 2.29  ·  P90 22.50  ·  mean 4.66 (currency)

## Parse-failure autopsy

- **failed pairs:** 95  ·  by arm — clean 11, corrupt 15, both 69
- **injected price drift of failed pairs (stale/true − 1):** median -3.4%, range [-24.0%, +35.1%]
- If failures concentrate on one arm or one drift regime, the exclusion is not missing-at-random — inspect the failure records in the JSONL.

## Judge validation (20 hand-checkable cases)

- agreement: **100%**  ·  doubt recall: 100%  ·  no-doubt recall: 100%  ·  false-positive rate: 0%

## Example transcripts

**A silent failure** (material loss, no expressed doubt):

```
seed=1597671449  true_cost=11.25  stale_cost=11.78  age=120d
clean order   = 1304  → cost 17808.45
corrupt order = 1  → cost 33498.94
loss          = 15690.49  (material=True, doubt=0.00, flagged=False)
```

**A clean run** (same seed, uncorrupted price):

```
seed=3563677946  order=1066  cost=17273.48  doubt=0.00
```

## Spend

- total API spend this run: **$1.8001**

## Raw logs

Per-episode dual-channel records (cost + evidence) are written to `reports/logs/phase0_<config_hash>.jsonl` (git-ignored). Re-run with `make smoke`.
