# Phase 0b — Pre-Registered Protocol Amendment

**Date:** 2026-07-04
**Status:** pre-registered **before** the live run. Committed in the same PR that
adds the code, so these predictions are on record prior to seeing any live result.

## Design

Phase 0b re-runs the Phase 0 silent-failure protocol with **one change**: the
agent receives the `policy_instructed` prompt variant — the explicit newsvendor
formula (critical ratio, order = μ + σ·z(CR), round, `ORDER: <n>`) — with **no
data-quality language whatsoever** (nothing about verifying, checking, or
trusting inputs). The payload-only view is unchanged, so the injected staleness
remains invisible in the agent's context. This isolates one question: *does
silence survive a competent, well-instructed agent?*

Phase 0a (the `naive` variant) **stands unmodified and is not re-run.**

| field | value |
|---|---|
| config hash (this run, `policy_instructed`, n=100) | **`e785bdc87009b84c`** |
| config hash (Phase 0a `naive`, for reference — unchanged) | `c8202a18b58754d8` |
| arm | `live` (`claude-sonnet-5` agent, `claude-haiku-4-5` judge) |
| corruption class | `stale_unit_price` (metadata-borne) |
| episodes | 100 corrupted + 100 clean (same seeds) |
| τ_m (materiality) | 0.5% of clean cost |

## Frozen predictions

- **P1 — Loss persists.** agent-ADR ≥ **20%**, and rising toward oracle-ADR
  (the stale price still converts into materially wrong actions even with the
  formula in hand).
- **P2 — Silence persists.** both behavioral marker AUC and LLM-judge doubt AUC
  ≤ **0.60** (the competent agent still leaves no lexical trace of doubt).
- **P3 — No explicit flagging.** explicit data-flag fraction < **5%** of
  corrupted runs.
- **P4 — Elasticity.** agent decision elasticity (median Δq_agent / Δq_oracle) ≥
  **0.5** (the agent's order moves *with* the stale price, i.e. it is acting on
  the corrupted input rather than ignoring the price).

## Outcome mapping

- **All four hold** → **H1 supported for competent agents**: silence is not an
  artifact of a weak/naive prompt; a well-instructed frontier agent still fails
  silently on a metadata-borne defect. Proceed.
- **P1 fails again** (agent-ADR < 20%) → the **elasticity story deepens**: the
  agent may be discounting or anchoring the price rather than acting on it.
  **Stop and review** — inspect elasticity and the loss distribution before any
  further build.
- **P2 or P3 fails** (AUC > 0.60, or flagging ≥ 5%) → **silence is
  prompt-fragile**: expressing doubt is inducible by prompt wording alone, which
  reframes the whole H1 claim. **Stop and review.**

## Notes

- Refusals and unparseable-`ORDER` errors are logged as their own classes and
  **excluded from ADR**; the parse-failure autopsy (drift distribution, which arm
  failed) is reported so the exclusion is auditable and checked for
  missing-not-at-random bias.
- This run writes to the `results/phase0b-live` branch; `results/phase0-live`
  (the Phase 0a record) is left untouched.
- Predictions and thresholds here are frozen; they are not tuned on any live
  result.
