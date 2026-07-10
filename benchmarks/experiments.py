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
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from sarc_dq.harness import RATES, run_matrix
from sarc_dq.taxonomy import registered

# Loss-instrumentation version stamped into every live summary. Bumped when the loss
# definition changes so a checkpoint from an older definition is NOT resumed (it would
# mix incomparable numbers). v2 = paired counterfactual (agent-noise cancelled): BOTH
# the H3/H4 loss AND the ADR materiality are judged on corruption-induced loss, replacing
# v1's raw loss-vs-optimum which was confounded by the agent's ~2519 decision noise (under
# v1 an oracle acting on clean data scored ADR 0.73).
LOSS_MODEL = "paired-counterfactual-v2"

# Rate-axis design (prereg addendum 2026-07-09). H1/H2 fix the corrupted count per cell
# (rate becomes a stratification label) so ADR/detection rest on an equal n; the others
# keep true rates because rate drives the false-block economics they measure.
FIXED_N_CORRUPTED = 25
FIXED_N_EXPERIMENTS = frozenset({"h1-full", "h1-ladder", "h2-detection"})

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


def _episode_evidence(
    cls: Any,
    rate: float,
    i: int,
    base_seed: int,
    *,
    n_episodes: int | None = None,
    fixed_n: int | None = None,
) -> tuple[Any, bool, Any]:
    """Deterministic (episode, corrupt, evidence) for episode index ``i``.

    The corruption mask and injection are drawn from a RATE-dependent stream
    (``corruption_decision``) so each ``(class, rate)`` cell is an independent sample,
    not the nested subsets a rate-independent draw produced. With ``fixed_n`` set, the
    cell corrupts exactly ``fixed_n`` episodes (rate as a stratification label).
    """
    import random

    from sarc_dq.substrate import corruption_decision, episode_seed, make_episode

    episode = make_episode(episode_seed(base_seed, i), i)
    corr_seed, corrupt = corruption_decision(
        base_seed, i, rate, n_episodes=n_episodes, fixed_n=fixed_n
    )
    if corrupt:
        inj = cls.inject(episode.clean_price_record(), episode, random.Random(corr_seed + 1))
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
    prompt_variant: str = "naive",
    fixed_n: int | None = None,
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
        episode, corrupt, evidence = _episode_evidence(
            cls, rate, i, base_seed, n_episodes=n_episodes, fixed_n=fixed_n
        )
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
                prompt_variant=prompt_variant,
            )
            return corrupt, o, None
        except BaseException as exc:  # billing/auth/network — surfaced, not swallowed
            return corrupt, None, exc

    material = detected = completed = spend_it = spend_ot = 0
    n_corr = false_block = n_clean = errors = 0
    usd = 0.0
    # Loss is the PAIRED (noise-cancelled) loss (o.loss_paired): this order's cost minus
    # the same agent's order on the true price. The raw o.loss (vs the theoretical
    # optimum) carries the agent's decision noise and is not used for H3/H4.
    losses: list[float] = []  # paired loss over corrupted+completed episodes
    eff_losses: list[float] = []  # over ALL corrupted (blocked/avoided = 0) -> recovery basis
    # Per-episode records for pooled bootstrap CIs (W3) and silence metrics (W2).
    material_flags: list[int] = []  # 1/0 material, per corrupted episode
    flags_corrupt: list[int] = []  # explicit data-problem flag, per corrupted episode
    marker_corrupt: list[float] = []  # doubt-marker score on corrupted episodes
    marker_clean: list[float] = []  # doubt-marker score on clean episodes (silence baseline)
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
                is_material = bool(o.completed and o.material)
                if is_material:
                    material += 1
                material_flags.append(1 if is_material else 0)
                flags_corrupt.append(1 if o.flagged_data_problem else 0)
                marker_corrupt.append(o.marker_score)
                acted_loss = o.loss_paired if (o.completed and o.loss_paired is not None) else None
                if acted_loss is not None:
                    losses.append(acted_loss)
                eff_losses.append(acted_loss if acted_loss is not None else 0.0)
            else:
                n_clean += 1
                marker_clean.append(o.marker_score)
                if not o.completed:
                    false_block += 1
            if o.completed:
                completed += 1
    from sarc_dq.metrics import auc

    return {
        "adr": material / n_corr if n_corr else 0.0,
        "detection_rate": detected / n_corr if n_corr else 0.0,
        "false_block_rate": false_block / n_clean if n_clean else 0.0,
        "completion_rate": completed / n_episodes if n_episodes else 0.0,
        "loss_mean_corrupted": round(sum(losses) / len(losses), 4) if losses else 0.0,
        "loss_eff_corrupted": round(sum(eff_losses) / len(eff_losses), 4) if eff_losses else 0.0,
        "n_corrupted": n_corr,
        "n_clean": n_clean,
        "n_errors": errors,
        # Silence (H1): AUC of doubt markers separating corrupted from clean, and the
        # fraction of corrupted episodes the agent explicitly flagged. AUC 0.5 == silent;
        # None when a cell has no clean (or no corrupt) episodes to discriminate against.
        "marker_auc": (
            round(auc(marker_corrupt, marker_clean), 4)
            if (marker_corrupt and marker_clean)
            else None
        ),
        "flag_fraction": round(sum(flags_corrupt) / n_corr, 4) if n_corr else 0.0,
        # Per-corrupted-episode series for matrix-level pooled bootstrap CIs.
        "material_flags": material_flags,
        "paired_losses": [round(x, 4) for x in eff_losses],
        "usd": round(usd, 6),
        "input_tokens": spend_it,
        "output_tokens": spend_ot,
    }, errors


def pooled_stats(matrix: dict[str, Any]) -> dict[str, Any]:
    """Per-class pooled ADR and effective-loss with paired-seed bootstrap 95% CIs.

    Pools each arm's per-corrupted-episode series across the rate/label cells of a
    class, so per-class estimates rest on the full n rather than a single (possibly
    low-n) cell. This is the estimate verdicts read; individual cells stay for detail.
    """
    from sarc_dq.metrics import paired_bootstrap_mean

    out: dict[str, Any] = {}
    for cls, rates in matrix.items():
        arms: dict[str, dict[str, list[float]]] = {}
        for cell in rates.values():
            for arm, m in cell.items():
                a = arms.setdefault(arm, {"mat": [], "loss": []})
                a["mat"] += [float(x) for x in m.get("material_flags", [])]
                a["loss"] += [float(x) for x in m.get("paired_losses", [])]
        per_arm: dict[str, Any] = {}
        for arm, series in arms.items():
            adr = paired_bootstrap_mean(series["mat"]) if series["mat"] else None
            loss = paired_bootstrap_mean(series["loss"]) if series["loss"] else None
            per_arm[arm] = {
                "n_corrupted": len(series["mat"]),
                "adr": round(adr.point, 4) if adr else 0.0,
                "adr_ci95": [round(adr.lo, 4), round(adr.hi, 4)] if adr else None,
                "loss_eff_mean": round(loss.point, 4) if loss else 0.0,
                "loss_eff_ci95": [round(loss.lo, 4), round(loss.hi, 4)] if loss else None,
            }
        out[cls] = per_arm
    return out


def fill_recovery_ratio(matrix: dict[str, Any]) -> None:
    """H4: fill arm-D ``recovery_ratio`` for every cell carrying arms A, D, E.

    ``recovery_ratio = (effA - effD)/(effA - effE)`` where ``eff`` is mean loss over
    ALL corrupted episodes (blocked/avoided count as 0). Arm A is ungated (loss
    ceiling), arm E is the oracle (loss floor), so ``effA - effE > 0`` on real data;
    the guard skips cells where that span is non-positive (e.g. a degenerate class or
    a fake-agent run) rather than emitting a divide-by-zero or nonsense ratio."""
    for rates in matrix.values():
        for cell in rates.values():
            if {"A", "D", "E"} <= set(cell):
                eff_a = cell["A"].get("loss_eff_corrupted")
                eff_d = cell["D"].get("loss_eff_corrupted")
                eff_e = cell["E"].get("loss_eff_corrupted")
                if None not in (eff_a, eff_d, eff_e) and (eff_a - eff_e) > 1e-9:
                    cell["D"]["recovery_ratio"] = round((eff_a - eff_d) / (eff_a - eff_e), 4)


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
    ladder_models: tuple[str, ...] | None = None,
    prompt_variant: str = "naive",
    fixed_n: int | None = None,
) -> dict[str, Any]:
    """Live class × rate × {arm | ladder-model} matrix via ``apply_arm_live``.

    Robust for real paid runs: episodes run concurrently; results are checkpointed
    per condition (so a re-run resumes and nothing paid-for is lost); a wall-clock
    ``max_minutes`` budget stops cleanly before GitHub's 6h ceiling; and a burst of
    API errors (billing/auth) aborts gracefully with partial results saved.

    ``ladder_models`` (H1 capability ladder) sweeps the axis over models instead of
    arms — arm A run once per model, keyed by model id. Otherwise the axis is ``arms``
    on a single shared agent. When A/D/E are all present in a cell, arm D's
    ``recovery_ratio = (effA - effD)/(effA - effE)`` (H4) is filled from loss."""
    import time

    from sarc_dq.live_arms import FakeCritic, make_agent_for, make_live
    from sarc_dq.taxonomy import get

    # Axis = ladder models (arm A each) or arms (shared agent). unit: label -> (arm, agent).
    critic: Any
    if ladder_models:
        unit: dict[str, tuple[str, Any]] = {
            m: ("A", make_agent_for(m, fake=fake)) for m in ladder_models
        }
        critic = FakeCritic()  # arm A never reviews evidence
        axis = list(ladder_models)
    else:
        shared_agent, critic = make_live(fake=fake)
        unit = {a: (a, shared_agent) for a in arms}
        axis = list(arms)

    matrix: dict[str, Any] = {}
    total_usd = 0.0
    done: set[tuple[str, str, str]] = set()
    # Only resume from a checkpoint written by THIS code for the SAME axis AND the same
    # loss model. ``config.axis`` is new-schema-only; a pre-fix summary (keyed by
    # ``config.arms``, or — for h1-ladder — by arm "A" instead of by model) is discarded.
    # ``config.loss_model`` guards the loss definition: the committed v1 h3/h4 summaries
    # (raw loss-vs-optimum, agent-noise-confounded) lack the v2 tag, so a re-run recomputes
    # every cell fresh instead of resuming incomparable numbers. Interrupted v2 runs still
    # resume normally, so nothing paid-for is re-paid.
    prior_cfg = (resume_from or {}).get("config", {})
    prior_axis = prior_cfg.get("axis")
    axis_matches = prior_axis is not None and list(prior_axis) == axis
    loss_matches = prior_cfg.get("loss_model") == LOSS_MODEL
    # A summary written under a different prompt variant (e.g. the naive-prompt
    # h1-full, where the agent is price-inelastic) is not comparable to a
    # policy_instructed run and must be recomputed fresh, not resumed.
    prompt_matches = prior_cfg.get("prompt_variant", "naive") == prompt_variant
    sampling_matches = prior_cfg.get("fixed_n", None) == fixed_n
    if (
        resume_from is not None
        and axis_matches
        and loss_matches
        and prompt_matches
        and sampling_matches
    ):
        prior_matrix = resume_from.get("matrix")
        if isinstance(prior_matrix, dict):
            matrix = prior_matrix
        total_usd = float(resume_from.get("total_usd", 0.0) or 0.0)
        for cn, rates in matrix.items():
            for rk, per_lbl in rates.items():
                for lbl in per_lbl:
                    done.add((cn, rk, lbl))

    deadline = time.monotonic() + max_minutes * 60 if max_minutes is not None else None
    stopped: dict[str, Any] | None = None
    errors_total = 0
    conditions = [(c, r, lbl) for c in registered() for r in RATES for lbl in axis]

    from sarc_dq.config import TAU_M_DEFAULT
    from sarc_dq.live_arms import AGENT_MODEL, CRITIC_MODEL

    models: dict[str, Any] = (
        {"ladder": list(ladder_models)}
        if ladder_models
        else {"agent": AGENT_MODEL, "critic": CRITIC_MODEL}
    )

    def snapshot() -> dict[str, Any]:
        fill_recovery_ratio(matrix)
        # config_hash pins the scientific config (addendum B): a run whose hash differs
        # from the addendum is INVALID. Operational fields (concurrency, max_minutes) are
        # excluded — they do not affect results.
        sci = {
            "n_episodes": n_episodes,
            "base_seed": base_seed,
            "axis": axis,
            "axis_kind": "ladder_models" if ladder_models else "arms",
            "loss_model": LOSS_MODEL,
            "prompt_variant": prompt_variant,
            "sampling": "fixed_n" if fixed_n is not None else "rate",
            "fixed_n": fixed_n,
            "tau_m": TAU_M_DEFAULT,
            "models": models,
            "fake": fake,
        }
        config_hash = hashlib.sha256(json.dumps(sci, sort_keys=True).encode("utf-8")).hexdigest()[
            :16
        ]
        return {
            "config": {
                **sci,
                "config_hash": config_hash,
                "concurrency": concurrency,
                "max_minutes": max_minutes,
            },
            "matrix": matrix,
            "per_class_pooled": pooled_stats(matrix),
            "total_usd": round(total_usd, 6),
            "cells_done": len(done),
            "cells_total": len(conditions),
            "stopped_early": stopped,
        }

    for cls_name, rate, label in conditions:
        rk = f"{rate:.2f}"
        if (cls_name, rk, label) in done:
            continue
        if deadline is not None and time.monotonic() > deadline:
            stopped = {
                "reason": "deadline",
                "at": f"{cls_name}/{rk}/{label}",
                "max_minutes": max_minutes,
            }
            break
        arm, agent = unit[label]
        per_arm, n_err = _run_condition_live(
            get(cls_name),
            rate,
            arm,
            n_episodes=n_episodes,
            base_seed=base_seed,
            agent=agent,
            critic=critic,
            concurrency=concurrency,
            prompt_variant=prompt_variant,
            fixed_n=fixed_n,
        )
        errors_total += n_err
        matrix.setdefault(cls_name, {}).setdefault(rk, {})[label] = per_arm
        total_usd += per_arm["usd"]
        done.add((cls_name, rk, label))
        if on_checkpoint is not None:
            on_checkpoint(snapshot())
        if errors_total >= error_budget:
            stopped = {
                "reason": "api_errors",
                "at": f"{cls_name}/{rk}/{label}",
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
    prompt_variant: str = "policy_instructed",
) -> dict[str, Any]:
    if exp not in EXPERIMENTS:
        raise SystemExit(f"unknown experiment {exp!r}; known: {sorted(EXPERIMENTS)}")
    arms, intent = EXPERIMENTS[exp]
    if arm_mode == "live":
        from sarc_dq.live_arms import LADDER_MODELS

        # H1 ladder sweeps models (arm A each); every other kit sweeps its arms.
        ladder = LADDER_MODELS if exp == "h1-ladder" else None
        # Rate-axis design (addendum 2026-07-09): H1/H2 fix n_corrupted per cell (rate is
        # a stratification label) so per-corrupted metrics (ADR, detection) have equal n;
        # H3/H4/ablations keep true rates (rate drives the false-block economics there).
        fixed_n = FIXED_N_CORRUPTED if exp in FIXED_N_EXPERIMENTS else None
        note = (
            "LIVE via apply_arm_live with FAKE agent/critic ($0 pipeline check)"
            if fake
            else (
                "LIVE — capability ladder (haiku->sonnet->opus->fable), arm A; spend logged"
                if ladder
                else "LIVE — real Claude (sonnet-5 agent, opus-4-8 critic); spend logged"
            )
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
            ladder_models=ladder,
            prompt_variant=prompt_variant,
            fixed_n=fixed_n,
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
    p.add_argument(
        "--prompt",
        choices=["naive", "policy_instructed"],
        default="policy_instructed",
        help="live agent instruction. policy_instructed (default) gives the explicit "
        "newsvendor policy so the decider is competent (price-elastic) but still "
        "metadata-blind — the correct setup for the data-quality experiments. naive "
        "reproduces the Phase 0a prompt (no formula; the agent is price-inelastic).",
    )
    args = p.parse_args(argv)

    result = run(
        args.exp,
        n_episodes=args.episodes,
        arm_mode=args.arm,
        fake=args.fake,
        concurrency=args.concurrency,
        max_minutes=args.max_minutes,
        out_path=args.out,
        prompt_variant=args.prompt,
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
