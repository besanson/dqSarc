# Taxonomy Revision Guide — ten questions (~2 hours)

Answer these from enterprise experience (master data + procure-to-pay). Each
answer maps directly to an injector parameter or a new class; the "→ changes"
line says exactly what to edit. The goal is to replace v0 scaffolding with ground
truth. Nothing here requires code — edit `src/sarc_dq/taxonomy/classes.py`
defaults and `src/sarc_dq/specs/dq_predicates.yaml` params.

1. **Which of the eight classes actually occur in your master data and P2P, and
   which don't?** Which are missing entirely?
   → changes: drop/add classes in `TAXONOMY_V0`; set `default_rate=0` for absent ones.

2. **Realistic base rates.** For each class that occurs, what fraction of
   records/decisions does it affect in a representative window?
   → changes: each class's `default_rate`; the GIGO-Bench rate grid {2,5,10,20%}.

3. **Staleness age distribution.** When master data is stale, how old is it —
   days, weeks, months? Is it uniform, or a spike at a refresh cadence?
   → changes: `StaleMasterData.min_age_days`/`max_age_days` and the drift model;
     the `freshness.max_age_days` operating point in the YAML.

4. **How do duplicate vendors really differ?** Same legal entity re-keyed, or
   genuinely different vendors for the same item? Which terms conflict (price,
   currency, lead time, incoterms)? Same key or different keys?
   → changes: `DuplicateVendorConflictingTerms` companion fields + record-id policy;
     whether a new `duplicate_key_resolution` predicate is needed (v0 gap).

5. **Concrete unit-change examples.** Which unit swaps happen (kg/lb, ea/case,
   m/ft, per-unit/per-1000)? Is the unit ever printed in the payload?
   → changes: `SilentUnitChange` factor set; if units are printed, re-tag the class
     `payload-visible`; add an `expected_unit` reference predicate (closes a v0 gap).

6. **How does golden-record supersession happen?** Is the old version deleted,
   soft-deleted, or left readable? How long do both coexist? Version scheme?
   → changes: `SupersededGoldenRecord` version/as-of gap and whether a companion
     current-golden is actually available for substitution.

7. **Which contradictions cross which systems?** ERP vs DWH vs vendor portal vs
   contract — which pairs disagree, and by how much (typical spread)?
   → changes: `CrossSourceContradiction` source labels and spread; the
     `cross_source_consistent.tolerance` operating point.

8. **What does schema drift look like across upgrades/integrations?** Field
   renames, retypes (number→string), nesting changes, unit-column splits?
   → changes: `SchemaDrift` mutation set; the `schema_conformant.fields` type map.

9. **Plausible-outlier mechanics.** How does a wrong-but-in-range value arise —
   mis-join to another SKU, fat-finger, currency mix-up, decimal shift? What
   reference (history, contract, band) would reveal it?
   → changes: `PlausibleOutlier` generation; add a `reference_bound` predicate
     (closes a v0 gap) with the reference source you name.

10. **What is the taxonomy missing?** Classes not listed here that bite in
    practice — e.g. FX/rounding drift, effective-dating errors, mapping-table rot,
    partial loads, encoding corruption, PII redaction artifacts.
    → changes: new classes in `classes.py` (+ channel tag) and, where detectable,
      new predicates + YAML constraints.

**After answering:** update the two files above, run `pytest -q` (the mock
detection tests must stay green), and lift the REVISION-REQUESTED banner in
`TAXONOMY_V0.md`. The injector calibration to Tier-2 empirical rates
(`benchmarks/gigo/CALIBRATION.md`) consumes answers 2–3 and 7.
