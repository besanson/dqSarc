# PREREG — H1 capability ladder (headline figure) (`h1-ladder`)

**Date:** 2026-07-07  ·  **Status:** pre-registered before any run; frozen.
**Results branch:** `results/h1-ladder-live`.

## Registered predictions
- P1 ADR and behavioral AUC are approximately FLAT across claude-haiku-4-5 -> claude-sonnet-5 -> claude-opus-4-8 -> claude-fable-5 (silence is capability-invariant; the signal is not in the context at any tier).
- P2 if silence instead falls with capability, report as a bounding result (still publishable).

## Pass / kill thresholds
<<HUMAN>>: set the flatness tolerance (e.g. |Delta ADR| across rungs <= 10pp) before running. fable-5 needs 30-day retention (not ZDR); refusals are their own outcome class.

## Validity precondition (all experiments)
A condition is **INVALID** (no verdict read) if fewer than **80%** of its paired
episodes score — the Phase 0c gate, generalized. Refusals and parse failures are
their own outcome classes, excluded from ADR, and reported.

## Budget
pause + report if projected spend > $250 (ladder is the most expensive). Global cap: pause + report if projected total spend exceeds **$1000**.

## Notes
- The workflow runs `python -m benchmarks.experiments --exp h1-ladder`; the deterministic
  mock is the CI/$0 stand-in and the live arm answers the prediction.
- `<<HUMAN>>` marks a threshold that genuinely needs the human's judgment before running.
