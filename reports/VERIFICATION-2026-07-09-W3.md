# VERIFICATION — 2026-07-09 — W3 (rate-cell sampling independence)

Self-verification per the autonomous-mode brief. Literal command outputs, not
summaries. This report covers **W3 core only** (the sampling fix); it is one slice
of the corrections PR, which is not yet complete (see PROGRESS.md).

## The bug (reproduced)

`_episode_evidence` / `harness.run_condition` drew the corruption coin from a
RATE-INDEPENDENT seed, so corrupted-episode sets were nested across rates and
byte-identical where no draw fell between two adjacent rates:

```
rate 0.02: n_corrupted=5  episodes=[20, 26, 53, 61, 83]
rate 0.05: n_corrupted=5  episodes=[20, 26, 53, 61, 83]
0.02 set == 0.05 set ? True      (byte-identical cells)
0.02 subset of 0.05 ? True       (nested, not independent)
```

## The fix

New `sarc_dq.substrate.corruption_decision(base_seed, i, rate)` seeds the corruption
coin and injection RNG from the rate as well as the episode; the episode population
(`episode_seed`) stays rate-independent. Both the live path (`_episode_evidence`) and
the mock path (`harness.run_condition`) call it — one shared implementation, no drift.

```
rate 0.02: n=2 episodes=[9, 80]
rate 0.05: n=4 episodes=[6, 7, 85, 89]
rate 0.10: n=13 episodes=[7, 10, 16, 25, 36, 39, 45, 57]
rate 0.20: n=24 episodes=[1, 3, 5, 8, 13, 15, 23, 28]
0.02 == 0.05 ? False     0.02 subset of 0.05 ? False     0.05 subset of 0.10 ? False
```

## Mock proof (V0 requirement)

`test_mock_matrix_rate_cells_differ` asserts, for every class, that the regenerated
reference's `0.02` and `0.05` cells are not byte-identical. `test_rate_cells_are_
independent_not_nested` asserts non-nesting at the sampler level. Both pass.

## GIGO reference re-frozen (consequence of the fix)

The sampling fix changes the deterministic mock matrix, so the frozen
`benchmarks/gigo/reference_summary.json` was regenerated. It is a $0 deterministic
artifact (config only; no timestamp/date-bomb) and reproduces exactly:

```
python -m benchmarks.gigo.reproduce --verify benchmarks/gigo/reference_summary.json
gigo verify: OK (192 cells within tolerance)
```

## Gate

```
ruff check .                       -> All checks passed!
mypy src/sarc_dq benchmarks scripts -> Success: no issues found in 38 source files
pytest -q                          -> 91 passed
make gigo-verify                   -> gigo verify: OK (192 cells within tolerance)
tests/test_phase0b.py (frozen hash) -> 7 passed  (config_hash c8202a18b58754d8 preserved)
```

Phase 0 (`phase0.py`, `phase0*.yml`) is untouched — its frozen config hash still
verifies. `pytest` count went 91 -> 91 (3 W3 regression tests added; earlier scratch
of an obsolete assertion is not present — net non-decreasing).

## CONSEQUENCE — MUST be acted on before firing (flagged, not worked around)

The committed live results were produced under the **buggy** sampling:
- `results/h1-full-live` (policy_instructed, $32.22)
- `results/h2-detection-live` ($56.60)

Their low-rate cells (0.02, 0.05) are degenerate/duplicated. Under the corrected
sampler these experiments must be **re-run** to be valid. The remaining W3 sub-item
(pooled per-class ADR + paired-seed bootstrap CIs; per-cell n printed everywhere)
requires per-episode logging, which is coupled to W2 and is **not yet done**. No
verdict may be issued, and no further experiment fired, until that is complete and
this consequence is resolved in the addendum (W1).

## STATUS: W3 core PASS. Corrections PR INCOMPLETE — see PROGRESS.md. Nothing fired; $0 spent.

## Spend ledger (required; `python scripts/spend_ledger.py`)

```
SPEND LEDGER — envelope $1000
  phase0 (0a+0b+0c)            $    5.13  [frozen pilot]
  h1-full                      $   32.22  prompt=policy_instructed sampling=None   [INVALID §6]
  h1-ladder                    $  120.32  prompt=None sampling=None
  h2-detection                 $   56.60  prompt=None sampling=None                [INVALID §6]
  h3-frontier                  $   54.13  prompt=None sampling=None
  h4-recovery                  $   36.75  prompt=None sampling=None
  ablations                    $   11.98  prompt=None sampling=None
  RUNNING TOTAL                $  317.13  (31.7% of envelope)
```

Note: h1-full and h2-detection ($88.82) are INVALID (§6) and will be re-spent under
the corrected sampler; the envelope accounting keeps the sunk spend visible.
