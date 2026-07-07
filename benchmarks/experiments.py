"""Experiment dispatcher for the Part-4 kits — build, do NOT run live here.

    python -m benchmarks.experiments --exp h2-detection --out artifacts/h2.json

Each experiment id maps to a slice of the frozen GIGO matrix. The default runs the
deterministic **mock** matrix (so the kits are CI-testable at $0); ``--arm live``
is reserved for the workflow to run the real agent once the arm-level live agent
is wired (tracked in PROGRESS.md). The registered predictions live in the paired
``reports/prereg/<exp>.md``; nothing here reads or writes a scientific result.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from sarc_dq.harness import RATES, run_matrix
from sarc_dq.taxonomy import registered

# exp id -> (arms exercised, one-line intent). Classes default to all 8.
EXPERIMENTS: dict[str, tuple[tuple[str, ...], str]] = {
    "h1-full": (("A",), "silence: all classes, no gate"),
    "h1-ladder": (("A",), "silence vs capability ladder (live-only: haiku->sonnet->opus->fable)"),
    "h2-detection": (("B", "C", "D"), "detection asymmetry by channel x arm"),
    "h3-frontier": (("C", "D", "F"), "loss avoided vs false-block at matched completion"),
    "h4-recovery": (("A", "D", "E"), "downstream recovery ratio vs oracle"),
    "ablations": (("D",), "each predicate off, one at a time"),
    "tier2-validation": (("D",), "predicates vs labeled real-error datasets (needs Tier-2 data)"),
}


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    return obj


def run(exp: str, *, n_episodes: int, arm_mode: str) -> dict[str, Any]:
    if exp not in EXPERIMENTS:
        raise SystemExit(f"unknown experiment {exp!r}; known: {sorted(EXPERIMENTS)}")
    arms, intent = EXPERIMENTS[exp]
    if arm_mode == "live":  # pragma: no cover - live wiring is a tracked TODO
        raise SystemExit(
            "live arms are not wired yet (mock stand-in only) — see PROGRESS.md human items"
        )
    matrix = run_matrix(classes=registered(), rates=RATES, arms=arms, n_episodes=n_episodes)
    return {
        "experiment": exp,
        "intent": intent,
        "arm_mode": arm_mode,
        "note": "MOCK stand-in — pipeline reference, not a scientific result",
        **matrix,
    }


def main(argv: Any = None) -> int:
    p = argparse.ArgumentParser(prog="benchmarks.experiments", description=__doc__)
    p.add_argument("--exp", required=True, choices=sorted(EXPERIMENTS))
    p.add_argument("--arm", choices=["mock", "live"], default="mock")
    p.add_argument("--episodes", type=int, default=100)
    p.add_argument("--out", default="artifacts/exp_summary.json")
    args = p.parse_args(argv)

    result = run(args.exp, n_episodes=args.episodes, arm_mode=args.arm)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(_json_safe(result), indent=2, allow_nan=False), encoding="utf-8")
    print(f"experiment {args.exp} [{args.arm}] -> {out}  ({result['intent']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
