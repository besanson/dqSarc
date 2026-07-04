# DQ predicates (Phase 1 — behind the next gate)

> **Not implemented yet.** The predicate family and its YAML schema are a Phase 1
> deliverable, gated behind the Phase 0 hard stop. This page records the intended
> design so the direction is legible; the taxonomy below is **v0 scaffolding**
> that the human revises at Gate 1 — it is explicitly *not* the contribution.

## Predicate schema (sarc-governance YAML style)

Authored exactly like a `sarc-governance` constraint spec (`id`, `class`,
`verif`, `response`, `predicate`, `description`), with DQ-specific predicates:

| predicate | checks | typical channel |
|---|---|---|
| `freshness(max_age)` | `retrieved_day - as_of_day ≤ max_age` | metadata-borne |
| `lineage_present` | a non-empty provenance chain exists | metadata-borne |
| `golden_record_unique` | no superseded version readable alongside the current one | metadata-borne |
| `cross_source_consistent(tolerance)` | independent sources agree within tolerance | payload-visible |
| `schema_conformant` | field names/types match the registered schema | payload-visible |
| `complete(required_fields)` | all mandatory fields present | payload-visible |

Each predicate carries a **class** (hard / soft / escalation), a **verification
point** (Pre-Action Gate / Action-Time Monitor / Post-Action Auditor), a
**response protocol** (block / degrade-autonomy / escalate /
quarantine-and-substitute), and an **operating point**.

## Corruption taxonomy v0 (scaffolding — revised at Gate 1)

1. Stale master data *(metadata-borne)* — **implemented in Phase 0**
2. Superseded golden record *(metadata-borne)*
3. Silent unit change, e.g. kg-for-lb *(metadata-borne unless units are printed)*
4. Duplicate vendor records with conflicting terms *(payload-visible)*
5. Cross-source contradiction *(payload-visible)*
6. Schema drift — renamed/retyped field *(payload-visible)*
7. Missing mandatory field *(payload-visible)*
8. Plausible outlier — wrong but in-range *(borderline; metadata-borne if only
   lineage reveals it)*

The Phase 0 injector framework (`sarc_dq.injectors`) already models the
channel-tagged, ground-truth-logging contract these classes will implement.
