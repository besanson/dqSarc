"""Ingest committed experiment result branches into ``paper/data/<exp>/``.

No-fabrication rule: every number the paper prints must trace to a committed
``results/<exp>-live`` summary. This script reads those summaries straight from git
(``git show origin/results/<exp>-live:reports/exp/<exp>_summary.json``), recomputes the
headline + supporting metrics, and writes ``paper/data/<exp>/reference_summary.json`` with
full provenance (branch, SHA, run id, config_hash, instrumentation, spend). ``make_macros``
then turns those into LaTeX macros. Re-runnable and deterministic; overwrites in place.

Only VALID runs on the hardened harness are ingested (see reports/VERIFICATION-*.md and
FINDINGS §8-§11). The invalid first-wave / cap-truncated runs are deliberately not ingested.
"""

from __future__ import annotations

import json
import statistics
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "paper" / "data"

# Each experiment: results branch + the run id recorded in the branch's commit subject.
BRANCHES = {
    "h1-full": ("results/h1-full-live", "29095598109"),
    "h2-detection": ("results/h2-detection-live", "29101951327"),
    "h3-frontier": ("results/h3-frontier-live", "30296664147"),
    "h4-recovery": ("results/h4-recovery-live", "30282599910"),
    "h1-ladder": ("results/h1-ladder-live", "30332532378"),
}

# Metadata-borne defect classes (the DQ channel the payload-only critic is blind to).
META = {
    "silent_unit_change",
    "stale_master_data",
    "superseded_golden_record",
    "plausible_outlier",
}
# Payload-visible defect classes (a content critic can in principle see these).
PAYLOAD_VISIBLE = {
    "cross_source_contradiction",
    "duplicate_vendor_conflicting_terms",
    "missing_mandatory_field",
    "schema_drift",
}


def _git_show(branch: str, path: str) -> dict[str, Any]:
    out = subprocess.run(
        ["git", "show", f"origin/{branch}:{path}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout)


def _sha(branch: str) -> str:
    out = subprocess.run(
        ["git", "rev-parse", "--short", f"origin/{branch}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def _prov(summ: dict[str, Any], branch: str, run_id: str) -> dict[str, Any]:
    c = summ["config"]
    return {
        "branch": branch,
        "sha": _sha(branch),
        "run_id": run_id,
        "config_hash": c.get("config_hash"),
        "instrumentation": c.get("instrumentation"),
        "prompt_variant": c.get("prompt_variant"),
        "sampling": c.get("sampling"),
        "spend_usd": round(float(summ.get("total_usd", 0.0)), 2),
        "cells": f"{summ.get('cells_done')}/{summ.get('cells_total')}",
    }


def _adr_pooled(matrix: dict[str, Any], arm: str, classes: set[str] | None = None) -> float:
    tot = n = 0.0
    for cls, rates in matrix.items():
        if classes is not None and cls not in classes:
            continue
        for cell in rates.values():
            a = cell.get(arm)
            if not a:
                continue
            nc = a.get("n_corrupted", 0)
            tot += a.get("adr", 0.0) * nc
            n += nc
    return round(tot / n, 4) if n else 0.0


def _paired_pool(matrix: dict[str, Any], arm: str) -> list[float]:
    out: list[float] = []
    for rates in matrix.values():
        for cell in rates.values():
            a = cell.get(arm)
            if a:
                out += a.get("paired_losses", [])
    return out


def _mean(xs: list[float]) -> float:
    return round(statistics.mean(xs), 2) if xs else 0.0


def ingest_h1_full(m: dict[str, Any]) -> dict[str, Any]:
    meta = _adr_pooled(m, "A", META)
    return {"headline": meta, "metadata_borne_adr": meta, "verdict": "SUPPORTED (P1)"}


def ingest_h1_ladder(m: dict[str, Any], models: list[str]) -> dict[str, Any]:
    rungs = {}
    for mod in models:
        meta = _adr_pooled(m, mod, META)
        # flag fraction + marker AUC pooled across cells for this model rung
        flags = ncorr = 0.0
        aucs: list[float] = []
        for rates in m.values():
            for cell in rates.values():
                a = cell.get(mod)
                if not a:
                    continue
                nc = a.get("n_corrupted", 0)
                flags += a.get("flag_fraction", 0.0) * nc
                ncorr += nc
                if a.get("marker_auc") is not None:
                    aucs.append(a["marker_auc"])
        rungs[mod] = {
            "metadata_borne_adr": meta,
            "flag_fraction": round(flags / ncorr, 4) if ncorr else 0.0,
            "marker_auc": round(statistics.mean(aucs), 3) if aucs else None,
        }
    adrs = [rungs[mod]["metadata_borne_adr"] for mod in models]
    return {
        "headline": rungs[models[-1]]["metadata_borne_adr"],  # frontier (fable) meta ADR
        "rungs": rungs,
        "adr_min": min(adrs),
        "adr_max": max(adrs),
        "flag_fraction_max": round(max(rungs[mod]["flag_fraction"] for mod in models), 4),
        "marker_auc_max": round(
            max(rungs[mod]["marker_auc"] for mod in models if rungs[mod]["marker_auc"] is not None),
            3,
        ),
        "verdict": "SUPPORTED — silence + loss-conversion flat across capability",
    }


def ingest_h2(m: dict[str, Any]) -> dict[str, Any]:
    # Detection asymmetry: payload critic C vs gate D, pooled detection on metadata classes.
    def det(arm: str, classes: set[str]) -> float:
        tot = n = 0.0
        for cls, rates in m.items():
            if cls not in classes:
                continue
            for cell in rates.values():
                a = cell.get(arm)
                if not a:
                    continue
                nc = a.get("n_corrupted", 0)
                tot += a.get("detection_rate", 0.0) * nc
                n += nc
        return round(tot / n, 4) if n else 0.0

    c_meta, d_meta = det("C", META), det("D", META)
    return {
        "headline": round(d_meta - c_meta, 4),
        "critic_detection_metadata": c_meta,
        "gate_detection_metadata": d_meta,
        "verdict": "REFRAMED — gate dominates on the metadata channel (channel boundary)",
    }


def ingest_h3(m: dict[str, Any]) -> dict[str, Any]:
    def pool(arm: str, key: str) -> float:
        vals: list[float] = []
        wts: list[float] = []
        for rates in m.values():
            for cell in rates.values():
                a = cell.get(arm)
                if not a:
                    continue
                if key == "resid":
                    vals += a.get("paired_losses", [])
                else:
                    vals.append(a.get(key, 0.0))
                    wts.append(1)
        return round(statistics.mean(vals), 3) if vals else 0.0

    return {
        "headline": pool("D", "detection_rate"),
        "gate_residual_loss": _mean(_paired_pool(m, "D")),
        "critic_residual_loss": _mean(_paired_pool(m, "C")),
        "gate_detection": pool("D", "detection_rate"),
        "critic_detection": pool("C", "detection_rate"),
        "gate_false_block": pool("D", "false_block_rate"),
        "verdict": "P1 NOT supported as written; gate dominates the realistic critic C",
    }


def ingest_h4(m: dict[str, Any]) -> dict[str, Any]:
    la, ld, le = _paired_pool(m, "A"), _paired_pool(m, "D"), _paired_pool(m, "E")
    mA, mD, mE = _mean(la), _mean(ld), _mean(le)
    rec = round((mA - mD) / (mA - mE), 3) if abs(mA - mE) > 1e-9 else None
    # freshness (stale) per-class recovery — the covered family
    st = m.get("stale_master_data", {})
    sa = _mean([x for cell in st.values() for x in cell.get("A", {}).get("paired_losses", [])])
    sd = _mean([x for cell in st.values() for x in cell.get("D", {}).get("paired_losses", [])])
    return {
        "headline": rec,
        "portfolio_recovery": rec,
        "portfolio_loss_a": mA,
        "portfolio_loss_d": mD,
        "stale_loss_a": sa,
        "stale_loss_d": sd,
        "verdict": "P1 (recovery>=0.80) NOT supported; gate recovers covered channel (freshness)",
    }


def main() -> int:
    for exp, (branch, run_id) in BRANCHES.items():
        summ = _git_show(branch, f"reports/exp/{exp}_summary.json")
        m = summ["matrix"]
        if exp == "h1-full":
            metrics = ingest_h1_full(m)
        elif exp == "h1-ladder":
            metrics = ingest_h1_ladder(m, list(summ["config"]["axis"]))
        elif exp == "h2-detection":
            metrics = ingest_h2(m)
        elif exp == "h3-frontier":
            metrics = ingest_h3(m)
        elif exp == "h4-recovery":
            metrics = ingest_h4(m)
        else:
            continue
        doc = {"experiment": exp, "provenance": _prov(summ, branch, run_id), **metrics}
        out = DATA / exp / "reference_summary.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        print(f"ingested {exp:14s} headline={metrics.get('headline')}  -> {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
