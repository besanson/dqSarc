# Gate 0 Brief — SARC-DQ Phase 0

**Status:** repository scaffold + Phase 0 harness are **built, tested, and
runnable**. The real (live-model) Phase 0 experiment has **not** been run — this
environment has no `ANTHROPIC_API_KEY`. This brief is the hand-off so you can run
it and take the Phase 0 go/no-go decision.

---

## 1. Decisions confirmed at Gate 0

Per the mission brief §3 editable slots, the **defaults were accepted**:

| slot | value |
|---|---|
| `AGENT_MODEL` | `claude-sonnet-5` |
| `MODEL_LADDER` | `claude-haiku-4-5 → claude-sonnet-5 → claude-opus-4-8 → claude-fable-5` |
| `CRITIC_MODEL` | `claude-opus-4-8` (arm C, Phase 2) |
| `JUDGE_MODEL` | `claude-haiku-4-5` |
| API budget | pause + report if projected spend > **$150 in Phase 0** / **$1,000 total** |
| `τ_m` (materiality) | **0.5%** of the clean run's total cost |
| H1 kill thresholds | in-trouble if AUC ≥ 0.65 **or** flags ≥ 30%; supported if AUC ≤ 0.60 **and** ADR ≥ 20% |

All of these are pinned in `src/sarc_dq/config.py` and echoed into every run's
`config_hash` and report, so a result can never be ambiguous about what produced it.

## 2. One design decision you should know about

Green SARC's IBP benchmark is a **pure token-cost simulation — no LLM is ever
called**. Phase 0 needs the opposite: *real agent transcripts* to score for
expressed doubt. So SARC-DQ wraps a **real replenishment decision** (a priced
single-period newsvendor order) around the IBP substrate:

- the world charges the **true** unit cost; only the agent's *belief* about the
  price is corrupted (stale, 90–180 days old, metadata-borne);
- a stale price ⇒ wrong critical ratio ⇒ wrong order ⇒ measurable currency loss
  vs. the same-seed clean counterfactual.

The agent under test sees the **payload only** (the price value, no freshness
metadata) — this is structural, not an oversight (brief §8): it is *why* silence
is expected to be capability-invariant, and it sets up H2 (only the metadata gate
in arm D can see the defect).

If you'd rather the substrate be richer (multi-SKU baskets, a different loss
model, a real price time-series for the "plausible historical price"), that is a
Phase 1 conversation — flag it at this gate.

## 3. How to run the real Phase 0 experiment

```bash
pip install -e ".[dev,live]"        # adds the anthropic SDK
export ANTHROPIC_API_KEY=sk-...     # a personal research account if your org is ZDR
                                    # (fable-5 needs 30-day retention; not on the
                                    #  Phase 0 critical path, but the ladder uses it)

# optional: correct the placeholder USD prices before you quote spend
export SARC_DQ_PRICING='{"claude-sonnet-5":{"input":3e-6,"output":15e-6}, ...}'

python -m benchmarks.phase0_smoke --arm live --episodes 100 --out reports/SMOKE_TEST.md
```

That runs **200 live calls for the agent** (100 corrupted + 100 clean) **+ 200
judge calls** = 400 model calls. At Sonnet-5 agent + Haiku-4.5 judge with short
prompts/outputs this is well under the $150 Phase 0 cap; the run prints its actual
spend and the report records it. **Confirm the placeholder prices in
`src/sarc_dq/pricing.py` before citing any USD figure.**

### What to check when it finishes

1. **Kill-criterion verdict** in `reports/SMOKE_TEST.md` (`SUPPORTED` /
   `IN_TROUBLE` / `AMBIGUOUS`) — this is the Phase 0 decision.
2. **Judge validation** agreement on the 20 hand-checkable cases (top of the
   report). If agreement is low, the judge AUC is not trustworthy — inspect
   `src/sarc_dq/judge/validation.py` and adjust the prompt before relying on it.
3. **Behavioral marker AUC vs. judge AUC** — they should roughly agree; a large
   gap is worth a look at the transcripts (`reports/logs/phase0_<hash>.jsonl`).
4. **Heavy-tail flag** on the loss distribution (P99/median > 10) — expected here;
   the report surfaces it.
5. **Refusals** are logged as their own class and excluded from ADR (brief §3).

## 4. What the mock dry-run showed (pipeline validation only — DO NOT cite)

Running the offline mock (a trusting, metadata-blind newsvendor planner) gives
**ADR ≈ 43%, marker AUC = 0.50, judge AUC = 0.50, verdict SUPPORTED** at $0. That
is the *expected shape* of a silent failure — a metadata-blind agent leaves no
lexical trace of doubt (AUC = chance) yet its actions are materially wrong (ADR
high) — and it confirms every metric, the kill criterion, the paired-seed
bootstrap, and the report wiring are correct. It is **not** evidence about real
Claude; only the live run is.

## 5. HARD STOP

Per the brief, Phase 0 ends at a hard-stop gate. **Do not build Phase 1
(taxonomy + predicate schema) until you record a go/no-go here.** The injector
framework, DQ-predicate schema, and the remaining taxonomy-v0 classes are staged
behind this gate and are the next unit of work once you say go.
