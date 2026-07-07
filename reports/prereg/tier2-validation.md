# PREREG — Tier-2 predicate validation on real errors (`tier2-validation`)

**Date:** 2026-07-07  ·  **Status:** pre-registered before any run; frozen.
**Results branch:** `results/tier2-validation-live`.

## Registered predictions
- P1 the six predicates achieve precision/recall on the labeled real-error datasets (Raha suite; Flights/Stock conflicts; Magellan duplicates; ALFRED vintages) at or above <<HUMAN>> thresholds (set per dataset before running).

## Pass / kill thresholds
<<HUMAN>>: set per-dataset precision/recall pass thresholds. Requires the Tier-2 datasets to be provisioned (not shipped in this repo).

## Validity precondition (all experiments)
A condition is **INVALID** (no verdict read) if fewer than **80%** of its paired
episodes score — the Phase 0c gate, generalized. Refusals and parse failures are
their own outcome classes, excluded from ADR, and reported.

## Budget
pause + report if projected spend > $50 (predicates are $0; cost is data provisioning). Global cap: pause + report if projected total spend exceeds **$1000**.

## Notes
- The workflow runs `python -m benchmarks.experiments --exp tier2-validation`; the deterministic
  mock is the CI/$0 stand-in and the live arm answers the prediction.
- `<<HUMAN>>` marks a threshold that genuinely needs the human's judgment before running.
