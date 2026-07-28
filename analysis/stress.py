"""Item #7 --- metadata-degradation stress testing of the runtime gate.

The thesis is that placement (a metadata-aware gate at the point of action) is what
buys the recovery. That gate reads *metadata* signals --- freshness (age), version
supersession, provenance/source, cross-source agreement. So its detection is only as
good as the metadata it is handed. This module stresses exactly that dependency.

For every corrupted episode of a *gate-covered* class we rebuild the real injected
evidence set (``sarc_dq.taxonomy`` + ``sarc_dq.substrate``, seeded) and run the real
``PreActionGate``. We then re-run it under deterministic metadata-degradation operators:

  intact              : the metadata as injected (baseline detection)
  stale_clock         : retrieved_day := as_of_day  (age collapses to 0 -> freshness blind)
  version_erased      : every version := 1          (supersession invisible)
  provenance_stripped : source := ""                (lineage/consistency lose their anchor)
  all_degraded        : all of the above at once

Detection is the gate's own ``detected`` flag --- no ground truth, no reruns, no API.
The output characterises how gracefully (or not) each predicate degrades: a class whose
detection survives clock loss is robust; one that collapses is metadata-fragile. This is
a stress test of the *architecture's dependence on metadata quality*, not a new result.

Writes ``analysis/out/stress.json``.
"""

from __future__ import annotations

import json
import random
from typing import Any

from analysis.common import BASE_SEED, CLASS_PREDICATE, RATES, ROOT, corrupted_indices
from sarc_dq.gate import PreActionGate
from sarc_dq.records import EvidenceRecord, RecordMetadata
from sarc_dq.substrate import corruption_decision, episode_seed, make_episode
from sarc_dq.taxonomy import get

OUT = ROOT / "analysis" / "out" / "stress.json"

# Gate-covered classes only: an uncovered class (silent_unit_change, plausible_outlier)
# has no firing predicate, so metadata degradation cannot make it *worse* --- it is a
# floor, and including it would understate the covered classes' fragility.
COVERED = [c for c, p in CLASS_PREDICATE.items() if p is not None]


def _degrade(rec: EvidenceRecord, mode: str) -> EvidenceRecord:
    md: RecordMetadata = rec.metadata
    if mode == "intact":
        new = md
    elif mode == "stale_clock":
        new = RecordMetadata(md.source, md.retrieved_day, md.retrieved_day, md.version, md.lineage)
    elif mode == "version_erased":
        new = RecordMetadata(md.source, md.as_of_day, md.retrieved_day, 1, md.lineage)
    elif mode == "provenance_stripped":
        new = RecordMetadata("", md.as_of_day, md.retrieved_day, md.version, ())
    elif mode == "all_degraded":
        new = RecordMetadata("", md.retrieved_day, md.retrieved_day, 1, ())
    else:
        raise ValueError(f"unknown degradation mode {mode!r}")
    return EvidenceRecord(rec.record_id, dict(rec.payload), new, dict(rec.ground_truth))


MODES = ["intact", "stale_clock", "version_erased", "provenance_stripped", "all_degraded"]


def _detection_rate(cls_name: str, mode: str) -> tuple[int, int]:
    """(#detected, #corrupted) for a class across all rates, under a degradation mode."""
    cls = get(cls_name)
    gate = PreActionGate()
    detected = total = 0
    for rate in RATES:
        for i in corrupted_indices(rate, fixed_n=True):
            ep = make_episode(episode_seed(BASE_SEED, i), i)
            corr_seed, corrupt = corruption_decision(
                BASE_SEED, i, rate, n_episodes=100, fixed_n=25
            )
            if not corrupt:
                continue
            inj = cls.inject(ep.clean_price_record(), ep, random.Random(corr_seed + 1))
            evidence = tuple(_degrade(r, mode) for r in inj.evidence_set())
            total += 1
            if gate.evaluate(evidence).detected:
                detected += 1
    return detected, total


def build() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    per_mode_pooled: dict[str, list[tuple[int, int]]] = {m: [] for m in MODES}
    for cls in COVERED:
        row: dict[str, Any] = {"class": cls, "predicate": CLASS_PREDICATE[cls]}
        base_det, base_tot = _detection_rate(cls, "intact")
        for mode in MODES:
            det, tot = _detection_rate(cls, mode)
            row[mode] = round(det / tot, 4) if tot else 0.0
            per_mode_pooled[mode].append((det, tot))
        row["fragility"] = round(
            (base_det / base_tot if base_tot else 0.0) - row["all_degraded"], 4
        )
        rows.append(row)

    pooled = {
        m: round(sum(d for d, _ in v) / sum(t for _, t in v), 4) if v else 0.0
        for m, v in per_mode_pooled.items()
    }
    # Rank predicates by how much detection they lose when all metadata is degraded.
    most_fragile = max(rows, key=lambda r: float(r["fragility"])) if rows else None
    return {
        "note": "real PreActionGate detection on covered classes under metadata degradation",
        "modes": MODES,
        "rows": rows,
        "pooled_detection_by_mode": pooled,
        "most_fragile_class": most_fragile["class"] if most_fragile else None,
        "interpretation": (
            "detection is a function of metadata quality: collapsing the freshness clock or "
            "erasing versions removes the very signal the gate reads. Placement helps only to "
            "the extent the metadata channel is intact: an honest boundary, not a universal win."
        ),
    }


def main() -> int:
    res = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  pooled detection by mode={res['pooled_detection_by_mode']}")
    print(f"  most fragile={res['most_fragile_class']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
