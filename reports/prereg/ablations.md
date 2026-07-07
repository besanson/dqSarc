# PREREG — Ablation (each predicate off) (`ablations`)

**Date:** 2026-07-07  ·  **Status:** pre-registered before any run; frozen.
**Results branch:** `results/ablations-live`.

## Registered predictions
- P1 removing predicate X drops detection_rate on X's target class(es) toward ~0 while leaving other classes unaffected — each predicate is load-bearing for its class.

## Pass / kill thresholds
Ablation informative if each removal produces the predicted, localized detection drop.

## Validity precondition (all experiments)
A condition is **INVALID** (no verdict read) if fewer than **80%** of its paired
episodes score — the Phase 0c gate, generalized. Refusals and parse failures are
their own outcome classes, excluded from ADR, and reported.

## Budget
pause + report if projected spend > $100 (mostly gate-side, cheap). Global cap: pause + report if projected total spend exceeds **$1000**.

## Notes
- The workflow runs `python -m benchmarks.experiments --exp ablations`; the deterministic
  mock is the CI/$0 stand-in and the live arm answers the prediction.
- `<<HUMAN>>` marks a threshold that genuinely needs the human's judgment before running.
