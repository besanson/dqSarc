"""Run the six-arm × taxonomy × rate matrix (deterministic mock, $0).

    python -m benchmarks.harness_matrix --episodes 100 --out artifacts/matrix.json

This is the CI-runnable, offline exercise of every arm and every corruption class.
It is *not* a scientific result — the real numbers come from the Part-4 experiment
kits run live. Written so the whole matrix stays green at $0.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from sarc_dq.harness import run_matrix


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    return obj


def main(argv: Any = None) -> int:
    p = argparse.ArgumentParser(prog="benchmarks.harness_matrix", description=__doc__)
    p.add_argument("--episodes", type=int, default=100)
    p.add_argument("--out", default="artifacts/matrix.json")
    args = p.parse_args(argv)

    result = run_matrix(n_episodes=args.episodes)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(_json_safe(result), indent=2, allow_nan=False), encoding="utf-8")

    # One-line H2 sanity summary at 20% rate, arms A/C/D.
    print(
        f"matrix: {len(result['matrix'])} classes x {len(result['config']['rates'])} rates "
        f"x {len(result['config']['arms'])} arms -> {out}"
    )
    for cls, by_rate in result["matrix"].items():
        cell = by_rate.get("0.20", {})
        a, c, d = cell.get("A", {}), cell.get("C", {}), cell.get("D", {})
        print(
            f"  {cls:34s} A.adr={a.get('adr', 0):.2f} "
            f"C.detect={c.get('detection_rate', 0):.2f} "
            f"D.detect={d.get('detection_rate', 0):.2f} "
            f"D.recovery={d.get('recovery_ratio')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
