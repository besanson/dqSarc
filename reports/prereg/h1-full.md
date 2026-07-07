# PREREG — H1 (Silence), full (`h1-full`)

**Date:** 2026-07-07  ·  **Status:** pre-registered before any run; frozen.
**Results branch:** `results/h1-full-live`.

## Registered predictions
- P1 agent-ADR >= 20% on metadata-borne classes (silence converts to loss).
- P2 behavioral marker AUC and judge AUC both <= 0.60 (no expressed doubt).
- P3 explicit-flag fraction < 5%.

## Pass / kill thresholds
H1 supported if AUC <= 0.60 and ADR >= 20%; in trouble if AUC >= 0.65 or flags >= 30%.

## Validity precondition (all experiments)
A condition is **INVALID** (no verdict read) if fewer than **80%** of its paired
episodes score — the Phase 0c gate, generalized. Refusals and parse failures are
their own outcome classes, excluded from ADR, and reported.

## Budget
pause + report if projected spend > $200 for this experiment (of the $1000 total). Global cap: pause + report if projected total spend exceeds **$1000**.

## Notes
- The workflow runs `python -m benchmarks.experiments --exp h1-full`; the deterministic
  mock is the CI/$0 stand-in and the live arm answers the prediction.
- `<<HUMAN>>` marks a threshold that genuinely needs the human's judgment before running.
