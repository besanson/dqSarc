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


def _run_live_matrix(
    *, arms: tuple[str, ...], n_episodes: int, fake: bool, base_seed: int = 20260707
) -> dict[str, Any]:
    """Live class × rate × arm matrix via ``apply_arm_live``. ``fake=True`` is $0."""
    import random

    from sarc_dq.config import TAU_M_DEFAULT
    from sarc_dq.gate import GovernedBuffer, PreActionGate
    from sarc_dq.live_arms import apply_arm_live, make_live
    from sarc_dq.substrate import make_episode
    from sarc_dq.taxonomy import get

    agent, critic = make_live(fake=fake)
    out: dict[str, Any] = {}
    total_usd = 0.0
    for cls_name in registered():
        out[cls_name] = {}
        cls = get(cls_name)
        for rate in RATES:
            per_arm: dict[str, Any] = {}
            for arm in arms:
                material = detected = completed = spend_it = spend_ot = 0
                n_corr = false_block = n_clean = 0
                usd = 0.0
                for i in range(n_episodes):
                    seed = (base_seed * 1_000_003 + i) & 0x7FFFFFFF
                    episode = make_episode(seed, i)
                    crng = random.Random(seed)
                    corrupt = crng.random() < rate
                    if corrupt:
                        inj = cls.inject(
                            episode.clean_price_record(), episode, random.Random(seed + 1)
                        )
                        evidence = inj.evidence_set()
                    else:
                        evidence = (episode.clean_price_record(),)
                    buf = GovernedBuffer({episode.sku: episode.true_unit_cost})
                    o = apply_arm_live(
                        arm,
                        episode,
                        evidence,
                        corrupted=corrupt,
                        gate=PreActionGate(buffer=buf),
                        velocity=0.5,
                        rng=random.Random(seed + 2),
                        tau_m=TAU_M_DEFAULT,
                        agent=agent,
                        critic=critic,
                    )
                    usd += o.usd
                    spend_it += o.input_tokens
                    spend_ot += o.output_tokens
                    if corrupt:
                        n_corr += 1
                        if o.detected:
                            detected += 1
                        if o.completed and o.material:
                            material += 1
                    else:
                        n_clean += 1
                        if not o.completed:
                            false_block += 1
                    if o.completed:
                        completed += 1
                total_usd += usd
                per_arm[arm] = {
                    "adr": material / n_corr if n_corr else 0.0,
                    "detection_rate": detected / n_corr if n_corr else 0.0,
                    "false_block_rate": false_block / n_clean if n_clean else 0.0,
                    "completion_rate": completed / n_episodes if n_episodes else 0.0,
                    "n_corrupted": n_corr,
                    "usd": round(usd, 6),
                    "input_tokens": spend_it,
                    "output_tokens": spend_ot,
                }
            out[cls_name][f"{rate:.2f}"] = per_arm
    return {
        "config": {
            "n_episodes": n_episodes,
            "base_seed": base_seed,
            "arms": list(arms),
            "fake": fake,
        },
        "matrix": out,
        "total_usd": round(total_usd, 6),
    }


def run(exp: str, *, n_episodes: int, arm_mode: str, fake: bool = False) -> dict[str, Any]:
    if exp not in EXPERIMENTS:
        raise SystemExit(f"unknown experiment {exp!r}; known: {sorted(EXPERIMENTS)}")
    arms, intent = EXPERIMENTS[exp]
    if arm_mode == "live":
        matrix = _run_live_matrix(arms=arms, n_episodes=n_episodes, fake=fake)
        note = (
            "LIVE via apply_arm_live with FAKE agent/critic ($0 pipeline check)"
            if fake
            else "LIVE — real Claude (claude-sonnet-5 agent, claude-opus-4-8 critic); spend logged"
        )
        return {"experiment": exp, "intent": intent, "arm_mode": arm_mode, "note": note, **matrix}
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
    p.add_argument(
        "--fake",
        action="store_true",
        help="live path with deterministic fake agent/critic ($0 CI check)",
    )
    p.add_argument("--episodes", type=int, default=100)
    p.add_argument("--out", default="artifacts/exp_summary.json")
    args = p.parse_args(argv)

    result = run(args.exp, n_episodes=args.episodes, arm_mode=args.arm, fake=args.fake)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(_json_safe(result), indent=2, allow_nan=False), encoding="utf-8")
    print(f"experiment {args.exp} [{args.arm}] -> {out}  ({result['intent']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
