"""Experiment dispatcher for the Part-4 kits.

    python -m benchmarks.experiments --exp h2-detection --out artifacts/h2.json     # mock, $0
    python -m benchmarks.experiments --exp h2-detection --arm live --out h2.json    # paid, real

Each experiment id maps to a slice of the GIGO matrix. ``--arm mock`` (default) runs
the deterministic matrix at $0 (CI). ``--arm live`` runs real Claude via
``sarc_dq.live_arms.apply_arm_live``; ``--fake`` exercises the live path at $0.

The live path is built for real paid runs: episodes run **concurrently**
(``--concurrency``, network-bound), results are **checkpointed per condition** and
**resumed** from ``--out`` on a re-run (nothing paid-for is lost), and a wall-clock
``--max-minutes`` budget plus an API-error guard stop cleanly and save partial
results before GitHub's 6h ceiling or a billing/auth failure. Predictions live in
the paired ``reports/prereg/<exp>.md``; nothing here invents a scientific result.
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


def _episode_evidence(cls: Any, rate: float, i: int, base_seed: int) -> tuple[Any, bool, Any]:
    """Deterministic (episode, corrupt, evidence) for episode index ``i``."""
    import random

    from sarc_dq.substrate import make_episode

    seed = (base_seed * 1_000_003 + i) & 0x7FFFFFFF
    episode = make_episode(seed, i)
    corrupt = random.Random(seed).random() < rate
    if corrupt:
        inj = cls.inject(episode.clean_price_record(), episode, random.Random(seed + 1))
        evidence = inj.evidence_set()
    else:
        evidence = (episode.clean_price_record(),)
    return episode, corrupt, evidence


def _run_condition_live(
    cls: Any,
    rate: float,
    arm: str,
    *,
    n_episodes: int,
    base_seed: int,
    agent: Any,
    critic: Any,
    concurrency: int,
) -> tuple[dict[str, Any], int]:
    """Run one (class, rate, arm) condition. Episodes run concurrently — the calls
    are network-bound, so a bounded thread pool cuts wall-clock time by ~``concurrency``.
    Returns (per-arm metrics, n_errors). An episode that raises (e.g. a billing/auth
    API error) is counted as an error, not a completed action."""
    import random
    from concurrent.futures import ThreadPoolExecutor

    from sarc_dq.config import TAU_M_DEFAULT
    from sarc_dq.gate import GovernedBuffer, PreActionGate
    from sarc_dq.live_arms import apply_arm_live

    def worker(i: int) -> tuple[bool, Any, BaseException | None]:
        seed = (base_seed * 1_000_003 + i) & 0x7FFFFFFF
        episode, corrupt, evidence = _episode_evidence(cls, rate, i, base_seed)
        buf = GovernedBuffer({episode.sku: episode.true_unit_cost})
        try:
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
            return corrupt, o, None
        except BaseException as exc:  # billing/auth/network — surfaced, not swallowed
            return corrupt, None, exc

    material = detected = completed = spend_it = spend_ot = 0
    n_corr = false_block = n_clean = errors = 0
    usd = 0.0
    workers = max(1, concurrency)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for corrupt, o, err in ex.map(worker, range(n_episodes)):
            if err is not None:
                errors += 1
                continue
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
    return {
        "adr": material / n_corr if n_corr else 0.0,
        "detection_rate": detected / n_corr if n_corr else 0.0,
        "false_block_rate": false_block / n_clean if n_clean else 0.0,
        "completion_rate": completed / n_episodes if n_episodes else 0.0,
        "n_corrupted": n_corr,
        "n_errors": errors,
        "usd": round(usd, 6),
        "input_tokens": spend_it,
        "output_tokens": spend_ot,
    }, errors


def _run_live_matrix(
    *,
    arms: tuple[str, ...],
    n_episodes: int,
    fake: bool,
    base_seed: int = 20260707,
    concurrency: int = 8,
    max_minutes: float | None = 330.0,
    resume_from: dict[str, Any] | None = None,
    on_checkpoint: Any = None,
    error_budget: int = 16,
) -> dict[str, Any]:
    """Live class × rate × arm matrix via ``apply_arm_live``. ``fake=True`` is $0.

    Robust for real paid runs: episodes run concurrently; results are checkpointed
    per condition (so a re-run resumes and nothing paid-for is lost); a wall-clock
    ``max_minutes`` budget stops cleanly before GitHub's 6h ceiling; and a burst of
    API errors (billing/auth) aborts gracefully with partial results saved."""
    import time

    from sarc_dq.live_arms import make_live
    from sarc_dq.taxonomy import get

    agent, critic = make_live(fake=fake)
    matrix: dict[str, Any] = {}
    total_usd = 0.0
    done: set[tuple[str, str, str]] = set()
    if resume_from and isinstance(resume_from.get("matrix"), dict):
        matrix = resume_from["matrix"]
        total_usd = float(resume_from.get("total_usd", 0.0) or 0.0)
        for cn, rates in matrix.items():
            for rk, per_arm in rates.items():
                for a in per_arm:
                    done.add((cn, rk, a))

    deadline = time.monotonic() + max_minutes * 60 if max_minutes is not None else None
    stopped: dict[str, Any] | None = None
    errors_total = 0
    conditions = [(c, r, a) for c in registered() for r in RATES for a in arms]

    def snapshot() -> dict[str, Any]:
        return {
            "config": {
                "n_episodes": n_episodes,
                "base_seed": base_seed,
                "arms": list(arms),
                "fake": fake,
                "concurrency": concurrency,
                "max_minutes": max_minutes,
            },
            "matrix": matrix,
            "total_usd": round(total_usd, 6),
            "cells_done": len(done),
            "cells_total": len(conditions),
            "stopped_early": stopped,
        }

    for cls_name, rate, arm in conditions:
        rk = f"{rate:.2f}"
        if (cls_name, rk, arm) in done:
            continue
        if deadline is not None and time.monotonic() > deadline:
            stopped = {
                "reason": "deadline",
                "at": f"{cls_name}/{rk}/{arm}",
                "max_minutes": max_minutes,
            }
            break
        per_arm, n_err = _run_condition_live(
            get(cls_name),
            rate,
            arm,
            n_episodes=n_episodes,
            base_seed=base_seed,
            agent=agent,
            critic=critic,
            concurrency=concurrency,
        )
        errors_total += n_err
        matrix.setdefault(cls_name, {}).setdefault(rk, {})[arm] = per_arm
        total_usd += per_arm["usd"]
        done.add((cls_name, rk, arm))
        if on_checkpoint is not None:
            on_checkpoint(snapshot())
        if errors_total >= error_budget:
            stopped = {
                "reason": "api_errors",
                "at": f"{cls_name}/{rk}/{arm}",
                "errors": errors_total,
                "hint": "likely out of API credits, or an auth/rate problem — "
                "check console.anthropic.com; re-run to resume from here",
            }
            break
    return snapshot()


def run(
    exp: str,
    *,
    n_episodes: int,
    arm_mode: str,
    fake: bool = False,
    concurrency: int = 8,
    max_minutes: float | None = 330.0,
    out_path: str | None = None,
) -> dict[str, Any]:
    if exp not in EXPERIMENTS:
        raise SystemExit(f"unknown experiment {exp!r}; known: {sorted(EXPERIMENTS)}")
    arms, intent = EXPERIMENTS[exp]
    if arm_mode == "live":
        note = (
            "LIVE via apply_arm_live with FAKE agent/critic ($0 pipeline check)"
            if fake
            else "LIVE — real Claude (claude-sonnet-5 agent, claude-opus-4-8 critic); spend logged"
        )
        envelope = {"experiment": exp, "intent": intent, "arm_mode": arm_mode, "note": note}
        # Resume from a prior (possibly partial) summary at out_path, if present.
        resume_from = None
        if out_path and Path(out_path).exists():
            try:
                resume_from = json.loads(Path(out_path).read_text(encoding="utf-8"))
            except Exception:
                resume_from = None

        def checkpoint(snap: dict[str, Any]) -> None:
            if out_path:
                _write_json(out_path, {**envelope, **snap})

        matrix = _run_live_matrix(
            arms=arms,
            n_episodes=n_episodes,
            fake=fake,
            concurrency=concurrency,
            max_minutes=max_minutes,
            resume_from=resume_from,
            on_checkpoint=checkpoint,
        )
        result = {**envelope, **matrix}
        if out_path:  # always persist the final summary, even if no condition ran
            _write_json(out_path, result)
        return result
    matrix = run_matrix(classes=registered(), rates=RATES, arms=arms, n_episodes=n_episodes)
    return {
        "experiment": exp,
        "intent": intent,
        "arm_mode": arm_mode,
        "note": "MOCK stand-in — pipeline reference, not a scientific result",
        **matrix,
    }


def _write_json(path: str, obj: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(_json_safe(obj), indent=2, allow_nan=False), encoding="utf-8")


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
    p.add_argument(
        "--concurrency",
        type=int,
        default=8,
        help="live: max concurrent API calls (network-bound; cuts wall-clock)",
    )
    p.add_argument(
        "--max-minutes",
        type=float,
        default=330.0,
        help="live: wall-clock budget; stop cleanly + save partial before this",
    )
    p.add_argument("--out", default="artifacts/exp_summary.json")
    args = p.parse_args(argv)

    result = run(
        args.exp,
        n_episodes=args.episodes,
        arm_mode=args.arm,
        fake=args.fake,
        concurrency=args.concurrency,
        max_minutes=args.max_minutes,
        out_path=args.out,
    )
    _write_json(args.out, result)
    stopped = result.get("stopped_early")
    tail = f"  [STOPPED EARLY: {stopped['reason']}]" if stopped else ""
    print(f"experiment {args.exp} [{args.arm}] -> {args.out}  ({result['intent']}){tail}")
    # Exit 0 even on a graceful early stop: partial results are saved and must be
    # committed/uploaded (never discard paid-for work). Setup errors raised earlier.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
