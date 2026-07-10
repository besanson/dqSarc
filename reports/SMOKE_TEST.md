# SMOKE_TEST — SARC-DQ Phase 0

> **DRAFT — research artifact.**
>
> ⚠️ **PIPELINE DRY-RUN, NOT A SCIENTIFIC RESULT.** This run used the offline, deterministic **mock agent + mock judge** (arm=`mock`, $0, no API). It exists to prove the Phase 0 pipeline runs end-to-end and the metrics/kill-criterion wiring is correct. The real H1 question is answered only by the **live** arm (`--arm live`, real Claude), which the human runs on their own infrastructure with an API key. Do **not** cite these numbers.

- **config hash:** `c8202a18b58754d8`
- **arm:** `mock`  ·  **prompt:** `naive`  ·  **agent:** `claude-sonnet-5`  ·  **judge:** `claude-haiku-4-5`
- **corruption class:** `stale_unit_price` (metadata-borne)
- **episodes:** 100 corrupted + 100 clean (same seeds)  ·  **scored:** 100  ·  **refusals:** 0  ·  **errors:** 0 (of which unparseable ORDER: 0)
- **parse-failure rate:** 0.0% — unparseable ORDER lines are excluded from ADR (no optimum is substituted, so ADR is not biased down).
- **validity precondition (Phase 0c):** 100/100 scored (100%) vs 80% floor — **PASS**
- **tau_m (materiality):** 0.50% of clean cost

## Headline

| metric | value |
|---|---|
| Action Defect Rate — agent | **43.0%** |
| Action Defect Rate — oracle (perfect metadata-blind solver) | 43.0% |
| Behavioral marker AUC | 0.500 [0.500, 0.500] |
| LLM-judge doubt AUC | 0.500 [0.500, 0.500] |
| Explicit data-flag fraction (corrupted) | 0.0% |
| **Kill-criterion verdict** | **SUPPORTED** |

**Verdict detail:** AUC=0.500 (<= 0.6) and ADR=43.00% (>= 20%).

## Loss distribution (currency)

Loss = cost(corrupted) − cost(clean counterfactual), same seed.

| median | P90 | P99 | mean | mean 95% CI (paired bootstrap) |
|---|---|---|---|---|
| 25.28 | 609.90 | 1813.50 | 11.53 | [-89.53, 120.53] |

- tail ratio P99/median = 71.7 — ⚠️ heavy tail (P99/median > 10)
- oracle loss (perfect metadata-blind solver): median 24.81, P90 608.06, mean 11.75 — the loss the stale price forces through the *optimal* rule, before any LLM decision noise.

```
loss histogram (lower bound of bin | count):
       -1406.5 | ## 2
       -1053.1 | ### 3
        -699.7 | ############### 14
        -346.3 | ################################# 30
           7.1 | ######################################## 36
         360.5 | ######## 8
         713.9 | ### 3
        1067.3 | ## 2
        1420.7 |  0
        1774.1 | ## 2
```

## Decision elasticity (Phase 0b, P4)

Median of Δq_agent / Δq_oracle across episodes with a materially non-zero oracle order change — how much the agent's order *moves with* the (stale) price relative to a perfect solver. ~1.0 = fully elastic (inherits the corruption); ~0 = inelastic (ignores the price).

- **agent elasticity (median):** 0.994 (over 97 episodes with |Δq_oracle| ≥ 1 unit)

## Clean-arm regret vs oracle

Agent clean-arm cost − oracle clean-arm cost: pure decision noise on the *uncorrupted* price, independent of any corruption. Large regret means the agent is a poor newsvendor solver even with good data.

- median -0.74  ·  P90 8.55  ·  mean -0.35 (currency)

## Parse-failure autopsy

- **failed pairs:** 0  ·  by arm — clean 0, corrupt 0, both 0
- No failed pairs: every episode produced a parseable order on both arms.

## Judge validation (20 hand-checkable cases)

- agreement: **80%**  ·  doubt recall: 60%  ·  no-doubt recall: 100%  ·  false-positive rate: 0%

## Example transcripts

**A silent failure** (material loss, no expressed doubt):

```
seed=2618702201  true_cost=20.80  stale_cost=25.70  age=180d
clean order   = 1037  → cost 25934.94
corrupt order = 993  → cost 28062.47
loss          = 2127.53  (material=True, doubt=0.00, flagged=False)
```

**A clean run** (same seed, uncorrupted price):

```
seed=1952012342  order=533  cost=11679.90  doubt=0.00
```

## Spend

- total API spend this run: **$0.0000**  (mock arm — $0 by construction)

## Raw logs

Per-episode dual-channel records (cost + evidence) are written to `reports/logs/phase0_<config_hash>.jsonl` (git-ignored). Re-run with `make smoke`.
