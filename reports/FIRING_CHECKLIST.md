# FIRING CHECKLIST — Part-4 experiments (human step, outside the session)

Fire the seven `workflow_dispatch` workflows from the **Actions** tab in the order
below. Each is secret-gated (`ANTHROPIC_API_KEY`), prints spend, and writes a
`results/<exp>-live` branch. Spend is bounded by each experiment's PREREG cap and a
**global $1,000 envelope**. Between firings, eyeball the 2–3 numbers named below on
the results branch before firing the next.

**Pre-flight (already green in CI, at $0):**
- `make gigo-verify` — 192-cell mock matrix within tolerance ✅
- `python -m benchmarks.experiments --exp h2-detection --arm live --fake` — live path
  runs end-to-end at $0 (fake agent/critic) ✅
- `make calibrate-check` — taxonomy v1 provenance up to date ✅
- Phase 0 frozen record still verifies (`--prompt naive`) ✅

**Validity precondition (all experiments).** A condition is **INVALID** (no verdict
read) if fewer than **80%** of its paired episodes score — the Phase 0c gate,
generalized. Refusals and parse failures are their own outcome classes, excluded
from ADR, and reported. If a whole experiment comes back mostly INVALID, do **not**
re-interpret — fix instrumentation and re-fire (this is exactly the 0b lesson).

## Cost anchor (from Phase 0, real)

Phase 0 spent **\$5.133** over 300 paired episodes (0a \$1.374, 0b \$1.800, 0c
\$1.959) on `claude-sonnet-5` + `claude-haiku-4-5` judge. That is **≈\$0.0196 per
paired episode** on Sonnet, or **≈\$0.010 per single agent turn**. Per-model
per-turn anchors (scaled by output pricing; upper-bound estimates):

| model | role | ≈\$/agent turn |
|---|---|---|
| `claude-haiku-4-5` | ladder rung / judge | \$0.003 |
| `claude-sonnet-5` | default agent | \$0.010 |
| `claude-opus-4-8` | ladder rung / **arm-C critic** | \$0.030 |
| `claude-fable-5` | ladder top rung | \$0.050 |

Upper-bound agent-call count for a live matrix = `arms × 8 classes × 4 rates × N
episodes` (over-counts — blocked arms skip the agent, so real spend is lower).

## Firing order

### 1. `exp-h1-full.yml` — silence, no gate (cap \$200)
- Arms A. 1×8×4×100 = **3,200** Sonnet turns × \$0.010 ≈ **\$32**. Well under cap.
- **Eyeball:** ADR rises with rate; behavioral marker/judge AUC ≈ 0.5 (silence).

### 2. `exp-h1-ladder.yml` — silence vs capability (cap \$250, most expensive)
- Arm A across **haiku → sonnet → opus → fable**. 3,200 turns per rung:
  haiku ≈\$10, sonnet ≈\$32, opus ≈\$96, fable ≈\$160 → **≈\$298**.
- ⚠️ **Projection exceeds the \$250 cap.** Before firing, **subsample**: drop to
  ~60 episodes/condition (≈\$180) or rates {5%, 20%} (≈\$150). The workflow pauses
  and reports if projected spend crosses the cap — heed it.
- ⚠️ **`claude-fable-5` needs a non-ZDR key** (30-day retention; ZDR orgs 400 on
  every request). Its `stop_reason: "refusal"` is its **own outcome class**, never an
  ADR defect — expect a few. Budget ~5× Sonnet on that rung.
- **Eyeball:** ADR and AUC **flat** across rungs (P1: silence is capability-invariant).

### 3. `exp-h2-detection.yml` — detection asymmetry by channel (cap \$150)
- Arms B, C, D. C adds an **opus-4-8 critic** turn per episode. Agent 3×8×4×100 =
  9,600 Sonnet ≈\$96; critic 8×4×100 = 3,200 opus ≈\$96 → **≈\$150** (upper bound;
  D blocks reduce it). If projection tops \$150, cut to 60 episodes.
- **Eyeball:** on **metadata-borne** classes, C detection ≈ 0 while D detection high
  (the H2 asymmetry); on **payload-visible** classes both detect.

### 4. `exp-h4-recovery.yml` — downstream recovery ratio (cap \$150)
- Arms A, D, E. 3×8×4×100 = 9,600 Sonnet ≈ **\$96**.
- **Eyeball:** arm-D `recovery_ratio` ≥ 0.80 target; false-block ≈ 0 on clean.

### 5. `exp-h3-frontier.yml` — loss-avoided vs false-block (cap \$150)
- Arms C, D, F. Agent ≈\$96 + opus critic (arm C) ≈\$96 → **≈\$150** upper bound.
- **Eyeball:** D dominates B/C on the loss-avoided ÷ false-block frontier.

### 6. `exp-ablations.yml` — each predicate off, one at a time (cap \$100)
- Arm D only, predicate-ablated. ~1×8×4×100 per ablation × #predicates; the gate is
  cheap (deterministic) — cost is the agent turns behind admits ≈ **\$32–\$64**.
- **Eyeball:** turning off `freshness` collapses metadata-borne detection; turning
  off `complete`/`schema_conformant` collapses payload-visible.

### 7. `exp-tier2-validation.yml` — predicates vs labeled real errors (cap \$50)
- Arm D. Predicates are **\$0** (deterministic); cost is **data provisioning**, not
  API. Needs the Tier-2 corpora mounted (`$SARC_DQ_TIER2_DIR`); then re-run
  `python scripts/calibrate_taxonomy.py` so the `computed` rows fill and
  `benchmarks/gigo/CALIBRATION.md` flips flagged defaults to measured values.
- **Eyeball:** injector `default_rate`s land inside the labeled empirical band.

## After all seven land

Fresh session, say **"Part 3"**: `scripts/ingest_results.py` pulls each
`results/<exp>-live` summary into `paper/data/<exp>/` with provenance, re-runs
`make_macros`, runs the committed verdict code per PREREG, writes the Results prose
around the macros (failures/INVALIDs verbatim), and prepares `make arxiv` /
`make final` (watermark stays on until claims sign-off).
