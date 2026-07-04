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
> **What it *is* right now:** the repository scaffold + the **Phase 0 smoke test**
> — the first hard-stop gate, which asks a single question: *does the
> silent-failure effect exist at all?* The harness runs end-to-end, is typed
> (`mypy --strict`), tested, and green under CI, and produces a watermarked
> `reports/SMOKE_TEST.md`.
>
> **What it *is not* yet:** the DQ predicate family, the Pre-Action Gate, the full
> corruption taxonomy, GIGO-Bench, and the H1–H4 experiments all live *behind*
> later gates and are **not built yet**. No claim in this repo about real Claude
> behaviour has been measured — the only numbers produced so far come from an
> **offline mock agent** and are labelled, loudly, as a pipeline dry-run.

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

## Phase 0 pipeline status (mock arm — **not a scientific result**)

These numbers come from the deterministic, offline **mock** agent + judge. They
exist only to prove the metrics and kill-criterion wiring are correct, and must
not be cited. The real H1 answer comes from the live arm.

| metric (mock dry-run) | value |
|---|---|
| Action Defect Rate | 43.0% |
| Behavioral marker AUC | 0.500 |
| LLM-judge doubt AUC | 0.500 |
| Kill-criterion verdict | SUPPORTED (pipeline shape only) |
| API spend | $0.0000 |

A metadata-blind agent leaves *no lexical trace of doubt* (AUC = chance) while its
actions are *materially wrong* (high ADR) — the expected signature of a silent
failure, and exactly what the live run will test on real models.

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
  injectors/       corruption framework + Phase 0 stale-price class (channel-tagged)
  agent/           payload-only decision interface; mock + live Claude agents
  judge/           LLM-judge doubt scoring; mock + live; 20 hand-checkable cases
  markers.py       lexical uncertainty / data-flag markers
  metrics.py       loss, ADR, discrimination AUC, paired-seed bootstrap CIs
  phase0.py        the Phase 0 protocol (dual-channel logging)
  report.py        renders reports/SMOKE_TEST.md from logged results only
benchmarks/phase0_smoke.py   runnable entrypoint + --verify
tests/             28 deterministic tests
reports/           SMOKE_TEST.md, GATE0_BRIEF.md, frozen reference_smoke.json
docs/              architecture, predicates, relationship-to-{sarc,greensarc}
```

## Reproducibility

Every run is seeded, logs its `config_hash`, and writes a dual-channel
(cost + evidence) JSONL log. `make verify` re-runs the mock pipeline and checks
ADR / AUC / flag-rate against the frozen `reports/reference_smoke.json`. Nothing
is ever tuned on evaluation seeds; the mock reference is frozen before it is
checked. All report numbers come from logged results — none is hand-entered.

## License

MIT — see [LICENSE](LICENSE).
