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
- [ ] **Part 1 — Taxonomy v0 + DQ predicate schema**
- [ ] **Part 2 — Full harness (6 arms) + DQ Pre-Action Gate**
- [ ] **Part 3 — GIGO-Bench freeze**
- [ ] **Part 4 — Experiment execution kits**
- [ ] **Part 5 — The paper (compiles today)**
- [ ] **Part 6 — Release hygiene**

## Key decisions

- Campaign branch: `claude/build-complete` off `main`. PRs base `main`.
- No live compute; no invented results. Result values flow from
  `reference_summary.json` files via generated LaTeX macros; missing values
  render `—` with `[pending: <exp-id>]`.

## Three human items (target final state — refine as Parts land)

1. Taxonomy v0 revision pass (Part 1: `reports/TAXONOMY_REVISION_GUIDE.md`).
2. Fire the experiment workflows (Part 4) and land results branches.
3. Claims sign-off on the paper (Part 5) before the DRAFT watermark comes off.
