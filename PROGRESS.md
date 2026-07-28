# PROGRESS — sarc-dq campaign tracker

> **HISTORICAL build log.** For the *current* state of every experiment (branch, SHA,
> validity, verdict, ingestion) see [`EXPERIMENT_STATUS.md`](EXPERIMENT_STATUS.md), the
> single source of truth. The H1–H4 campaign is complete; any `[pending]`/"to fire"
> language below is a record of an earlier stage, not an open task.

**Active campaign: MASTER BRIEF FINAL (`CLAUDE_CODE_MASTER_BRIEF_FINAL.md`)** — takes
sarc-dq from CI-green-with-[pending] to arXiv-ready v1.0. Parts 0–2 this session →
human merges + fires workflows → "Part 3" in a fresh session after results land.
Branch `claude/new-session-f1dhsq` off `main`; PR base `main`. Standing rules: no
fabricated result (values flow from committed `reference_summary.json` via macros;
missing/failed render `[pending]` or reported failed); Phase 0 frozen (extend-only);
PREREG verdicts computed by committed code against frozen thresholds (no post-hoc
edits); the DRAFT watermark is removed only by `make final`, which this campaign
PREPARES but NEVER RUNS.

### FINAL campaign — Part status
- [x] **FINAL Part 0 — Research-calibrated taxonomy** — `scripts/calibrate_taxonomy.py`
  (deterministic, $0, `--check` in CI) emits `src/sarc_dq/specs/taxonomy_v1_calibrated.yaml`
  (every parameter carries a provenance block: computed | literature | default+flagged),
  rewrites `benchmarks/gigo/CALIBRATION.md`, and writes `reports/TAXONOMY_VETO_SCREEN.md`
  (≤10-min author veto). Paper: "Taxonomy grounding" subsection (Rahm&Do, Kim,
  Wang&Strong, ISO 8000, Sambasivan) + prevalence anchors (HBR 47%, Experian 17–32%,
  Li/Dong ~70%) + realism band + non-arbitrary-parameter methods sentence + Limitations
  sentence on literature-thin classes; 11 bibliography entries added. Datasets not
  vendored (multi-GB) → CI runs the literature/default path; `computed` rows render as
  flagged defaults naming the pending Tier-2 dataset. **Human item: the veto screen.**
- [x] **FINAL Part 1 — Audit fixes.**
  1. **Live arm wiring** — `src/sarc_dq/live_arms.py` (`apply_arm_live` mirrors the mock
     arm structure exactly; real `claude-sonnet-5` agent + `claude-opus-4-8` payload-only
     `AnthropicCritic`; per-arm spend from usage fields; `FakeAgent`/`FakeCritic` +
     `make_live(fake=)` drive the whole path at $0). `harness.apply_arm` left
     **byte-identical** → gigo-verify still passes (192 cells). `experiments.py --arm live`
     now runs the live matrix (`--fake` = $0 CI); the "not wired" stub is gone.
  2. **`scripts/derive_phase0a_metrics.py`** — derives 0a elasticity + clean-arm regret
     from the committed `results/phase0-live` JSONL with provenance (branch, file,
     commit `d853f7d`). Real values: **elasticity 0.000** (naive agent inelastic),
     **clean_regret_median 2520** — vendored to `paper/data/phase0/phase0a_derived.summary.json`;
     `make_macros` fills `\PZaElasticity`/`\PZaRegret` (0a cells no longer `[pending]`).
     **This retires the 0a human-item candidate** (real, provenance-tracked, not the mock).
  3. **Adversarial zero-write test** (`tests/test_zero_write.py`) — every source record
     bit-identical after quarantine-substitute across all 8 classes (Prop 1 assumption).
  4. **0b footnote** — pilot-table caption marks 0b elasticity diagnostic-only / invalid.
  5. **Provenance SHAs** — `_provenance` blocks on all `paper/data/phase0/*.json` naming
     branch + commit (0a `d853f7d`, 0b `fe504d1`, 0c `3fb4aa3`).
  6. **Citations** — resolved ToolEmu (Ruan, ICLR 2024), τ-bench (Yao, 2406.12045),
     ISO/IEC 5259 (2024), Raha (Mahdavi SIGMOD 2019), Magellan (Konda VLDB 2016),
     AgentNoiseBench; inline `⟨VERIFY⟩` dropped on resolved cites. NoisyToolBench,
     "Tools Fail", AgentSpec, MI9, ISO 8000, Experian, Sambasivan stay `⟨VERIFY⟩`.
  78 tests; gigo mock + Phase 0 frozen both still verify.
- [x] **FINAL Part 2 — Pre-flight + firing checklist + PR.** Pre-flight green at $0:
  full mock matrix + `gigo-verify` (192 cells), live path via `--arm live --fake`,
  `calibrate-check`, Phase 0 frozen record. `reports/FIRING_CHECKLIST.md` — per
  experiment: workflow name, firing order (h1-full, h1-ladder, h2, h4, h3, ablations,
  tier2), budget arithmetic from the Phase 0 per-turn anchor (\$0.010 Sonnet / \$0.030
  Opus critic / \$0.050 Fable) vs each PREREG cap (flags h1-ladder's ~\$298 > \$250 →
  subsample), the 80%-scored validity precondition, fable-5's non-ZDR-key + refusal-
  class note, and 2–3 eyeball numbers per branch. **STOP after the PR is open** — the
  human merges and fires the seven workflows; "Part 3" resumes in a fresh session.

### Human items remaining (target: exactly four)
1. **Taxonomy v1 author veto** — `reports/TAXONOMY_VETO_SCREEN.md` (≤10 min; silence = accept).
2. **Fire the seven experiment workflows** — `reports/FIRING_CHECKLIST.md` (spend-gated, $1000 envelope).
3. **Claims sign-off** — review the compiled paper; only `make final` lifts the DRAFT watermark (prepared in Part 3, never run here).
4. **arXiv upload** — from the author's account (Part 3 produces the `make arxiv` tarball + `CLAIMS_CHECKLIST.md`).

---

## Prior campaign (Build-to-Complete) — merged to main via PR #6

Resume rule: a fresh session reads this file + the brief and
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

- `make paper` compiles: the `paper` workflow builds the PDF via latex-action. Two
  post-hoc build fixes were needed that static macro/brace validation could not catch:
  (a) CI runs bare `pytest`, so the repo root was not on `sys.path` and `benchmarks`
  failed to import — fixed with `pythonpath = ["."]`; (b) the DRAFT watermark's
  `\rotatebox` needs `graphicx`, which was not loaded — added `\usepackage{graphicx}`.
  Full prose + real Phase 0 numbers + `[pending]` everywhere else + DRAFT watermark. ✅
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

---

## Autonomous corrections program (2026-07-09) — IN PROGRESS

Working the CLAUDE_CODE_AUTONOMOUS_CORRECTIONS_AND_RUNS brief (W1–W7 + verification,
then staged firing). Mode: human does not review; every check is executed as code and
written to `reports/VERIFICATION-<date>-<stage>.md`. Nothing fired; $0 spent.

**Merged before this program:** #10 (paired counterfactual loss + materiality),
#11 (policy_instructed prompt — competent, metadata-blind decider).

### Done (committed to branch claude/new-session-f1dhsq)
- **W3 core** — rate-cell sampling independence (`corruption_decision`); live+mock;
  GIGO regenerated; regression tests. `reports/VERIFICATION-2026-07-09-W3.md`.
- **FINDINGS §6** — sampler bug; h1-full (2993ece) + h2-detection (a37bf0b) marked
  INVALID by SHA; 0.585 / 16-16 / $1,080 withdrawn; naive-null retained w/ caveat.
- **ADDENDUM-2026-07-09** (= W1 a/b/c + W5 + GIGO note + elevated naive-null) and the
  **fixed-n sampler** (`stratified_corrupt_indices`; H1/H2 fixed_n=25, others true
  rate; config stamps sampling/fixed_n; resume guards on it).
- **Spend ledger** (`scripts/spend_ledger.py`; $317.13 / 31.7%) + **VERIFICATION_METHOD.md**
  (amended V0 freeze check + ledger requirement). Gate green: ruff, mypy(39), 94 pytest, gigo.

### Blocking consequence (recorded in FINDINGS §6 / addendum)
- `results/h1-full-live` ($32.22) and `results/h2-detection-live` ($56.60) ran under the
  buggy sampler → INVALID → must be re-run under the fixed sampler. Adds ~$89 to the plan.

- **W2 (done)** — transcript capture + per-cell marker AUC + flag fraction in the runner;
  FINDINGS §7 downgrades H1 silence (P2/P3 PENDING instrumented re-run). LLM-judge AUC
  deferred (model pinned in addendum).
- **W3 rest (done)** — per-cell material_flags/paired_losses + n_clean; matrix-level
  `per_class_pooled` with paired-seed bootstrap 95% CIs on ADR and loss.

- **W4 (done)** — `benchmarks/verdicts.py`; H2 verdict NOT SUPPORTED, reframed (FINDINGS §5).
- **config_hash (done)** — sha256 over the scientific config stamped in every live summary.

### Remaining before the corrections PR opens
- **W1 remainder** — paper "Deviations and clarifications" subsection.
- **W6** — tag-triggers + verification-gate on the h4/h3/ladder workflows; self-merge attempt.
- **W7** — rewrite FIRING_CHECKLIST.md → FIRING_PLAN.md (autonomous sequence, corrected costs).
- **V0** — full pre-merge verification battery; then open the PR. Nothing fired; $0 new spend.

### Human items (unchanged): claims sign-off + arXiv upload remain the only human acts.
