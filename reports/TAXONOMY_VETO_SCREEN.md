# Taxonomy v1 — author veto screen (≤10 minutes)

One screen. Each row is a v0→v1 parameter with its provenance. **Silence = accept.**
To override any line, replace its value and add `{author_judgment: <you>, date: <ISO>}`
to the corresponding entry in `src/sarc_dq/specs/taxonomy_v1_calibrated.yaml`, then
re-run `python scripts/calibrate_taxonomy.py` (your override is preserved; the script
only regenerates provenance for lines you did not touch).

This replaces any interview: the calibration already did the structural and
literature work; you are exercising a veto, not answering questions.

| # | class · parameter | v0 | v1 | provenance | veto? |
|---|---|---|---|---|---|
| 1 | `stale_master_data` · `default_rate` | 0.1 | 0.1 (unchanged) | default+flagged | ☐ |
| 2 | `stale_master_data` · `min_age_days` | 90 | 90 (unchanged) | default+flagged | ☐ |
| 3 | `stale_master_data` · `max_age_days` | 180 | 180 (unchanged) | default+flagged | ☐ |
| 4 | `superseded_golden_record` · `default_rate` | 0.05 | 0.05 (unchanged) | default+flagged | ☐ |
| 5 | `silent_unit_change` · `default_rate` | 0.05 | 0.05 (unchanged) | default+flagged | ☐ |
| 6 | `duplicate_vendor_conflicting_terms` · `default_rate` | 0.05 | 0.05 (unchanged) | default+flagged | ☐ |
| 7 | `cross_source_contradiction` · `default_rate` | 0.05 | 0.05 (unchanged) | literature | ☐ |
| 8 | `cross_source_contradiction` · `tolerance` | 0.02 | 0.02 (unchanged) | default+flagged | ☐ |
| 9 | `schema_drift` · `default_rate` | 0.05 | 0.05 (unchanged) | literature | ☐ |
| 10 | `missing_mandatory_field` · `default_rate` | 0.05 | 0.05 (unchanged) | default+flagged | ☐ |
| 11 | `plausible_outlier` · `default_rate` | 0.05 | 0.05 (unchanged) | default+flagged | ☐ |

**Legend.** `computed` = measured from a named public dataset. `literature` = a cited
published aggregate. `default+flagged` = no public base rate exists; a scaffolding
default is declared and surfaced here and in the paper's Limitations. Rows marked
`default+flagged` whose provenance names a `pending_source_dataset` will become
`computed` once the `tier2-validation` run lands.

See also the ten open questions in `reports/TAXONOMY_REVISION_GUIDE.md`.
