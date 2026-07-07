# SARC-DQ

**Runtime data-quality gating for agentic AI.** The third SARC pillar — SARC
governs *obligations*, [Green SARC](https://github.com/besanson/greensarc) governs
*cost + carbon*, **SARC-DQ governs *evidence quality*** — built on the same thesis:
**enforcement placement beats model intelligence.** A data-defect that is
invisible in a record's payload (a stale price, a superseded golden record) never
enters the agent's context, so no amount of model capability catches it — but a
Pre-Action Gate with *metadata access* does.

![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Typed](https://img.shields.io/badge/mypy-strict-blue)

> ### Status — read this first
>
> **Alpha, research artifact — this is *not* a turnkey production system.**
>
> **What it *is* right now:** **Phase 0 is closed and SUPPORTED** (see
> [`reports/PHASE0_CLOSEOUT.md`](reports/PHASE0_CLOSEOUT.md)) on a real 3-run live
> pilot ($5.13, `claude-sonnet-5`). The `build-to-complete` campaign then adds, on
> top of that pilot: the corruption taxonomy v0 + DQ predicate schema, the six-arm
> harness and DQ Pre-Action Gate, the frozen GIGO-Bench spec, experiment execution
> kits (built, not run), and a compiling working paper whose every result value is
> macro-generated from `reference_summary.json` files. Progress is tracked in
> [`PROGRESS.md`](PROGRESS.md). Everything is typed (`mypy --strict`), tested, and
> green under CI at **$0** — every arm and every injector has a deterministic mock
> path.
>
> **What it *is not* yet:** the H1–H4 experiments have **not been run** — their
> result cells render `—` `[pending]` under a DRAFT watermark until the workflows
> are fired. No H1–H4 number in this repo is invented; the only measured numbers
> are the Phase 0 pilot's. Three human items remain (see bottom of this README).

## The conversion chain

```
   data defect  ──►  (invisible in payload)  ──►  agent acts on it  ──►  wrong action  ──►  currency loss
   (stale price)         silent                    no expressed doubt      wrong order       vs clean counterfactual
```

SARC-DQ measures every arrow, in currency, against a certifiably-clean paired
counterfactual — and (from Phase 1 on) inserts a metadata-aware gate that breaks
the chain **downstream only**: it never writes to source systems; repairs and
substitutions live in a governed buffer, and every admitted action logs a
versioned evidence set (full lineage back to the exact records it relied on).

## Quickstart

```bash
pip install -e ".[dev]"     # zero-dependency core; dev extras add ruff/mypy/pytest
make quality                # ruff + format + mypy --strict + pytest  (all green)
make smoke                  # Phase 0 smoke test → reports/SMOKE_TEST.md  ($0, offline mock)
```

To run the **real** experiment (live Claude), see
[`reports/GATE0_BRIEF.md`](reports/GATE0_BRIEF.md):

```bash
pip install -e ".[dev,live]" && export ANTHROPIC_API_KEY=sk-...
python -m benchmarks.phase0_smoke --arm live --episodes 100
```

## Headline — Phase 0 pilot (real live numbers, run 0c)

Source: `results/phase0c-live` → `paper/data/phase0/reference_summary.json`
(`claude-sonnet-5` agent, `claude-haiku-4-5` judge). This is a **pilot**, not the
GIGO-Bench matrix.

| metric (0c, valid: 100/100 scored) | value |
|---|---|
| Action Defect Rate (agent) | **42%** |
| Action Defect Rate (metadata-blind oracle) | 43% |
| Decision elasticity (agent tracks the optimum) | 0.992 |
| Behavioral marker AUC | 0.505 |
| LLM-judge doubt AUC | 0.500 |
| Explicit data-flag rate | 0% |
| Kill-criterion verdict | **SUPPORTED** |

**Competence buys conversion, not detection.** The *naive* agent (run 0a) is
inelastic — it barely tracks the price, so a stale price doesn't convert (ADR 0%),
protected only by being bad at the task. The *policy-instructed* agent (0c) is
elastic (0.992) and therefore inherits the corruption (ADR 42%) while expressing
no doubt (AUC ≈ chance). Making the agent better made it more vulnerable, because
the discriminating signal was never in its context. A methods-integrity aside: run
0b returned `SUPPORTED` on only **5/100** scored pairs — garbage-in-garbage-out in
our *own* pipeline — which is exactly why the harness now has a validity gate
(`INVALID` if scored < 80/100). Full story: `reports/PHASE0_CLOSEOUT.md`.

## How it maps to the source repos

| SARC-DQ needs | reused from | how |
|---|---|---|
| priced replenishment environment | `greensarc` IBP benchmark | extended from a token-cost *simulation* into a real, LLM-driven newsvendor *decision* whose quality depends on a corruptible price |
| reproducibility (`make reproduce`/`verify`, reference JSON, tolerance checks, CI) | `greensarc` | mirrored: seeded config hashes, frozen reference summary, per-metric verify |
| constraint spec / predicate machinery (`class`, `verif`, `response`, predicate registry) | `sarc-governance` | the DQ predicate schema (Phase 1) is authored in the same YAML style |
| four enforcement sites + trace stores + hash-chain evidence | `sarc-governance` | the Pre-Action Gate and versioned-evidence-set semantics (Phase 2) build on these |

## Repository layout

```
src/sarc_dq/
  config.py        frozen run config, model-ID pins, config-hash + seed registry
  records.py       EvidenceRecord: payload/metadata split, versioned evidence ids
  substrate.py     priced newsvendor IBP episode (paired counterfactuals)
  injectors/       Phase 0 stale-price class (channel-tagged) — frozen
  taxonomy/        corruption taxonomy v0: framework + 8 channel/site-tagged classes
  dq_predicates.py 6 parameterized DQ predicates (freshness, lineage, …)
  dq_spec.py       YAML constraint-spec loader (sarc-governance style)
  specs/           dq_predicates.yaml — the constraint spec
  gate.py          PreActionGate + GovernedBuffer (downstream-only remediation)
  harness.py       6 mitigation arms (A–F) + matrix runner with H4 recovery
  agent/           payload-only decision interface; mock + live Claude agents
  judge/           LLM-judge doubt scoring; mock + live; 20 hand-checkable cases
  markers.py       lexical uncertainty / data-flag markers
  metrics.py       loss, ADR, discrimination AUC, paired-seed bootstrap CIs
  phase0.py        the Phase 0 protocol (dual-channel logging)
  report.py        renders reports/SMOKE_TEST.md from logged results only
benchmarks/
  phase0_smoke.py  Phase 0 runnable entrypoint + --verify
  gigo/            GIGO-Bench: SPEC.md, reproduce.py (--verify), reference (192 cells)
  experiments.py   H1–H4 dispatcher (mock $0; live arm gated)
tests/             68 deterministic tests
reports/           SMOKE_TEST.md, PHASE0_CLOSEOUT.md, prereg/, frozen reference_smoke.json
paper/             macro-driven LaTeX working paper (make paper → sarc-dq.pdf)
docs/              architecture, predicates, benchmark, relationship-to-{sarc,greensarc}
.github/workflows/ ci, phase0-live, exp-*, paper
```

## Reproducibility

Every run is seeded, logs its `config_hash`, and writes a dual-channel
(cost + evidence) JSONL log. `make verify` re-runs the mock pipeline and checks
ADR / AUC / flag-rate against the frozen `reports/reference_smoke.json`. Nothing
is ever tuned on evaluation seeds; the mock reference is frozen before it is
checked. All report numbers come from logged results — none is hand-entered.

## Three human items

Everything buildable without live compute or human judgment is automated. Three
items genuinely need a human:

1. **Taxonomy v0 revision** — answer the ten questions in
   [`reports/TAXONOMY_REVISION_GUIDE.md`](reports/TAXONOMY_REVISION_GUIDE.md);
   each answer maps to injector parameters. The taxonomy is *scaffolding*, not the
   contribution.
2. **Fire the experiment workflows** — the Phase 4 kits (`.github/workflows/exp-*.yml`)
   are secret-gated and print spend; each writes a `results/<exp>-live` branch that
   feeds the paper macros.
3. **Claims sign-off** — review the compiled paper and lift the DRAFT watermark
   once the results land and the claims are owned.

## The paper

The working paper lives in [`paper/`](paper/) and compiles today:

```bash
make paper            # regenerate result macros + compile → paper/sarc-dq.pdf
```

**No result value is hand-authored.** `paper/scripts/make_macros.py` reads every
`paper/data/**/reference_summary.json` and emits `generated/results.tex`; a value
that does not exist yet renders `\pending{<id>}` → "**—** `[pending: id]`". The
Phase 0 pilot numbers are real (vendored from the `results/*-live` branches);
H1–H4 stay pending until the experiment workflows are fired. Every page carries a
**DRAFT** watermark until claims sign-off, and citations marked `⟨VERIFY⟩` are
unverified. CI builds the PDF on every `paper/**` change
([`.github/workflows/paper.yml`](.github/workflows/paper.yml)).

## License

MIT — see [LICENSE](LICENSE).
