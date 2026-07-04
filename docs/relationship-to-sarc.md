# Relationship to sarc-governance

[`sarc-governance`](https://github.com/besanson/sarc-governance) is the SARC
architecture's runtime spine: declarative constraint specs (hard / soft /
escalation) enforced at in-process points around every tool call, with trace
stores and a tamper-evident hash chain. SARC-DQ is the **evidence-quality**
application of that architecture.

What SARC-DQ reuses (from Phase 1 on):

- **Spec + predicate machinery** — the DQ predicate schema is authored in the same
  YAML style (`id`, `class`, `verif`, `response`, `predicate`) and resolved
  through a named predicate registry (no `eval`), exactly as
  `sarc_governance.specs` / `sarc_governance.predicates` do.
- **Four enforcement sites** — SARC-DQ places DQ predicates on the Pre-Action
  Gate, Action-Time Monitor, Post-Action Auditor, and Escalation Router. This
  repo asserts nothing about SARC beyond that documented four-site architecture.
- **Trace stores + hash chain** — the versioned-evidence-set semantics (every
  admitted action attributable to the exact records + metadata it relied on) build
  on the sarc-governance trace/hash-chain primitives. Phase 0 already ships the
  content-addressed `evidence_id` primitive in `sarc_dq.records`.

The delta: sarc-governance governs the **action** side (what the agent is about to
do). SARC-DQ governs the **input** side (whether the evidence the action rests on
is trustworthy) — the gap that action-side guardrails leave open.
