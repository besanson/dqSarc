# Corruption Taxonomy v0

> ## ⚠️ REVISION REQUESTED
> This taxonomy is **v0 scaffolding**, not the intellectual contribution. It exists
> so the harness and predicates have something to bite on. The classes, rates, and
> mechanics below are placeholders to be **replaced with enterprise ground truth**
> via [`TAXONOMY_REVISION_GUIDE.md`](TAXONOMY_REVISION_GUIDE.md) (≈2 hours). Do not
> treat any base rate or mechanism here as validated.

The framework (`sarc_dq.taxonomy`) is the generalized successor to the frozen
Phase 0 injector: every class declares a detection **channel** (load-bearing for
H2), an injection **site**, a **default_rate**, and produces an `InjectionResult`
(primary record + companion records + a ground-truth tag written to the log,
never shown to any agent/critic/judge/gate).

| # | class | channel | site | default rate | v0 predicate coverage |
|---|---|---|---|---|---|
| 1 | `stale_master_data` | metadata-borne | unit_price | 0.10 | `freshness` ✓ |
| 2 | `superseded_golden_record` | metadata-borne | unit_price | 0.05 | `golden_record_unique` ✓ |
| 3 | `silent_unit_change` | metadata-borne | unit_price | 0.05 | **none (v0 gap)** — needs an expected-unit reference |
| 4 | `duplicate_vendor_conflicting_terms` | payload-visible | vendor_terms | 0.05 | **none (v0 gap)** — dup rows have distinct keys |
| 5 | `cross_source_contradiction` | payload-visible | unit_price | 0.05 | `cross_source_consistent` ✓ |
| 6 | `schema_drift` | payload-visible | unit_price | 0.05 | `schema_conformant` ✓ (+ `complete`) |
| 7 | `missing_mandatory_field` | payload-visible | unit_price | 0.05 | `complete` ✓ (+ `schema_conformant`) |
| 8 | `plausible_outlier` | metadata-borne | unit_price | 0.05 | **none (v0 gap)** — needs a reference value |

**Three v0 gaps are intentional and instructive:** silent-unit-change,
duplicate-vendor, and plausible-outlier have no clean v0 predicate. They mark
where the taxonomy revision must either add a predicate (an expected-unit table, a
duplicate-key resolver, a reference-value bound) or refine the class. The gaps are
surfaced, not hidden.

## DQ predicate schema

Authored in sarc-governance YAML style at
[`src/sarc_dq/specs/dq_predicates.yaml`](../src/sarc_dq/specs/dq_predicates.yaml),
parameterized so a revision edits YAML, not Python:

| predicate | params | class | verif | response |
|---|---|---|---|---|
| `freshness` | `max_age_days` | hard | PAG | quarantine_substitute |
| `golden_record_unique` | — | hard | PAG | quarantine_substitute |
| `cross_source_consistent` | `tolerance`, `field` | escalation | PAG | escalate |
| `schema_conformant` | `fields` | hard | PAG | block |
| `complete` | `required_fields` | hard | PAG | block |
| `lineage_present` | — | soft | PAA | escalate |

Verification points: **PAG** Pre-Action Gate · **AATM** Action-Time Monitor ·
**PAA** Post-Action Auditor. Response protocols: **block** · **degrade** (autonomy)
· **escalate** · **quarantine_substitute** (from the governed buffer; never writes
to source).
