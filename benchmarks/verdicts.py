"""Committed verdict code — evaluates a run summary against frozen PREREG predictions.

Verdicts are mechanical: the thresholds come from ``reports/prereg/<exp>.md`` (and the
dated addendum), never from prose. A failed prediction is reported as FAILED with its
pre-registered interpretation, not reinterpreted. Usage:

    python -m benchmarks.verdicts --exp h2-detection --summary <path-or-branch>

``--summary`` accepts a local JSON path or ``results/<exp>-live`` (read via git).
"""

from __future__ import annotations

import argparse
import json
import subprocess
from typing import Any

from sarc_dq.taxonomy import get, registered


def _load(src: str) -> dict[str, Any]:
    if src.startswith("results/"):
        ref = f"origin/{src}:reports/exp/{src.split('/')[1].replace('-live', '')}_summary.json"
        text = subprocess.check_output(["git", "show", ref], text=True)
    else:
        with open(src, encoding="utf-8") as fh:
            text = fh.read()
    data: dict[str, Any] = json.loads(text)
    return data


def pooled_detection(summary: dict[str, Any]) -> dict[str, dict[str, float]]:
    """Per-class, per-arm detection rate pooled over the rate/label cells (weighted by n)."""
    out: dict[str, dict[str, float]] = {}
    for cls, rates in summary["matrix"].items():
        acc: dict[str, list[float]] = {}
        for cell in rates.values():
            for arm, m in cell.items():
                n = int(m.get("n_corrupted", 0))
                det = float(m.get("detection_rate", 0.0))
                a = acc.setdefault(arm, [0.0, 0.0])
                a[0] += det * n
                a[1] += n
        out[cls] = {arm: (num / den if den else 0.0) for arm, (num, den) in acc.items()}
    return out


def h2_verdict(summary: dict[str, Any]) -> dict[str, Any]:
    """H2 (detection asymmetry). P1: payload-visible |C-D| <= 0.15. P2: metadata-borne
    C <= 0.10 AND D >= 0.80. H2 supported iff every class passes its channel's test."""
    det = pooled_detection(summary)
    rows = []
    p1_ok = p2_ok = True
    for cls in registered():
        ch = getattr(get(cls), "channel", "?")
        c = round(det.get(cls, {}).get("C", 0.0), 3)
        d = round(det.get(cls, {}).get("D", 0.0), 3)
        if ch == "payload-visible":
            ok = abs(c - d) <= 0.15
            p1_ok = p1_ok and ok
            rule = f"P1 |C-D|={abs(c - d):.2f}<=0.15"
        else:
            ok = c <= 0.10 and d >= 0.80
            p2_ok = p2_ok and ok
            rule = f"P2 C={c:.2f}<=0.10 & D={d:.2f}>=0.80"
        rows.append({"class": cls, "channel": ch, "C": c, "D": d, "pass": ok, "rule": rule})
    return {
        "hypothesis": "H2",
        "supported": p1_ok and p2_ok,
        "P1_payload_visible": p1_ok,
        "P2_metadata_borne": p2_ok,
        "rows": rows,
    }


VERDICTS = {"h2-detection": h2_verdict}


def render(v: dict[str, Any]) -> str:
    lines = [
        f"VERDICT {v['hypothesis']}: {'SUPPORTED' if v['supported'] else 'NOT SUPPORTED'}"
        f"  (P1={'pass' if v['P1_payload_visible'] else 'FAIL'},"
        f" P2={'pass' if v['P2_metadata_borne'] else 'FAIL'})",
        f"  {'class':30s} {'chan':16s} {'C':>5s} {'D':>5s}  result",
    ]
    for r in v["rows"]:
        lines.append(
            f"  {r['class']:30s} {r['channel']:16s} {r['C']:5.2f} {r['D']:5.2f}"
            f"  {'pass' if r['pass'] else 'FAIL'}  [{r['rule']}]"
        )
    return "\n".join(lines)


def main(argv: Any = None) -> int:
    p = argparse.ArgumentParser(prog="benchmarks.verdicts", description=__doc__)
    p.add_argument("--exp", required=True, choices=sorted(VERDICTS))
    p.add_argument("--summary", required=True, help="JSON path or results/<exp>-live")
    args = p.parse_args(argv)
    verdict = VERDICTS[args.exp](_load(args.summary))
    print(render(verdict))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
