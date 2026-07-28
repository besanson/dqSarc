# CLAIMS CHECKLIST — SARC-DQ v1.0.0-rc

Every quantitative claim in the paper, mapped to the committed run it comes from. Sign-off
means: each row's number matches the cited macro and the cited results branch, and no number
is hand-entered. Regenerate with `python paper/scripts/ingest_results.py && python
paper/scripts/make_macros.py`; the macros live in `paper/generated/results.tex`.

**Integrity boundary:** no threshold, prediction, or verdict rule was altered at any point;
only instrument configuration, under a dated addendum (`reports/prereg/ADDENDUM-2026-07-09.md`).
Every experiment run cited below is on the cap-hardened harness
(`instrumentation=api-error-aware-v1`, 0 API errors).

## Experiment provenance (all VALID, hardened harness)

| exp | branch @ SHA | run id | config_hash | spend | cells |
|---|---|---|---|---|---|
| h1-full | `results/h1-full-live` @ `fac16e5` | 29095598109 | `835a81b3602bb435` | $34.88 | 32/32 |
| h2-detection | `results/h2-detection-live` @ `aac7518` | 29101951327 | `b52ba463e0e1b9b4` | $122.93 | 96/96 |
| h1-ladder | `results/h1-ladder-live` @ `6a1ee4d` | 30332532378 | `63ea99e0e8ea046d` | $182.62 | 128/128 |
| h4-recovery | `results/h4-recovery-live` @ `a9a4b38` | 30282599910 | `0d606d9b7730cc95` | $99.12 | 96/96 |
| h3-frontier | `results/h3-frontier-live` @ `9bfff1f` | 30296664147 | `32c0c09dd052f859` | $115.16 | 96/96 |

## Claims → macros → source

| # | claim (paper) | macro | value | verdict | source |
|---|---|---|---|---|---|
| 1 | H1 metadata-borne ADR (loss-conversion) | `\HoneFullMetaAdr` | 60% | **SUPPORTED** (≥20%) | h1-full arm A, META classes |
| 2 | H1 ladder ADR, haiku rung | `\HoneLadderAdrHaiku` | 60% | — | h1-ladder |
| 3 | H1 ladder ADR, fable rung | `\HoneLadderAdrFable` | 62% | — | h1-ladder |
| 4 | H1 ladder marker AUC (max over rungs) | `\HoneLadderAuc` | 0.50 | **SUPPORTED** (≤0.60) | h1-ladder |
| 5 | H1 ladder flag fraction (max over rungs) | `\HoneLadderFlag` | 0% | **SUPPORTED** (<5%) | h1-ladder |
| 6 | **H1 headline: silence + loss flat across capability** | `\ResHoneLadder` | SUPPORTED | **SUPPORTED** | h1-ladder |
| 7 | H2 payload-critic detection on metadata | `\HtwoCriticMeta` | 25% | REFRAMED | h2 arm C, META |
| 8 | H2 gate detection on metadata | `\HtwoGateMeta` | 50% | REFRAMED | h2 arm D, META |
| 9 | H3 gate detection | `\HthreeGateDet` | 62% | see #12 | h3 arm D |
| 10 | H3 realistic-critic detection | `\HthreeCriticDet` | 31% | see #12 | h3 arm C |
| 11 | H3 gate vs critic residual loss | `\HthreeGateResid`/`\HthreeCriticResid` | 294 / 311 | see #12 | h3 arms D,C |
| 12 | H3 Pareto-dominance (as written) | `\ResHthree` | NOT SUPPORTED | **NOT SUPPORTED** | h3 (degenerate false-block; F(v) partial oracle) |
| 13 | H4 portfolio recovery ratio | `\HfourRecovery` | −0.04 | **NOT SUPPORTED** (≥0.80) | h4 arms A/D/E pooled |
| 14 | H4 freshness recovery (stale loss A→D) | `\HfourStaleLossA`/`\HfourStaleLossD` | 134 → −0.5 | covered channel | h4 stale_master_data |

## Verification — DONE (agent-verified 2026-07-13)

- [x] `python paper/scripts/ingest_results.py` reproduces `paper/data/*/reference_summary.json` with the SHAs above (deterministic; no drift).
- [x] `python paper/scripts/make_macros.py` yields `paper/generated/results.tex` with **no** `\pending` among h1/h2/h3/h4 macros.
- [x] Independent cross-check of 3 macros straight from the committed raw summaries: H1-full meta-ADR = 0.6025 → 60% (macro 60%); H4 recovery = −0.041 (macro −0.04); ladder fable meta-ADR = 0.6175 → 62% (macro 62%). All match.
- [x] Abstract/intro headline matches row #6 (H1 supported, capability-invariant) and does not overclaim H3/H4; Deviations states H2/H3/H4 as not-supported and discloses the spend-cap incident (items v–vii).
- [ ] `make paper` compiles the PDF — **requires a LaTeX toolchain** (not in the sandbox); run on your machine or let CI (`paper.yml`) do it.

## Still needs YOUR eyes before upload (agent cannot verify)

- [ ] **Confirm the `\verifyc`-flagged references exist.** 13 citations were marked "verify" (the agent has no web access to check them). In `paper/arxiv/sarc-dq.tex` the marker renders nothing, so the PDF is clean — but confirm these are real papers before submitting: `noisytoolbench`, `toolsfail`, `sarc` (arXiv:2605.07728), `greensarc` (arXiv:2606.15954), `iso8000`, `experian2017`, plus the AgentSpec/MI9 guardrail sentence (§related work) and the "Tools Fail" / ISO / CHI entries. Grep: `grep -n '\\verifyc' paper/sarc-dq.tex`.

## Not-run (reported as such; not ingested)

- `ablations`, `tier2-validation` — `\ResAblations`, `\ResTier` render `[pending]`; the paper labels them "not run in this campaign."
- First-wave runs and the cap-truncated h4 (`701c38e`) — INVALID, retained on branches for audit (FINDINGS §6, §8), **not** ingested.

## Human-only remaining acts

1. Sign off this checklist.
2. `make final` (watermark removal) — prepared, **never run by the agent**.
3. arXiv upload.
