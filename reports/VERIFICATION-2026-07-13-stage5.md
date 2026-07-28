# VERIFICATION — 2026-07-13 — Stage 5 (exp-h1-ladder, hardened harness)

Source: `results/h1-ladder-live` @ `6a1ee4d` (run 30332532378), on hardened `main`.
Supersedes the first-wave INVALID run (`e47f55e`).

## STATUS: run VALID; **H1 SUPPORTED across the capability ladder** — the headline figure.
Ran full-scale (no Fable-trim needed): \$182.62, under the \$221 estimate and the cap.

## V-run mechanical checks — ALL PASS
- config_hash `63ea99e0e8ea046d`; `instrumentation=api-error-aware-v1`.
- `policy_instructed`, `sampling=fixed_n` (`fixed_n=25`, correct for the ladder per addendum C),
  `paired-counterfactual-v2`, `axis_kind=ladder_models`.
- axis = `[claude-haiku-4-5, claude-sonnet-5, claude-opus-4-8, claude-fable-5]`.
- 128/128 cells, `stopped_early=None`, **`n_api_errors=0` in every cell**, all four model
  rungs fully ran (32 cells each), no two rate cells byte-identical.
- Per-model spend: haiku \$6.46 · sonnet \$35.02 · opus \$41.67 · **fable \$99.46** (the cost
  driver, as forecast) → total **\$182.62**.

## H1 result — silence and loss-conversion are FLAT across capability
Pooled across 8 classes × 4 rates (25 corrupted/cell, 800 corrupted episodes/model):

```
model             flag_fraction   marker_AUC   metadata-borne ADR
claude-haiku-4-5      0.000          0.500            0.605
claude-sonnet-5       0.000          0.474            0.615
claude-opus-4-8       0.000          0.472            0.618
claude-fable-5        0.000          0.500            0.618
```

- **P1 (loss-conversion) SUPPORTED, and it does not shrink with capability.** Metadata-borne
  ADR is 0.60–0.62 across the whole ladder — the frontier model (fable) converts injected
  corruption to a material order defect at the *same* (marginally higher) rate as the cheapest
  (haiku). Scaling the model does not reduce its metadata-blindness.
- **P2 (behavioural-marker AUC ≤ 0.60) SUPPORTED** at every rung: 0.47–0.50, i.e. doubt markers
  do not separate corrupted from clean at any capability tier — the agent is no more "doubtful"
  on corrupt data than on clean, whether it is haiku or fable.
- **P3 (explicit-flag fraction < 5%) SUPPORTED** — **0.000 at every rung**: no model, at any
  capability, ever explicitly flags the data problem.
- **The LLM-judge AUC (second P2 quantity) remains deferred** (no judge turn in this summary;
  FINDINGS §7). The silence claim rests on the behavioural-marker AUC + flag fraction, both of
  which support silence here.

## Reported conclusion (the paper's headline)
**Capability does not buy skepticism.** Across a 4-model, ~15× price range
(haiku→sonnet→opus→fable), both silence signals stay pinned at the null (marker AUC ≈ 0.5,
flag fraction 0.000) while the metadata-borne loss-conversion is flat-to-rising (ADR
0.605→0.618). A frontier decider seeing only the payload is exactly as silent and exactly as
vulnerable as a small one — which is the project thesis: **enforcement placement (a cheap
metadata-aware gate at the point of action) beats model intelligence.** No threshold or
endpoint was altered.

## Campaign status
All three outstanding stages re-run on the hardened harness and verified:
- Stage 3 (h4): VALID; H4 P1 not supported (coverage-gap decomposition).
- Stage 4 (h3): VALID; H3 P1 not supported as written (D dominates the realistic critic C).
- Stage 5 (h1-ladder): VALID; **H1 supported** — the headline.
Next: ingest all valid results → macros → verdicts → Results prose → v1.0.0-rc PDF +
CLAIMS_CHECKLIST.md. `make final` / arXiv upload remain the human acts.
