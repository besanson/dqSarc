# PHASE 0 — Closeout

**Verdict: SUPPORTED** (on the valid run, 0c). The silent-failure effect exists,
and — crucially — it is *conditional on agent competence*. Phase 0 is closed; the
record is frozen. This note is the human-readable summary; every number here is
also carried in `paper/data/phase0/reference_summary.json` (sourced from the three
committed `results/*-live` branches), and the paper renders from that file — no
number below is hand-authored into the paper.

## The three runs

| run | prompt | scored | verdict | ADR | oracle-ADR | elasticity | marker/judge AUC | flags | spend |
|---|---|---|---|---|---|---|---|---|---|
| **0a** | naive | 89/100 | AMBIGUOUS | **0%** | 0.438 | — ¹ | 0.500 / 0.500 | 0% | $1.374 |
| **0b** | policy | 5/100 | ~~SUPPORTED~~ ² | 0.60 | 0.40 | 0.976 | 0.500 / 0.500 | 0% | $1.800 |
| **0c** | policy | 100/100 | **SUPPORTED** | **0.42** | 0.43 | **0.992** | 0.505 / 0.500 | 0% | $1.959 |

Total live spend across all three runs: **$5.13** (`claude-sonnet-5` agent,
`claude-haiku-4-5` judge).

## What Phase 0 established

1. **Silence is real and capability-plausible.** On the valid run (0c) the agent
   acts on a stale price 42% of the time (ADR 0.42, essentially matching the
   metadata-blind oracle's 0.43) while its transcripts carry **no** discriminating
   signal of doubt — behavioral marker AUC 0.505, judge AUC 0.500 (both at
   chance), explicit data-flags 0%. The corruption converts into wrong actions
   and leaves no trace.

2. **Competence buys conversion, not detection — the incompetence shield.** The
   naive agent (0a) is *inelastic*: it barely moves its order with the price, so a
   stale price does not convert (ADR 0%). It is protected from the defect only by
   being bad at the task. The policy-instructed agent (0c) is *elastic*
   (0.992 — it tracks the newsvendor optimum) and therefore *inherits* the
   corruption (ADR 0.42). Making the agent better at its job made it more
   vulnerable, because the discriminating signal was never in its context at any
   competence level. This is the paper's central finding.

3. **A validity gate, produced by our own instrumentation failure.** Run 0b
   returned **SUPPORTED** on only **5 of 100** scored pairs — the agent's replies
   were truncated (reasoning consumed a 512-token budget before the `ORDER:` line)
   and the brittle parser dropped the rest. A verdict read off 5 pairs is
   meaningless. 0b is reported *as-is*, as methods integrity, and it directly
   motivated the Phase 0c **validity precondition**: any run scoring < 80/100 is
   `INVALID` regardless of metrics. We caught garbage-in-garbage-out **in our own
   measurement pipeline** — a fitting first result for a data-quality project, and
   it is reported as such rather than hidden.

## Kill criterion (as applied to 0c)

- `INVALID` if scored < 80/100 — **passed** (100/100).
- H1 *supported* if AUC ≤ 0.60 **and** ADR ≥ 20% — **met** (AUC 0.505, ADR 42%).
- H1 *in trouble* if AUC ≥ 0.65 or flags ≥ 30% — not triggered.

## Frozen record

Extend-only, never altered by later phases: the three `results/*-live` branches;
`reports/PHASE0B_PREREG.md` and `reports/PHASE0C_PREREG.md`; the substrate,
metrics, and stale-price injector semantics as of Phase 0c; and the three
`phase0*-live.yml` workflows. `--prompt naive|policy_instructed` on the Phase 0
CLI reproduces identically (config hashes `c8202a18b58754d8` /
`e785bdc87009b84c`).

---

¹ 0a's committed summary has `elasticity_median` and `clean_regret` as `null` —
its instrumentation predated those metrics. The build brief cites 0a elasticity
0.000 / regret 2519 from a *naive-under-0c* re-run that is not in any committed
results branch; per the no-fabrication rule we render the committed value and flag
it (see `PROGRESS.md`, human items).
² 0b's `SUPPORTED` is struck through because the validity precondition — added in
response to this very run — reclassifies it `INVALID`.
