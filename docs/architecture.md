# Architecture

SARC-DQ applies the SARC governance-by-architecture pattern to **evidence
quality**. The full design targets the four SARC enforcement sites; **Phase 0
(this release) exercises only the measurement path** — the gate itself is Phase 2.

## The payload / metadata split (the load-bearing idea)

Every record an agent reads (`sarc_dq.records.EvidenceRecord`) has two channels:

- **payload** — the field values a naive agent sees (`unit_cost`, `vendor`, …).
- **metadata** — freshness / lineage / provenance (`as_of_day`, `source`,
  `version`, `retrieved_day`).

A corruption class declares a **channel**:

- `payload-visible` — detectable from content alone (duplicates, contradictions,
  schema drift, missing fields);
- `metadata-borne` — detectable *only* from freshness / lineage (stale master
  data, superseded golden record). **Phase 0's `stale_unit_price` is
  metadata-borne**: the stale value is a perfectly plausible price; only its age
  betrays it.

This tag is load-bearing for **H2 (detection asymmetry)**: a payload-only critic
(arm C) structurally cannot see a metadata-borne defect; a metadata-aware gate
(arm D) can.

## The measurement substrate

`sarc_dq.substrate` turns the Green SARC IBP domain (a token-cost *simulation*)
into a priced *decision*: a single-period newsvendor replenishment order whose
cost-minimising quantity depends on the **unit price**. The world always charges
the true price; only the agent's belief is corrupted. Loss is the currency gap
between the corrupted order and the same-seed clean counterfactual — a paired,
seeded measurement.

## Dual-channel logging (brief §6)

Each Phase 0 episode logs two channels, keyed to seed + `config_hash`:

- **cost** — USD + tokens (paper-grade; a later trajectory-cost paper reads it);
- **evidence** — the record read, its metadata, the ground-truth tag, the
  decision, and the versioned `evidence_id` (content-addressed over payload +
  metadata, excluding the hidden ground truth).

## What is not built yet

The DQ predicate family, the Pre-Action Gate, quarantine-and-substitute
remediation, the governed buffer, and the versioned-evidence-set *admission*
logic are Phase 1–2 deliverables behind later gates. `records.py` already carries
the evidence-set primitive (`evidence_id`) they will build on.
