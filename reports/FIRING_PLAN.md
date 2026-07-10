# FIRING PLAN (autonomous) — supersedes FIRING_CHECKLIST.md

Replaces the human firing checklist. Firing is **autonomous, one stage per session**:
each stage verifies the prior stage, checks the spend ledger, fires one workflow by
pushing a tag, and ends. A stage never fires on an unmerged corrections PR, and never
if any verification fails (FAILURE PROTOCOL: stop, commit the report, spend nothing).

Method and gates: `reports/VERIFICATION_METHOD.md`. Predictions: `reports/prereg/*.md`
+ `reports/prereg/ADDENDUM-2026-07-09.md`. Verdicts: `benchmarks/verdicts.py`.

## Pinned config (addendum B; every run must stamp a matching `config_hash`)

`prompt_variant=policy_instructed` · agent `claude-sonnet-5` · critic `claude-opus-4-8`
· ladder `haiku→sonnet→opus→fable` · `loss_model=paired-counterfactual-v2`
· `base_seed=20260707` · `tau_m=0.005`. Sampling: **fixed_n=25** for h1-full,
h1-ladder, h2-detection; **true rate** for h3-frontier, h4-recovery, ablations.

## Why the runs below (all under the corrected code)

The previously-committed `h1-full` and `h2-detection` used the buggy sampler (FINDINGS
§6) and the wrong prompt path — both **INVALID**, both re-run here. `h3`/`h4` never ran
under `policy_instructed`. So the corrected campaign re-runs the full set.

## Sequence (one stage per session; corrected costs)

| # | workflow | sampling | est. $ | verify before firing |
|---|---|---|---|---|
| # | workflow | sampling | agent+critic | judge | stage est. | gate |
|---|---|---|---|---|---|---|
| 1 | `exp-h1-full` | fixed_n=25 | ~\$32 | ~\$4 | **~\$36** | PR merged; V0.1 passed |
| 2 | `exp-h2-detection` | fixed_n=25 | ~\$57 | ~\$12 | **~\$69** | stage 1 pass + ledger |
| 3 | `exp-h4-recovery` | rate | ~\$90 | ~\$12 | **~\$102** | stage 2 pass + ledger |
| 4 | `exp-h3-frontier` | rate | ~\$140 | ~\$12 | **~\$152** | stage 3 pass + ledger |
| 5 | `exp-h1-ladder` | fixed_n=25 | ~\$300 | ~\$16 | **~\$316** ⚠️ | stage 4 pass + ledger; **trim** |

**Judge-scoring cost (addendum B / reviewer).** Every stage now includes a
`claude-haiku-4-5` **judge turn per transcript, both arms** (the agent's order transcript
and its clean-price counterfactual), for the H1 silence AUC. Modelled at ~\$0.001/judge
turn (short transcript in, a score out) × the agent-transcript count.

**Envelope arithmetic.** Sunk first-wave spend (all INVALID, still on branches) is
**\$317**. Corrected re-runs at full scale total **~\$675** (incl. judge), so
\$317 + \$675 = **~\$992** — at the ragged edge of the **\$1000** cap, and over it once
estimate uncertainty (±30%) is admitted. **The addendum C.1 Fable-trim rule therefore
applies to stage 5** (halve the Fable-5 cell count — Fable is the cost driver), bringing
the ladder to ~\$240 and the campaign to **~\$0.92k**, safely under. `python
scripts/spend_ledger.py` is pasted in every VERIFICATION report; a stage whose ledger +
remaining estimates would cross \$1000 does not fire until trimmed per C.1.

## Per-stage procedure (autonomous)

1. `git fetch` the prior stage's `results/<exp>-live`; run `benchmarks.verdicts` (where a
   verdict exists) and the V-run checks (`reports/VERIFICATION_METHOD.md`): validity
   (≥80% scored), `config_hash` matches the addendum, no two rate cells byte-identical,
   spend within cap. Write `reports/VERIFICATION-<date>-<stage>.md` with literal output.
2. If all pass: push the stage's tag (`run-<exp>-<date>`) to fire; **end the session**.
3. On any failure: stop, commit the failing report, spend nothing, end.

## After stage 5

Ingest every `results/<exp>-live` into `paper/data/<exp>/` with provenance (branch, SHA,
run URL), re-run `make_macros`, run all verdicts, write Results prose around the macros
(failures/INVALIDs verbatim), and prepare `make arxiv` / the v1.0.0-rc PDF +
CLAIMS_CHECKLIST.md. `make final` (watermark removal) is prepared, never run; claims
sign-off + arXiv upload remain the only human acts.
