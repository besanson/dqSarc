# VERIFICATION — 2026-07-09 — V0 (pre-merge, corrections PR)

Self-verification for the corrections PR (W1–W7). Human does not review; every check
is executed as code with literal output. Method: `reports/VERIFICATION_METHOD.md`.
Nothing fired; $0 new spend.

## V0.1 — PREREG originals unedited; addendum is a new file

`git log --oneline -- reports/prereg/<f>` — each original has exactly ONE commit; the
dated addendum is a separate new file:

```
ablations.md 1 · h1-full.md 1 · h1-ladder.md 1 · h2-detection.md 1
h3-frontier.md 1 · h4-recovery.md 1 · tier2-validation.md 1
ADDENDUM-2026-07-09.md 1 (new)
```

## V0.2 — Frozen files: no existing line modified (amended check; additions allowed)

`git diff origin/main...HEAD --numstat` over `src/sarc_dq/phase0.py`,
`reports/PHASE0*_PREREG.md`, `reports/prereg/*.md` (originals),
`.github/workflows/phase0*.yml`: **empty** (no frozen file touched at all).

## V0.4 — Gate

```
ruff check .                         -> All checks passed!
ruff format --check                  -> clean
mypy src/sarc_dq benchmarks scripts  -> Success: no issues found in 40 source files
pytest -q                            -> 98 passed  (was 95 before W2/W3-rest/W4; non-decreasing)
make gigo-verify                     -> gigo verify: OK (192 cells within tolerance)
make verify                          -> verify: OK (4 metrics within tolerance); Phase 0
                                        config hash c8202a18b58754d8 (frozen) preserved
```

## V0.5 — W3 mock proof (rate cells independent)

`tests/test_gigo.py::test_mock_matrix_rate_cells_differ` and
`::test_rate_cells_are_independent_not_nested` pass: no two rate cells are byte-identical
and the sampler masks are neither identical nor nested (0.02≠0.05, 0.02⊄0.05).
Per-class pooled ADR + paired-seed bootstrap 95% CI appears in the summary schema
(`per_class_pooled`), verified by `test_summary_carries_silence_and_pooled_ci`.

## V0.6 — Gate-freeze (no new predicate)

`git diff origin/main...HEAD --stat -- src/sarc_dq/gate.py src/sarc_dq/dq_spec.py
src/sarc_dq/specs/dq_predicates.yaml`: **empty**. No predicate added/removed/reparam.

## V0.7 — Hand-typed audit (paper)

`grep -rnE "0\.585|1,?080|0\.727|13\.12|32\.2|56\.6|0\.976|0\.992" paper/*.tex`:
**empty**. No result literal is hand-typed in the paper; all flow through macros.

## W2 outcome

Silence is instrumented (per-cell `marker_auc`, `flag_fraction`; `sarc_dq.markers`).
Prior runs logged no transcripts, so the H1 silence verdict is DOWNGRADED (FINDINGS §7):
"P1 loss-conversion supported (policy_instructed); silence P2/P3 PENDING an instrumented
re-run." LLM-judge AUC deferred (paid; model pinned in addendum B).

## W4 outcome — H2 verdict (`benchmarks/verdicts.py` on `results/h2-detection-live`)

```
VERDICT H2: NOT SUPPORTED  (P1=FAIL, P2=FAIL)
  schema_drift              payload-visible  C0.00 D1.00  FAIL  [P1 |C-D|=1.00>0.15]
  missing_mandatory_field   payload-visible  C0.77 D1.00  FAIL  [P1 |C-D|=0.23>0.15]
  plausible_outlier         metadata-borne   C0.00 D0.00  FAIL  [P2 D<0.80]
  silent_unit_change        metadata-borne   C0.00 D0.00  FAIL  [P2 D<0.80]
  superseded_golden_record  metadata-borne   C1.00 D1.00  FAIL  [P2 C>0.10]
  (stale_master_data, cross_source_contradiction, duplicate_vendor: pass)
```

Reframed failed-then-reframed in FINDINGS §5. NB: run on §6-invalid h2 data; re-issued
on the corrected re-run. Verdict is qualitatively stable (detection is per-corrupted).

## Spend ledger (`python scripts/spend_ledger.py`)

```
RUNNING TOTAL $317.13 / $1000 (31.7%)  — incl. h1-full/h2-detection ($88.82) marked
INVALID (§6); corrected re-runs pending per FIRING_PLAN.md.
```

## STATUS: V0 PASS. Corrections PR ready. No experiment fired; $0 new spend. Merge is a single action; firing (stage 1) is a separate session, gated on the merge.
