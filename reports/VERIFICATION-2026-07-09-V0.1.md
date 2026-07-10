# VERIFICATION — 2026-07-09 — V0.1 (pre-fire closeout, reviewer conditions)

Reviewer pre-fire conditions before stage 1. Diff since merged `main` is **docs-only**
(`paper/sarc-dq.tex`, `reports/FINDINGS.md`, `reports/FIRING_PLAN.md`,
`reports/prereg/ADDENDUM-2026-07-09.md`); no `.py` touched, so the code gate is
unchanged from the merged 98-passing state. Nothing fired; $0 new spend.

## 1. INVALID-table completeness (FINDINGS §6)

All six first-wave branches present, each with SHA / spend / grounds:

```
h1-full ✓  h2-detection ✓  h3-frontier ✓  h4-recovery ✓  h1-ladder ✓  ablations ✓
audit sentence present ✓ ("All first-wave experiment runs are invalid and retained
                           on their branches for audit.")
```

## 2. Budget realism (judge cost + trim rule)

FIRING_PLAN estimates now carry an explicit judge line (one `claude-haiku-4-5` turn per
transcript, both arms): h1-full ~\$36, h2 ~\$69, h4 ~\$102, h3 ~\$152, ladder ~\$316.
Full-scale re-runs ~\$675; \$317 sunk + \$675 = ~\$992 (over once ±30% admitted), so
**addendum C.1 Fable-trim applies to stage 5**, bringing the campaign to ~\$0.92k. C.1
is dated and appended to the addendum (halve Fable-5 cell count; trim by this rule only;
never breach \$1000). Addendum C now records the portfolio-level endpoint rule.

## 3. Paper plainness — four verbatim sentences present (whitespace-normalized)

```
(a) integrity: "No threshold, prediction, or verdict rule was altered ... under a dated addendum" ✓
(b) silence:   "the silence claim (P2/P3) rests on Phase 0c and is reported as PENDING ..." ✓
(c) first-wave: "All first-wave experiment runs are invalid and retained on their branches for audit" ✓
(d) H2:        "H2 is expected to fail its original registration again ... the reframe, not the pass ..." ✓
```

No `pdflatex` in this environment; sentences verified in `paper/sarc-dq.tex` source
(LaTeX reflows text, so source presence ⇒ compiled presence). No result literal is
hand-typed (V0.7 audit remains empty).

## 4. Quality gate

```
git diff --name-only origin/main...HEAD  -> docs only (0 .py files)
ruff check .                             -> All checks passed!
mypy src/sarc_dq benchmarks scripts      -> Success: no issues found in 40 source files
make gigo-verify                         -> gigo verify: OK (192 cells within tolerance)
make verify                              -> verify: OK; Phase 0 hash c8202a18b58754d8 (frozen)
pytest -q                                -> 98 passed (unchanged; no .py in the diff)
```

## 5. Ledger (`python scripts/spend_ledger.py`)

```
RUNNING TOTAL $317.13 / $1000 (31.7%) — all six experiment rows are INVALID first-wave
(FINDINGS §6). Projected campaign incl. judge + Fable-trim ~$0.92k, under the envelope.
```

## STATUS: V0.1 PASS. Cleared to merge and fire stage 1 (exp-h1-full) per FIRING_PLAN.md.
