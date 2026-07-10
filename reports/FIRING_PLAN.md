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
| 1 | `exp-h1-full` | fixed_n=25 | ~\$32 | corrections PR merged; V0 passed |
| 2 | `exp-h2-detection` | fixed_n=25 | ~\$57 | stage 1 VERIFICATION pass + ledger |
| 3 | `exp-h4-recovery` | rate | ~\$90 | stage 2 pass + ledger |
| 4 | `exp-h3-frontier` | rate | ~\$140 | stage 3 pass + ledger |
| 5 | `exp-h1-ladder` | fixed_n=25 | ~\$300 ⚠️ | stage 4 pass + ledger; **subsample** |

⚠️ The 4-model ladder at 100 episodes projects **over its \$250 cap** (policy_instructed
roughly tripled per-call cost). Subsample to ~60 episodes or rates {label subset} so the
projection lands under the cap; the workflow stops-and-reports if it would exceed.

Envelope: sunk spend is **\$317** (incl. the two invalid runs); the corrected re-runs add
~\$620, for ~\$0.94k against the **\$1000** cap — tight. `python scripts/spend_ledger.py`
is pasted in every VERIFICATION report; a stage that would cross the envelope does not fire.

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
