"""GIGO-Bench reproduce/verify (Part 3 freeze).

    python -m benchmarks.gigo.reproduce                                   # run + write summary
    python -m benchmarks.gigo.reproduce --verify benchmarks/gigo/reference_summary.json

Runs the frozen conditions matrix (corruption class × rate {2,5,10,20%} × arm
A–F) via the deterministic mock harness and writes a ``reference_summary.json``.
``--verify`` re-runs and checks per-metric tolerances against the committed
reference, exiting 2 on drift — the same discipline as Green SARC's IBP verify.

The mock matrix is a **pipeline reference**, not a scientific result; the live
H1–H4 numbers come from the Part-4 experiment kits.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from sarc_dq.harness import run_matrix

# Per-metric absolute tolerances for --verify (rates/ratios). Losses are checked
# relatively. The mock is deterministic, so drift should be ~0; the tolerance
# guards against incidental float noise across platforms.
_ABS = {"adr", "detection_rate", "false_block_rate", "completion_rate", "recovery_ratio"}
_ABS_TOL = 0.02
_REL_TOL = 0.02


def _summary(n_episodes: int) -> dict[str, Any]:
    return run_matrix(n_episodes=n_episodes)


def _cells(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    flat: dict[str, dict[str, Any]] = {}
    for cls, by_rate in summary["matrix"].items():
        for rate, by_arm in by_rate.items():
            for arm, metrics in by_arm.items():
                flat[f"{cls}|{rate}|{arm}"] = metrics
    return flat


def _verify(summary: dict[str, Any], ref_path: str) -> int:
    ref = json.loads(Path(ref_path).read_text(encoding="utf-8"))
    new_c, ref_c = _cells(summary), _cells(ref)
    failures: list[str] = []
    for key, ref_metrics in ref_c.items():
        new_metrics = new_c.get(key)
        if new_metrics is None:
            failures.append(f"{key}: missing in new run")
            continue
        for metric, ref_val in ref_metrics.items():
            if not isinstance(ref_val, (int, float)):
                continue
            new_val = new_metrics.get(metric)
            if not isinstance(new_val, (int, float)):
                failures.append(f"{key}.{metric}: type/None drift")
                continue
            if metric in _ABS:
                if abs(new_val - ref_val) > _ABS_TOL:
                    failures.append(f"{key}.{metric}: {ref_val:.4f} -> {new_val:.4f}")
            else:
                denom = max(abs(ref_val), 1.0)
                if abs(new_val - ref_val) / denom > _REL_TOL:
                    failures.append(f"{key}.{metric}: {ref_val:.2f} -> {new_val:.2f}")
    if failures:
        print("gigo verify: FAILED")
        for f in failures[:40]:
            print("  " + f)
        return 2
    print(f"gigo verify: OK ({len(ref_c)} cells within tolerance)")
    return 0


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    return obj


def main(argv: Any = None) -> int:
    p = argparse.ArgumentParser(prog="benchmarks.gigo.reproduce", description=__doc__)
    p.add_argument("--episodes", type=int, default=100)
    p.add_argument("--out", default="artifacts/gigo_summary.json")
    p.add_argument("--verify", default=None)
    args = p.parse_args(argv)

    summary = _summary(args.episodes)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(_json_safe(summary), indent=2, allow_nan=False), encoding="utf-8")
    print(
        f"gigo: wrote {out} "
        f"({len(summary['matrix'])} classes x {len(summary['config']['rates'])} rates "
        f"x {len(summary['config']['arms'])} arms)"
    )
    if args.verify:
        return _verify(summary, args.verify)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
