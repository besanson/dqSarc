"""Phase 0 smoke test: does the silent-failure effect exist at all? (brief §4)

100 seeded corrupted episodes + the **same 100 seeds** clean, one corruption
class (stale unit price), no gate, no advisory — same agent, same prompts, same
everything except the injected corruption. We measure ADR, the loss distribution,
behavioral markers + LLM-judge doubt on both arms, and the discrimination AUC,
then apply the kill criterion.

Dual-channel logging per episode (brief §6): a **cost** channel (USD + tokens,
cumulative) and an **evidence** channel (the record read, its metadata, the
ground-truth tag, the decision). Both keyed to seed + config hash.

Refusals are their own outcome class and never counted as action defects
(brief §3).
"""

from __future__ import annotations

import random
import statistics
from dataclasses import asdict, dataclass, field
from typing import Any

from sarc_dq.agent import make_agent
from sarc_dq.agent.base import OUTCOME_OK, OUTCOME_REFUSAL, Agent
from sarc_dq.config import VALIDITY_MIN_SCORED_FRACTION, RunConfig
from sarc_dq.injectors import STALE_UNIT_PRICE
from sarc_dq.judge import make_judge, validate
from sarc_dq.judge.base import Judge
from sarc_dq.markers import extract
from sarc_dq.metrics import (
    action_defect_rate,
    bootstrap_auc,
    is_material,
    paired_bootstrap_mean,
    quantiles,
)
from sarc_dq.substrate import make_episode


@dataclass
class EpisodeResult:
    index: int
    seed: int
    outcome: str
    # Evidence channel
    evidence_id_clean: str
    evidence_id_corrupt: str
    age_days: int
    true_unit_cost: float
    stale_unit_cost: float
    # Actions + loss (currency)
    clean_qty: float
    corrupt_qty: float
    clean_cost: float
    corrupt_cost: float
    loss: float
    material: bool
    # Oracle baseline: a perfect newsvendor solver that trusts the price it is
    # shown (optimal_order on each arm's believed price). Isolates the loss that
    # the stale price forces through the *optimal* rule, independent of LLM
    # decision noise — so agent-ADR can be read against oracle-ADR.
    oracle_clean_qty: float
    oracle_corrupt_qty: float
    oracle_clean_cost: float
    oracle_corrupt_cost: float
    oracle_loss: float
    oracle_material: bool
    # Behavioral signals
    marker_clean: float
    marker_corrupt: float
    doubt_clean: float
    doubt_corrupt: float
    flagged_corrupt: bool
    # Cost channel
    usd: float
    input_tokens: int
    output_tokens: int


@dataclass
class Phase0Result:
    config: dict[str, Any]
    config_hash: str
    n_episodes: int
    n_scored: int  # episodes that reached a decision (excludes refusals/errors)
    n_refusals: int
    n_errors: int
    n_parse_failures: int  # subset of errors: unparseable ORDER line (excluded from ADR)
    adr: float
    oracle_adr: float  # ADR of a perfect metadata-blind newsvendor solver (baseline)
    loss_quantiles: dict[str, float]
    oracle_loss_quantiles: dict[str, float]
    loss_ci: dict[str, float]
    tail_ratio: float
    heavy_tail_flag: bool
    marker_auc: dict[str, float]
    judge_auc: dict[str, float]
    flagged_fraction: float
    judge_validation: dict[str, float]
    kill_verdict: str
    kill_detail: str
    spend_usd: float
    # Phase 0b additions.
    elasticity_median: float  # median Δq_agent / Δq_oracle (P4)
    elasticity_n: int  # episodes with a materially non-zero oracle Δq used in the median
    clean_regret: dict[str, float]  # agent clean_cost − oracle clean_cost (decision noise)
    failure_autopsy: dict[str, Any]  # drift distribution + which arm failed
    episodes: list[dict[str, Any]] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)


def run_phase0(
    config: RunConfig,
    *,
    agent: Agent | None = None,
    judge: Judge | None = None,
) -> Phase0Result:
    """Execute the Phase 0 protocol and return a fully structured result.

    ``agent`` / ``judge`` may be injected (tests use a failing stub to exercise the
    failure-logging path); by default they are built from ``config.arm``.
    """
    agent = agent if agent is not None else make_agent(config.arm, config.agent_model)
    judge = judge if judge is not None else make_judge(config.arm, config.judge_model)
    injector = STALE_UNIT_PRICE

    results: list[EpisodeResult] = []
    failures: list[dict[str, Any]] = []
    spend = 0.0
    n_refusals = n_errors = n_parse_failures = 0

    for i in range(config.n_episodes):
        seed = config.episode_seed(i)
        episode = make_episode(seed, i)
        clean_rec = episode.clean_price_record()
        # A dedicated RNG stream for injection, derived from the paired seed so
        # the corruption draw is reproducible yet independent of the episode draw.
        inject_rng = random.Random(seed + 1)
        corrupt_rec = injector.inject(clean_rec, episode, inject_rng)

        clean_dec = agent.decide(
            episode, clean_rec, advisory=False, prompt_variant=config.prompt_variant
        )
        corrupt_dec = agent.decide(
            episode, corrupt_rec, advisory=False, prompt_variant=config.prompt_variant
        )

        # Cost channel: agent calls on both arms + judge calls on both transcripts.
        cj = judge.score(clean_dec.transcript)
        dj = judge.score(corrupt_dec.transcript)
        usd = clean_dec.usd + corrupt_dec.usd + cj.usd + dj.usd
        spend += usd

        if corrupt_dec.outcome != OUTCOME_OK or clean_dec.outcome != OUTCOME_OK:
            is_refusal = OUTCOME_REFUSAL in (clean_dec.outcome, corrupt_dec.outcome)
            is_parse_fail = bool(
                clean_dec.raw.get("parse_failed") or corrupt_dec.raw.get("parse_failed")
            )
            if is_refusal:
                n_refusals += 1
            else:
                n_errors += 1
                if is_parse_fail:
                    n_parse_failures += 1
            # Log the failed pair so it is auditable (excluded from ADR). Records
            # the outcome, both raw transcripts, and the injected drift.
            gt = corrupt_rec.ground_truth
            if clean_dec.outcome != OUTCOME_OK and corrupt_dec.outcome != OUTCOME_OK:
                failed_arm = "both"
            elif corrupt_dec.outcome != OUTCOME_OK:
                failed_arm = "corrupt"
            else:
                failed_arm = "clean"
            true_c = float(gt["true_unit_cost"])
            stale_c = float(gt["stale_unit_cost"])
            failures.append(
                {
                    "kind": "failure",
                    "index": i,
                    "seed": seed,
                    "failed_arm": failed_arm,
                    "is_refusal": is_refusal,
                    "is_parse_failure": is_parse_fail,
                    "clean_outcome": clean_dec.outcome,
                    "corrupt_outcome": corrupt_dec.outcome,
                    "clean_transcript": clean_dec.transcript,
                    "corrupt_transcript": corrupt_dec.transcript,
                    "true_unit_cost": true_c,
                    "stale_unit_cost": stale_c,
                    "drift_frac": (stale_c / true_c - 1.0) if true_c else float("nan"),
                    "age_days": int(gt["age_days"]),
                }
            )
            continue

        clean_cost = episode.realised_cost(clean_dec.order_qty)
        corrupt_cost = episode.realised_cost(corrupt_dec.order_qty)
        loss = corrupt_cost - clean_cost
        mk_c = extract(clean_dec.transcript)
        mk_d = extract(corrupt_dec.transcript)
        gt = corrupt_rec.ground_truth

        # Oracle: optimal newsvendor order on each arm's *believed* price (the value
        # actually shown in that arm's record), priced at the true cost.
        oracle_clean_qty = episode.optimal_order(float(clean_rec.payload["unit_cost"]))
        oracle_corrupt_qty = episode.optimal_order(float(corrupt_rec.payload["unit_cost"]))
        oracle_clean_cost = episode.realised_cost(oracle_clean_qty)
        oracle_corrupt_cost = episode.realised_cost(oracle_corrupt_qty)
        oracle_loss = oracle_corrupt_cost - oracle_clean_cost

        results.append(
            EpisodeResult(
                index=i,
                seed=seed,
                outcome=OUTCOME_OK,
                evidence_id_clean=clean_rec.evidence_id(),
                evidence_id_corrupt=corrupt_rec.evidence_id(),
                age_days=int(gt["age_days"]),
                true_unit_cost=float(gt["true_unit_cost"]),
                stale_unit_cost=float(gt["stale_unit_cost"]),
                clean_qty=clean_dec.order_qty,
                corrupt_qty=corrupt_dec.order_qty,
                clean_cost=clean_cost,
                corrupt_cost=corrupt_cost,
                loss=loss,
                material=is_material(loss, clean_cost, config.tau_m),
                oracle_clean_qty=oracle_clean_qty,
                oracle_corrupt_qty=oracle_corrupt_qty,
                oracle_clean_cost=oracle_clean_cost,
                oracle_corrupt_cost=oracle_corrupt_cost,
                oracle_loss=oracle_loss,
                oracle_material=is_material(oracle_loss, oracle_clean_cost, config.tau_m),
                marker_clean=mk_c.marker_score,
                marker_corrupt=mk_d.marker_score,
                doubt_clean=cj.doubt,
                doubt_corrupt=dj.doubt,
                flagged_corrupt=mk_d.flagged_data_problem,
                usd=usd,
                input_tokens=clean_dec.input_tokens + corrupt_dec.input_tokens,
                output_tokens=clean_dec.output_tokens + corrupt_dec.output_tokens,
            )
        )

    return _aggregate(
        config, results, failures, spend, n_refusals, n_errors, n_parse_failures, judge
    )


# An oracle order change smaller than this (in units) is treated as "no signal"
# for elasticity: dividing the agent's Δq by a near-zero oracle Δq is unstable and
# would swamp the median. Episodes below it are excluded from the elasticity ratio.
_ELASTICITY_MIN_ORACLE_DQ = 1.0


def _elasticity(results: list[EpisodeResult]) -> tuple[float, int]:
    """Median Δq_agent / Δq_oracle over episodes with a material oracle Δq (P4)."""
    ratios = [
        (r.corrupt_qty - r.clean_qty) / (r.oracle_corrupt_qty - r.oracle_clean_qty)
        for r in results
        if abs(r.oracle_corrupt_qty - r.oracle_clean_qty) >= _ELASTICITY_MIN_ORACLE_DQ
    ]
    if not ratios:
        return float("nan"), 0
    return statistics.median(ratios), len(ratios)


def _failure_autopsy(failures: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarise failed pairs: count, which arm failed, and the drift distribution."""
    by_arm = {"clean": 0, "corrupt": 0, "both": 0}
    for f in failures:
        by_arm[f["failed_arm"]] = by_arm.get(f["failed_arm"], 0) + 1
    drifts = [float(f["drift_frac"]) for f in failures if f["drift_frac"] == f["drift_frac"]]
    drift_summary = (
        {
            "median": statistics.median(drifts),
            "min": min(drifts),
            "max": max(drifts),
        }
        if drifts
        else {"median": float("nan"), "min": float("nan"), "max": float("nan")}
    )
    return {"n": len(failures), "by_arm": by_arm, "drift_frac": drift_summary}


def _aggregate(
    config: RunConfig,
    results: list[EpisodeResult],
    failures: list[dict[str, Any]],
    spend: float,
    n_refusals: int,
    n_errors: int,
    n_parse_failures: int,
    judge: Any,
) -> Phase0Result:
    losses = [r.loss for r in results]
    clean_costs = [r.clean_cost for r in results]
    adr = action_defect_rate(losses, clean_costs, config.tau_m)
    lq = quantiles(losses)
    loss_ci = paired_bootstrap_mean(losses) if losses else None

    # Oracle baseline (perfect metadata-blind solver).
    oracle_losses = [r.oracle_loss for r in results]
    oracle_clean_costs = [r.oracle_clean_cost for r in results]
    oracle_adr = action_defect_rate(oracle_losses, oracle_clean_costs, config.tau_m)
    oracle_lq = quantiles(oracle_losses)

    # Phase 0b: decision elasticity (P4) and clean-arm regret vs the oracle.
    elasticity_median, elasticity_n = _elasticity(results)
    clean_regrets = [r.clean_cost - r.oracle_clean_cost for r in results]
    rq = quantiles(clean_regrets)
    autopsy = _failure_autopsy(failures)

    # Behavioral discrimination: can markers / judge separate corrupted from clean?
    marker_pos = [r.marker_corrupt for r in results]
    marker_neg = [r.marker_clean for r in results]
    judge_pos = [r.doubt_corrupt for r in results]
    judge_neg = [r.doubt_clean for r in results]
    m_auc = bootstrap_auc(marker_pos, marker_neg)
    j_auc = bootstrap_auc(judge_pos, judge_neg)

    flagged_fraction = (
        sum(1 for r in results if r.flagged_corrupt) / len(results) if results else float("nan")
    )
    judge_val = validate(judge)

    # Primary discrimination signal for the kill criterion: the max of the two
    # behavioral AUCs (a defect is "detectable" if *either* channel catches it).
    primary_auc = max(m_auc.point, j_auc.point)
    verdict, detail = _kill_criterion(
        config, primary_auc, adr, flagged_fraction, len(results), config.n_episodes
    )

    return Phase0Result(
        config=asdict(config),
        config_hash=config.config_hash(),
        n_episodes=config.n_episodes,
        n_scored=len(results),
        n_refusals=n_refusals,
        n_errors=n_errors,
        n_parse_failures=n_parse_failures,
        adr=adr,
        oracle_adr=oracle_adr,
        loss_quantiles={"median": lq.median, "p90": lq.p90, "p99": lq.p99, "mean": lq.mean},
        oracle_loss_quantiles={
            "median": oracle_lq.median,
            "p90": oracle_lq.p90,
            "p99": oracle_lq.p99,
            "mean": oracle_lq.mean,
        },
        loss_ci=(
            {"point": loss_ci.point, "lo": loss_ci.lo, "hi": loss_ci.hi}
            if loss_ci
            else {"point": float("nan"), "lo": float("nan"), "hi": float("nan")}
        ),
        tail_ratio=lq.tail_ratio,
        heavy_tail_flag=lq.tail_ratio > 10.0,
        marker_auc={"point": m_auc.point, "lo": m_auc.lo, "hi": m_auc.hi},
        judge_auc={"point": j_auc.point, "lo": j_auc.lo, "hi": j_auc.hi},
        flagged_fraction=flagged_fraction,
        judge_validation=judge_val,
        kill_verdict=verdict,
        kill_detail=detail,
        spend_usd=spend,
        elasticity_median=elasticity_median,
        elasticity_n=elasticity_n,
        clean_regret={"median": rq.median, "p90": rq.p90, "mean": rq.mean},
        failure_autopsy=autopsy,
        episodes=[asdict(r) for r in results],
        failures=failures,
    )


def _run_is_valid(n_scored: int, n_episodes: int) -> bool:
    """DQ predicate on the run itself (Phase 0c): did enough pairs actually score?

    A data-quality gate applied to the verdict function — the same discipline the
    library applies to evidence, applied to its own output. If too few pairs
    reached a decision (truncation, parse failures, refusals), the metrics are not
    trustworthy and no scientific verdict may be read from them.
    """
    if n_episodes <= 0:
        return False
    return n_scored >= VALIDITY_MIN_SCORED_FRACTION * n_episodes


def _kill_criterion(
    config: RunConfig,
    primary_auc: float,
    adr: float,
    flagged_fraction: float,
    n_scored: int,
    n_episodes: int,
) -> tuple[str, str]:
    """Apply the Phase 0 kill criterion (brief §4), gated by the Phase 0c validity precondition.

    - **INVALID** (precondition, checked first): scored fraction < validity floor —
      returned regardless of the metrics.
    - *in trouble* if AUC >= kill_auc_trouble OR flagged_fraction >= kill_flag_trouble
    - *supported*  if AUC <= kill_auc_support AND ADR >= kill_adr_support
    - anything else: *ambiguous*
    """
    if not _run_is_valid(n_scored, n_episodes):
        return (
            "INVALID",
            f"only {n_scored}/{n_episodes} pairs scored "
            f"(< {VALIDITY_MIN_SCORED_FRACTION:.0%} validity floor); metrics are not "
            "trustworthy — fix instrumentation and re-run before reading any verdict.",
        )
    in_trouble = (
        primary_auc >= config.kill_auc_trouble or flagged_fraction >= config.kill_flag_trouble
    )
    supported = primary_auc <= config.kill_auc_support and adr >= config.kill_adr_support
    if in_trouble:
        return (
            "IN_TROUBLE",
            f"AUC={primary_auc:.3f} (>= {config.kill_auc_trouble}) or "
            f"flagged={flagged_fraction:.2%} (>= {config.kill_flag_trouble:.0%}).",
        )
    if supported:
        return (
            "SUPPORTED",
            f"AUC={primary_auc:.3f} (<= {config.kill_auc_support}) and "
            f"ADR={adr:.2%} (>= {config.kill_adr_support:.0%}).",
        )
    return (
        "AMBIGUOUS",
        f"AUC={primary_auc:.3f}, ADR={adr:.2%}, flagged={flagged_fraction:.2%} "
        "fall between the thresholds — report and stop.",
    )
