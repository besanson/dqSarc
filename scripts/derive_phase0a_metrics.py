"""Derive Phase 0a's elasticity and clean-arm regret from the committed 0a JSONL.

Run 0a's committed summary (``paper/data/phase0/phase0.summary.json``) predates the
elasticity / clean-regret instrumentation, so those fields are ``null`` and the
paper renders them ``[pending]``. The per-episode data needed to compute them *is*
in the dual-channel JSONL committed to ``results/phase0-live`` — this script derives
them from that log and writes a derived summary whose provenance names the source
branch, file, and commit SHA. No value is hand-typed; the paper macro fills from the
derived file (else stays ``[pending]``).

Elasticity (per episode): how much the agent's order tracks the price it is given,
``ln(corrupt_qty/clean_qty) / ln(stale_price/true_price)`` — 0 means the agent
ignores the price (the incompetence shield); ~1 means it fully tracks it. Reported
as the median over episodes where the price actually moved.

Clean-arm regret (per episode): the agent's clean-counterfactual cost minus the
oracle's clean optimum, ``clean_cost - oracle_clean_cost`` — how far the agent is
from optimal even on clean data. Reported as mean and median.

Usage::

    python scripts/derive_phase0a_metrics.py                 # from results/phase0-live via git
    python scripts/derive_phase0a_metrics.py --jsonl PATH    # from a local JSONL
    python scripts/derive_phase0a_metrics.py --check         # verify derived file is current
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from datetime import date
from pathlib import Path
from statistics import mean, median
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "data" / "phase0" / "phase0a_derived.summary.json"
DEFAULT_REF = "results/phase0-live"
DEFAULT_PATH = "reports/logs/phase0_c8202a18b58754d8.jsonl"


def _read_ref(ref: str, path: str) -> tuple[str, str]:
    """Return (jsonl_text, commit_sha) for ``path`` on git ``ref``. Raises on failure."""
    text = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    sha = subprocess.run(
        ["git", "rev-parse", ref],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return text, sha


def _num(row: dict[str, Any], key: str) -> float | None:
    v = row.get(key)
    return float(v) if isinstance(v, (int, float)) else None


def derive(rows: list[dict[str, Any]]) -> dict[str, Any]:
    elasticities: list[float] = []
    regrets: list[float] = []
    for r in rows:
        cq, xq = _num(r, "clean_qty"), _num(r, "corrupt_qty")
        tp, sp = _num(r, "true_unit_cost"), _num(r, "stale_unit_cost")
        if None not in (cq, xq, tp, sp) and cq and tp and sp and abs(sp - tp) > 1e-9 and xq:
            assert cq and xq and tp and sp  # narrow types for mypy
            dp = math.log(sp / tp)
            if abs(dp) > 1e-9 and cq > 0 and xq > 0:
                elasticities.append(math.log(xq / cq) / dp)
        cc, oc = _num(r, "clean_cost"), _num(r, "oracle_clean_cost")
        if cc is not None and oc is not None:
            regrets.append(cc - oc)

    def _r(xs: list[float], nd: int) -> float | None:
        if not xs:
            return None
        v = round(median(xs), nd)
        return 0.0 if v == 0 else v  # normalize -0.0

    return {
        "n_rows": len(rows),
        "elasticity_median": _r(elasticities, 6),
        "elasticity_n": len(elasticities),
        "clean_regret_mean": round(mean(regrets), 4) if regrets else None,
        "clean_regret_median": round(median(regrets), 4) if regrets else None,
        "clean_regret_n": len(regrets),
    }


def build(ref: str, path: str, jsonl: str | None) -> dict[str, Any]:
    if jsonl is not None:
        text = Path(jsonl).read_text(encoding="utf-8")
        prov: dict[str, Any] = {"type": "local_jsonl", "source_file": jsonl}
    else:
        text, sha = _read_ref(ref, path)
        prov = {
            "type": "results_branch",
            "source_branch": ref,
            "source_file": path,
            "source_commit": sha,
        }
    rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    metrics = derive(rows)
    prov["derived_by"] = "scripts/derive_phase0a_metrics.py"
    prov["derived_date"] = date.today().isoformat()
    return {"run": "phase0a", **metrics, "provenance": prov}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    check = "--check" in args
    jsonl = None
    if "--jsonl" in args:
        jsonl = args[args.index("--jsonl") + 1]
    ref = args[args.index("--ref") + 1] if "--ref" in args else DEFAULT_REF
    path = args[args.index("--path") + 1] if "--path" in args else DEFAULT_PATH

    try:
        summary = build(ref, path, jsonl)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        # The results branch isn't fetched in this environment — leave 0a [pending].
        print(f"derive: source unavailable ({e}); 0a stays [pending]")
        return 0 if not check else 0
    text = json.dumps(summary, indent=2) + "\n"

    if check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print(
                f"derive: STALE {OUT.relative_to(ROOT)} — re-run scripts/derive_phase0a_metrics.py"
            )
            return 1
        print("derive: OK (phase0a_derived up to date)")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(
        f"wrote {OUT.relative_to(ROOT)}: elasticity={summary['elasticity_median']} "
        f"regret_mean={summary['clean_regret_mean']} (n={summary['elasticity_n']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
