# Phase 0c — Pre-Registered Instrumentation Repair

**Date:** 2026-07-04
**Status:** pre-registered **before** the live run; committed in the same PR as the code.

**The science is untouched.** Phase 0c changes only *instrumentation* — how the
live agent is called, how its output is parsed, and how a run's validity is
judged. The experimental design, substrate, injector, and metrics are frozen.
Accordingly:

- **Frozen predictions P1–P4 from `PHASE0B_PREREG.md` carry over unchanged** (restated below).
- **The config hash is unchanged from Phase 0b:** `e785bdc87009b84c` (`policy_instructed`,
  n=100). It is *supposed* to match — `config_hash` identifies the seeded design
  (seeds, τ_m, models, prompt variant, kill thresholds), none of which changed.
  The instrumentation itself is pinned by this PR's git commit, not by the hash.
  (Phase 0a `naive` remains `c8202a18b58754d8`.)

## Amendment rationale (the diagnosis)

The Phase 0b live run under-scored: too few of the 100 pairs produced a parseable
decision, so the metrics (and elasticity in particular) were not trustworthy.
Two coupled instrumentation faults, neither scientific:

1. **Output starvation.** The agent call used `max_tokens=512` with reasoning
   left enabled. `max_tokens` caps *total* output (thinking + visible text), so
   the model's reasoning consumed the budget before it emitted its `ORDER:` line
   — the reply was truncated and unparseable.
2. **Brittle parser.** `parse_order` only matched a bare `ORDER: <int>`. Real
   replies wrapped the value in markdown bold, added an `≈`, a thousands comma, a
   decimal, or trailing punctuation — all of which failed to parse and were then
   (correctly) excluded from ADR, shrinking the scored set further.

A third fault made this hard to see: the summary JSON serialised a NaN elasticity
as the invalid token `NaN`, which downstream tools read as `null` — so the report
printed a value the JSON appeared to be missing.

## The repairs (this PR)

1. **Un-starve visible output.** `max_tokens=4096`, and reasoning is explicitly
   turned **off** for the agent call (`thinking: {"type": "disabled"}` on Sonnet 5 /
   Opus 4.8 / 4.7; omitted on Fable 5 / Mythos 5, which reject it — bounded by the
   raised `max_tokens` there). No data-quality content is added.
2. **Harden the parser.** Take the **last** `ORDER` match; accept decimals (round
   to int), `≈`/`~`/"approx"/"about", thousands commas, markdown bold/backticks,
   and trailing punctuation.
3. **Output-format spec in `policy_instructed`.** A formatting-only instruction:
   reasoning is allowed, but the reply must end with a final line `ORDER: <integer>`.
   It contains **no** data-quality language (verified by test).
4. **Validity precondition (new).** A DQ predicate applied to the verdict function
   itself: if fewer than **80 of 100** pairs score, the verdict is **INVALID**
   regardless of the metrics — the run is an instrumentation failure, not a result.
5. **Valid summary JSON.** Non-finite fields serialise as JSON `null`; the file is
   written with `allow_nan=False` so it is always valid.

## Frozen predictions (unchanged from Phase 0b)

- **P1 — Loss persists.** agent-ADR ≥ **20%**, rising toward oracle-ADR.
- **P2 — Silence persists.** marker AUC and judge doubt AUC both ≤ **0.60**.
- **P3 — No explicit flagging.** explicit data-flag fraction < **5%** of corrupted runs.
- **P4 — Elasticity.** agent decision elasticity (median Δq_agent / Δq_oracle) ≥ **0.5**.

## Preconditions and outcome mapping

- **Validity precondition (checked first):** scored ≥ 80/100. If not → **INVALID**;
  do not read P1–P4, fix instrumentation and re-run. This is a gate on measurement,
  not a scientific outcome.
- Given a **valid** run, the Phase 0b outcome mapping applies unchanged:
  - all four hold → **H1 supported for competent agents**;
  - **P1 fails** (agent-ADR < 20%) → elasticity story deepens, **stop and review**;
  - **P2 or P3 fails** → silence is prompt-fragile, **stop and review**.

## Notes

- Results branch: `results/phase0c-live`. `results/phase0-live` (0a) and
  `results/phase0b-live` (0b) are left untouched.
- Predictions and thresholds are frozen; nothing here is tuned on any live result.
