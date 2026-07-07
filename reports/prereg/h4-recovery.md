# PREREG — H4 (Downstream sufficiency) (`h4-recovery`)

**Date:** 2026-07-07  ·  **Status:** pre-registered before any run; frozen.
**Results branch:** `results/h4-recovery-live`.

## Registered predictions
- P1 recovery ratio = (loss_A - loss_{D+substitute}) / (loss_A - loss_E) >= 0.80.
- P2 zero source writes (verified from traces).
- P3 100% lineage completeness (every admitted action attributable to a versioned evidence set).

## Pass / kill thresholds
H4 supported if recovery >= 0.80 AND zero source writes AND lineage 100%.

## Validity precondition (all experiments)
A condition is **INVALID** (no verdict read) if fewer than **80%** of its paired
episodes score — the Phase 0c gate, generalized. Refusals and parse failures are
their own outcome classes, excluded from ADR, and reported.

## Budget
pause + report if projected spend > $150. Global cap: pause + report if projected total spend exceeds **$1000**.

## Notes
- The workflow runs `python -m benchmarks.experiments --exp h4-recovery`; the deterministic
  mock is the CI/$0 stand-in and the live arm answers the prediction.
- `<<HUMAN>>` marks a threshold that genuinely needs the human's judgment before running.
