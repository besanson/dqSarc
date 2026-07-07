# GIGO-Bench — Injector Calibration to Tier-2 data (stub)

> **Stub — pending Tier-2 validation runs (Part 4 `tier2-validation`).** This file
> will map the injector's default rates and patterns to *empirically observed*
> error rates from labeled real-error datasets, so GIGO's synthetic corruption is
> anchored to reality rather than guessed.

## Tier-2 sources (labeled real errors)

| dataset | defect type it grounds | taxonomy class |
|---|---|---|
| Raha/Baran suite (Hospital, Flights, Beers, Rayyan, Movies, Tax) | mixed cell-level errors, missing values | `missing_mandatory_field`, `schema_drift`, `plausible_outlier` |
| Flights / Stock multi-source-conflict | source disagreement | `cross_source_contradiction` |
| Magellan / DeepMatcher entity-matching pairs | real duplicates | `duplicate_vendor_conflicting_terms` |
| ALFRED archival data vintages | real staleness (value-as-known-at-T vs revised) | `stale_master_data`, `superseded_golden_record` |

## Mapping to inject

Once the `tier2-validation` experiment lands (`results/tier2-validation-live`):

1. **Base rates** — set each class's `default_rate` (in `sarc_dq/taxonomy/classes.py`)
   to the observed error rate in the corresponding Tier-2 dataset.
2. **Staleness age distribution** — fit `StaleMasterData.min/max_age_days` and the
   drift model to ALFRED vintage gaps.
3. **Cross-source spread** — fit `CrossSourceContradiction` spread + tolerance to
   the Flights/Stock disagreement distribution.
4. **Duplicate similarity** — fit `DuplicateVendorConflictingTerms` to Magellan
   duplicate-pair term differences.

Each mapping is a one-line edit; the values are filled from the committed Tier-2
summary, never hand-guessed (no-fabrication rule). See also
`reports/TAXONOMY_REVISION_GUIDE.md` questions 2, 3, 7.
