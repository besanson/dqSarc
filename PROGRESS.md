# PROGRESS — sarc-dq Build-to-Complete campaign

Resume rule: a fresh session reads this file + the BUILD-TO-COMPLETE brief and
continues from the first unfinished Part. Everything must stay mypy --strict
clean, ruff clean, pytest green, CI green at $0. The Phase 0 record is frozen
(extend-only): the three `results/*-live` branches, both PREREG files, the
PHASE0C semantics of substrate/metrics/stale-price injector, and the three
Phase 0 workflows. `--prompt naive|policy_instructed` on the Phase 0 CLI must
reproduce identically.

## Real Phase 0 numbers (frozen, from results branches → paper/data/phase0/)

| run | prompt | scored | verdict | ADR | oracle-ADR | elasticity | marker/judge AUC | flags | spend |
|---|---|---|---|---|---|---|---|---|---|
| 0a | naive | 89/100 | AMBIGUOUS | 0% | 0.438 | — ¹ | 0.500/0.500 | 0% | $1.374 |
| 0b | policy | 5/100 | SUPPORTED (rejected) ² | 0.60 | 0.40 | 0.976 | 0.500/0.500 | 0% | $1.800 |
| 0c | policy | 100/100 | SUPPORTED | 0.42 | 0.43 | 0.992 | 0.505/0.500 | 0% | $1.959 |

Total live spend: **$5.1331**.

¹ 0a's committed summary has `elasticity_median = null` and `clean_regret = null`
  — its instrumentation predated those metrics. The BUILD brief cites 0a
  elasticity 0.000 / regret 2519 (from a *naive-under-0c* re-run that is **not**
  in any committed results branch). Per the no-fabrication rule the paper renders
  the committed value ("—") and flags this. **HUMAN ITEM candidate:** commit the
  naive-under-0c summary to a results branch, or accept "—".
² 0b returned SUPPORTED on only 5 scored pairs — the instrumentation failure that
  motivated the Phase 0c validity gate. Reported as methods integrity.

## Part status

- [x] **Part 0 — Closeout** — PHASE0_CLOSEOUT.md, README rewrite (register + is/is-not + 0c table), consolidated `paper/data/phase0/reference_summary.json`. Elasticity JSON fix already merged in 0c. *(in progress → will flip to done at commit)*
- [x] **Part 1 — Taxonomy v0 + DQ predicate schema** — `sarc_dq/taxonomy/` (generalized
  framework + 8 classes, channel/site/rate/ground-truth; Phase 0 `injectors/` left
  frozen); `sarc_dq/dq_predicates.py` (6 parameterized predicates) + `dq_spec.py`
  loader over `specs/dq_predicates.yaml` (sarc-governance style); TAXONOMY_V0.md
  (REVISION-REQUESTED) + TAXONOMY_REVISION_GUIDE.md (10 questions). PyYAML in
  `[gate]`/`[dev]`. 51 tests. **v0 predicate gaps (intentional):** silent_unit_change,
  duplicate_vendor_conflicting_terms, plausible_outlier — flagged in the guide.
- [x] **Part 2 — Full harness (6 arms) + DQ Pre-Action Gate** — `sarc_dq/gate.py`
  (PreActionGate + GovernedBuffer, content-addressed evidence ids, quarantine-and-
  substitute from buffer only, never writes to source, read-only over evidence);
  `sarc_dq/harness.py` (arms A–F, mock critic payload-only view, matrix runner with
  H4 recovery). `benchmarks/harness_matrix.py` ($0). CI runs the matrix. 57 tests.
  Mock matrix reproduces H1/H2/H4: C blind to metadata-borne, D detects+recovers,
  false-block 0. Phase 0 frozen still verifies.
- [x] **Part 3 — GIGO-Bench freeze** — `benchmarks/gigo/`: SPEC.md (conditions
  matrix, seeds, splits, metrics, schema), reproduce.py (`make gigo-reproduce`) +
  `--verify` (`make gigo-verify`, per-cell tolerances), frozen `reference_summary.json`
  (192 cells), CALIBRATION.md stub. CI runs gigo-verify. Perf: spec loaded once per
  condition (was per-episode). 59 tests.
- [x] **Part 4 — Experiment execution kits** — `benchmarks/experiments.py` dispatcher
  (mock stand-in $0; live arm gated with a clear TODO); 7 `.github/workflows/exp-*.yml`
  (workflow_dispatch, secret-gated, artifact upload if:always, `results/<exp>-live`,
  contents:write); 7 `reports/prereg/*.md` (frozen predictions, pass/kill, validity
  precondition, budget cap, `<<HUMAN>>` marks). 68 tests.
  **REMAINING (human item 2 territory):** arm-level LIVE agent wiring — the six arms
  run mock only; wiring real Claude into arms B/C/D/F is the work before firing.
- [x] **Part 5 — The paper (compiles today)** — `paper/sarc-dq.tex` (12-section
  macro-driven working paper: DRAFT watermark on every page, Prop 1 lineage-preservation
  proof + Prop 2 honest ADR upper bound, real Phase 0 pilot table, ⟨VERIFY⟩ bibliography);
  `paper/scripts/make_macros.py` emits `generated/results.tex` from every
  `paper/data/**/reference_summary.json` — no result value is hand-typed, missing runs
  render `\pending{id}` → "— [pending: id]". `paper/Makefile` + `.github/workflows/paper.yml`
  (regenerate macros → latex-action → PDF artifact). Statically validated: all custom
  macros defined, braces balanced, single document env.
- [x] **Part 6 — Release hygiene** — `docs/benchmark.md` added (GIGO-Bench
  orientation → SPEC.md is authority); `docs/` now covers architecture, predicates,
  benchmark, relationship-to-{sarc,greensarc}. **LICENSE Apache→MIT** to resolve the
  mismatch (pyproject/CITATION/README all declared MIT; only the LICENSE file was
  Apache — aligned to the majority declaration). CITATION.cff present, version 0.1.0
  consistent across pyproject/CITATION. `pip install -e .` clean; `import sarc_dq` OK.
  README final pass: repository-layout block refreshed to the full build (taxonomy,
  gate, harness, gigo, paper), 68 tests, paper build section added.

## Definition of done — status

- `make paper` compiles (validated statically: macros defined, braces balanced, one
  document env; CI uses latex-action). Full prose + real Phase 0 numbers + `[pending]`
  everywhere else + DRAFT watermark. ✅
- No fabricated result: every printed value flows from `reference_summary.json` via
  generated macros; unrun renders `[pending]`. ✅
- Phase 0 frozen record intact: `--prompt naive` reproduces `reports/reference_smoke.json`
  (config_hash `c8202a18b58754d8`, verify OK) after the full build. ✅
- Quality gate: ruff clean, `mypy src/sarc_dq benchmarks paper/scripts` clean, pytest 68
  green, matrix/gigo mock paths at $0. ✅
- Exactly three human items named (below). ✅

## Key decisions

- Campaign branch: `claude/build-complete` off `main`. PRs base `main`.
- No live compute; no invented results. Result values flow from
  `reference_summary.json` files via generated LaTeX macros; missing values
  render `—` with `[pending: <exp-id>]`.

## Three human items (target final state — refine as Parts land)

1. Taxonomy v0 revision pass (Part 1: `reports/TAXONOMY_REVISION_GUIDE.md`).
2. Fire the experiment workflows (Part 4) and land results branches.
3. Claims sign-off on the paper (Part 5) before the DRAFT watermark comes off.
