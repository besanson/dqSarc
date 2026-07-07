# PREREG — H2 (Detection asymmetry) (`h2-detection`)

**Date:** 2026-07-07  ·  **Status:** pre-registered before any run; frozen.
**Results branch:** `results/h2-detection-live`.

## Registered predictions
- P1 C ~= D on payload-visible classes (|detection_C - detection_D| <= 0.15).
- P2 C << D on metadata-borne classes (detection_C <= 0.10, detection_D >= 0.80).
- P3 cost-per-detection for C (opus-4-8 critic) exceeds D (cheap metadata gate).

## Pass / kill thresholds
H2 supported if P1 and P2 hold. The payload-only critic view is the design; do not 'fix' it.

## Validity precondition (all experiments)
A condition is **INVALID** (no verdict read) if fewer than **80%** of its paired
episodes score — the Phase 0c gate, generalized. Refusals and parse failures are
their own outcome classes, excluded from ADR, and reported.

## Budget
pause + report if projected spend > $150. Global cap: pause + report if projected total spend exceeds **$1000**.

## Notes
- The workflow runs `python -m benchmarks.experiments --exp h2-detection`; the deterministic
  mock is the CI/$0 stand-in and the live arm answers the prediction.
- `<<HUMAN>>` marks a threshold that genuinely needs the human's judgment before running.
