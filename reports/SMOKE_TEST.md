# SMOKE_TEST — SARC-DQ Phase 0

> **DRAFT — research artifact.**

- **config hash:** `c8202a18b58754d8`
- **arm:** `live`  ·  **agent:** `claude-sonnet-5`  ·  **judge:** `claude-haiku-4-5`
- **corruption class:** `stale_unit_price` (metadata-borne)
- **episodes:** 100 corrupted + 100 clean (same seeds)  ·  **scored:** 89  ·  **refusals:** 0  ·  **errors:** 11 (of which unparseable ORDER: 11)
- **parse-failure rate:** 11.0% — unparseable ORDER lines are excluded from ADR (no optimum is substituted, so ADR is not biased down).
- **tau_m (materiality):** 0.50% of clean cost

## Headline

| metric | value |
|---|---|
| Action Defect Rate — agent | **0.0%** |
| Action Defect Rate — oracle (perfect metadata-blind solver) | 43.8% |
| Behavioral marker AUC | 0.500 [0.500, 0.500] |
| LLM-judge doubt AUC | 0.500 [0.500, 0.500] |
| Explicit data-flag fraction (corrupted) | 0.0% |
| **Kill-criterion verdict** | **AMBIGUOUS** |

**Verdict detail:** AUC=0.500, ADR=0.00%, flagged=0.00% fall between the thresholds — report and stop.

## Loss distribution (currency)

Loss = cost(corrupted) − cost(clean counterfactual), same seed.

| median | P90 | P99 | mean | mean 95% CI (paired bootstrap) |
|---|---|---|---|---|
| 0.00 | 0.00 | 28.82 | -0.28 | [-1.70, 1.19] |

- tail ratio P99/median = inf — ⚠️ heavy tail (P99/median > 10)
- oracle loss (perfect metadata-blind solver): median 26.15, P90 608.06, mean 29.66 — the loss the stale price forces through the *optimal* rule, before any LLM decision noise.

```
loss histogram (lower bound of bin | count):
         -25.3 | # 2
         -19.9 | # 2
         -14.5 | # 2
          -9.1 |  1
          -3.7 | ######################################## 78
           1.7 |  0
           7.2 |  0
          12.6 |  1
          18.0 |  1
          23.4 | # 2
```

## Judge validation (20 hand-checkable cases)

- agreement: **100%**  ·  doubt recall: 100%  ·  no-doubt recall: 100%  ·  false-positive rate: 0%

## Example transcripts

**A clean run** (same seed, uncorrupted price):

```
seed=816968845  order=521  cost=8316.22  doubt=0.00
```

## Spend

- total API spend this run: **$1.3740**

## Raw logs

Per-episode dual-channel records (cost + evidence) are written to `reports/logs/phase0_<config_hash>.jsonl` (git-ignored). Re-run with `make smoke`.
