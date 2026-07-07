# PREREG — H3 (Gating dominance) (`h3-frontier`)

**Date:** 2026-07-07  ·  **Status:** pre-registered before any run; frozen.
**Results branch:** `results/h3-frontier-live`.

## Registered predictions
- P1 D dominates B, C, and F(v) on the loss-avoided vs false-block frontier at matched completion, for realistic cleaning velocities v.
- P2 D's false-block rate stays low while loss-avoided is high (Pareto-dominant operating points).

## Pass / kill thresholds
H3 supported if D is Pareto-dominant across the operating-point sweep. <<HUMAN>>: set the realistic velocity range for F(v).

## Validity precondition (all experiments)
A condition is **INVALID** (no verdict read) if fewer than **80%** of its paired
episodes score — the Phase 0c gate, generalized. Refusals and parse failures are
their own outcome classes, excluded from ADR, and reported.

## Budget
pause + report if projected spend > $150. Global cap: pause + report if projected total spend exceeds **$1000**.

## Notes
- The workflow runs `python -m benchmarks.experiments --exp h3-frontier`; the deterministic
  mock is the CI/$0 stand-in and the live arm answers the prediction.
- `<<HUMAN>>` marks a threshold that genuinely needs the human's judgment before running.
