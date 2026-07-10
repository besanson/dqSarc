"""Six-arm harness over the taxonomy — the engine GIGO-Bench freezes (Part 3).

Arms behind one switch (brief §6):

- **A** no gate (baseline);
- **B** prompt advisory ("verify data quality"). In the deterministic mock this is
  a no-op (the mock decision ignores the prompt); its value shows only live.
- **C** critic with a **payload-only view** (⟨CRITIC_MODEL⟩ = claude-opus-4-8). The
  payload-only view is the H2 *design*, not a shortcut: the mock critic can flag a
  payload-visible defect but structurally cannot see a metadata-borne one.
- **D** DQ Pre-Action Gate (metadata access, Part-1 predicates) with
  block / degrade / escalate / quarantine-and-substitute from the governed buffer.
- **E** oracle clean source (upper bound; loss 0).
- **F(v)** upstream cleaning at velocity ``v`` — a fraction ``v`` of defects fixed
  before the agent acts.

Deterministic mock throughout, so the whole class × rate × arm matrix runs in CI
at $0. The mock "agent" is the newsvendor optimum on the price it is *led to
believe*; each arm decides what that believed price is and whether the action
executes at all.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from sarc_dq.config import TAU_M_DEFAULT
from sarc_dq.dq_spec import load_spec
from sarc_dq.gate import GovernedBuffer, PreActionGate
from sarc_dq.metrics import quantiles
from sarc_dq.records import EvidenceRecord
from sarc_dq.substrate import Episode, corruption_decision, episode_seed, make_episode
from sarc_dq.taxonomy import get as get_class

ARMS = ("A", "B", "C", "D", "E", "F")
RATES = (0.02, 0.05, 0.10, 0.20)
_FALLBACK_PRICE = 15.0  # truth-free default when the site field is absent/untyped


def split_of(seed: int) -> str:
    """Workload-level split (train/calibration/test) — trajectories never cross it."""
    return ("train", "calibration", "test")[seed % 3]


def _read_price(record: EvidenceRecord) -> float | None:
    v = record.payload.get("unit_cost")
    return float(v) if isinstance(v, (int, float)) else None


def _critic_detects_payload_only(evidence: Sequence[EvidenceRecord]) -> bool:
    """Arm-C mock critic: sees payload only, so catches only payload-visible defects."""
    for r in evidence:  # schema drift / missing field: site field absent or non-numeric
        if not isinstance(r.payload.get("unit_cost"), (int, float)):
            return True
    by_sku: dict[str, set[float]] = {}
    for r in evidence:  # duplicate / cross-source: same key, different payload value
        p = r.payload.get("unit_cost")
        if isinstance(p, (int, float)):
            by_sku.setdefault(str(r.payload.get("sku")), set()).add(round(float(p), 6))
    return any(len(v) > 1 for v in by_sku.values())


@dataclass(frozen=True)
class ArmOutcome:
    arm: str
    completed: bool  # did an autonomous action execute?
    detected: bool  # did the arm flag the defect?
    believed_price: float | None
    loss: float | None  # realised currency loss vs the same-seed clean counterfactual
    material: bool
    response: str
    substituted: bool
    evidence_ids: tuple[str, ...]


def _decide(believed: float | None, episode: Episode) -> tuple[float, float]:
    """(realised_cost, loss vs clean) for the mock newsvendor decision on a price."""
    price = believed if believed is not None else _FALLBACK_PRICE
    order = episode.optimal_order(price)
    clean_cost = episode.realised_cost(episode.optimal_order(episode.true_unit_cost))
    return episode.realised_cost(order), episode.realised_cost(order) - clean_cost


def apply_arm(
    arm: str,
    episode: Episode,
    evidence: Sequence[EvidenceRecord],
    *,
    corrupted: bool,
    gate: PreActionGate,
    velocity: float,
    rng: random.Random,
    tau_m: float,
) -> ArmOutcome:
    """Run one arm on one episode's evidence set. Deterministic given ``rng``."""
    primary = evidence[0]
    true_p = episode.true_unit_cost
    eids = tuple(r.evidence_id() for r in evidence)
    clean_cost = episode.realised_cost(episode.optimal_order(true_p))

    def out(
        completed: bool,
        detected: bool,
        believed: float | None,
        response: str,
        substituted: bool = False,
    ) -> ArmOutcome:
        if not completed:
            return ArmOutcome(arm, False, detected, None, None, False, response, substituted, eids)
        _, loss = _decide(believed, episode)
        return ArmOutcome(
            arm,
            True,
            detected,
            believed,
            loss,
            loss >= tau_m * clean_cost,
            response,
            substituted,
            eids,
        )

    if arm in ("A", "B"):
        return out(True, False, _read_price(primary), "admit")
    if arm == "C":
        if _critic_detects_payload_only(evidence):
            return out(False, True, None, "block")
        return out(True, False, _read_price(primary), "admit")
    if arm == "D":
        d = gate.evaluate(evidence)
        if not d.admitted:
            return out(False, True, None, d.response)
        if d.substituted_value is not None:
            return out(True, True, d.substituted_value, "quarantine_substitute", substituted=True)
        if d.response == "degrade":
            return out(True, True, _FALLBACK_PRICE, "degrade")
        return out(True, d.detected, _read_price(primary), d.response)
    if arm == "E":
        return out(True, False, true_p, "oracle")
    if arm == "F":
        cleaned = corrupted and rng.random() < velocity
        return out(
            True,
            False,
            true_p if cleaned else _read_price(primary),
            "clean" if cleaned else "admit",
        )
    raise ValueError(f"unknown arm {arm!r}")


@dataclass
class ConditionResult:
    corruption_class: str
    rate: float
    arm: str
    n_episodes: int
    n_corrupted: int
    adr: float  # material loss among corrupted+completed
    detection_rate: float  # among corrupted
    false_block_rate: float  # among clean
    completion_rate: float  # among all
    loss_mean_corrupted: float  # mean over corrupted+completed
    loss_eff_corrupted: float  # mean over ALL corrupted (blocked = avoided = 0)
    loss_quantiles: dict[str, float]
    recovery_ratio: float | None  # filled at the matrix level (needs arms A & E)
    outcomes: list[dict[str, Any]] = field(default_factory=list)


def run_condition(
    corruption_class: str,
    rate: float,
    arm: str,
    *,
    n_episodes: int = 100,
    base_seed: int = 20260707,
    tau_m: float = TAU_M_DEFAULT,
    velocity: float = 0.5,
    gate: PreActionGate | None = None,
) -> ConditionResult:
    cls = get_class(corruption_class)
    # Load the spec ONCE per condition (YAML parse is expensive); only the per-episode
    # governed buffer changes below.
    spec = gate.spec if gate is not None else load_spec()
    outcomes: list[ArmOutcome] = []
    corrupted_flags: list[bool] = []

    for i in range(n_episodes):
        seed = episode_seed(base_seed, i)
        episode = make_episode(seed, i)
        clean_rec = episode.clean_price_record()
        # Rate-dependent corruption draw so each (class, rate) cell is an independent
        # sample (not the nested/duplicate cells a rate-independent draw produced).
        corr_seed, corrupt = corruption_decision(base_seed, i, rate)
        if corrupt:
            inj = cls.inject(clean_rec, episode, random.Random(corr_seed + 1))
            evidence: tuple[EvidenceRecord, ...] = inj.evidence_set()
        else:
            evidence = (clean_rec,)
        # Governed buffer: a downstream clean cache keyed by SKU (never a source store).
        buf = GovernedBuffer({episode.sku: episode.true_unit_cost})
        g = PreActionGate(spec, buf)
        outcomes.append(
            apply_arm(
                arm,
                episode,
                evidence,
                corrupted=corrupt,
                gate=g,
                velocity=velocity,
                rng=random.Random(seed + 2),
                tau_m=tau_m,
            )
        )
        corrupted_flags.append(corrupt)

    return _aggregate_condition(corruption_class, rate, arm, outcomes, corrupted_flags, n_episodes)


def _aggregate_condition(
    corruption_class: str,
    rate: float,
    arm: str,
    outcomes: list[ArmOutcome],
    corrupted: list[bool],
    n_episodes: int,
) -> ConditionResult:
    corr = [(o, c) for o, c in zip(outcomes, corrupted, strict=True) if c]
    clean = [(o, c) for o, c in zip(outcomes, corrupted, strict=True) if not c]
    corr_completed = [o for o, _ in corr if o.completed]
    losses = [o.loss for o in corr_completed if o.loss is not None]

    def frac(num: int, den: int) -> float:
        return num / den if den else 0.0

    adr = frac(sum(1 for o in corr_completed if o.material), len(corr_completed))
    detection = frac(sum(1 for o, _ in corr if o.detected), len(corr))
    false_block = frac(sum(1 for o, _ in clean if not o.completed), len(clean))
    completion = frac(sum(1 for o in outcomes if o.completed), n_episodes)
    loss_mean = sum(losses) / len(losses) if losses else 0.0
    # Effective loss: a blocked/escalated corrupted episode avoids the wrong action
    # (loss 0). Averaged over ALL corrupted episodes — the basis for recovery.
    eff = [(o.loss if o.completed and o.loss is not None else 0.0) for o, _ in corr]
    loss_eff = sum(eff) / len(eff) if eff else 0.0
    lq = quantiles(losses) if losses else quantiles([0.0])

    return ConditionResult(
        corruption_class,
        rate,
        arm,
        n_episodes,
        len(corr),
        adr,
        detection,
        false_block,
        completion,
        loss_mean,
        loss_eff,
        {"median": lq.median, "p90": lq.p90, "p99": lq.p99, "mean": lq.mean},
        None,
        [_outcome_row(o, c) for o, c in zip(outcomes, corrupted, strict=True)],
    )


def run_matrix(
    *,
    classes: Sequence[str] | None = None,
    rates: Sequence[float] = RATES,
    arms: Sequence[str] = ARMS,
    n_episodes: int = 100,
    base_seed: int = 20260707,
    tau_m: float = TAU_M_DEFAULT,
    velocity: float = 0.5,
    keep_outcomes: bool = False,
) -> dict[str, Any]:
    """Run the class × rate × arm matrix (deterministic mock). Fills recovery for D.

    Returns a nested summary ``{class: {rate: {arm: metrics}}}`` plus a config hash.
    Recovery ratio (H4) for arm D is ``(effA - effD)/(effA - effE)`` with effE ≈ 0.
    """
    from sarc_dq.taxonomy import registered

    classes = list(classes) if classes is not None else registered()
    out: dict[str, Any] = {}
    for cls in classes:
        out[cls] = {}
        for rate in rates:
            per_arm: dict[str, ConditionResult] = {
                arm: run_condition(
                    cls,
                    rate,
                    arm,
                    n_episodes=n_episodes,
                    base_seed=base_seed,
                    tau_m=tau_m,
                    velocity=velocity,
                )
                for arm in arms
            }
            eff_a = per_arm["A"].loss_eff_corrupted if "A" in per_arm else None
            eff_e = per_arm["E"].loss_eff_corrupted if "E" in per_arm else 0.0
            if "D" in per_arm and eff_a is not None and (eff_a - eff_e) > 1e-9:
                per_arm["D"].recovery_ratio = (eff_a - per_arm["D"].loss_eff_corrupted) / (
                    eff_a - eff_e
                )
            out[cls][f"{rate:.2f}"] = {
                arm: _condition_summary(r, keep_outcomes) for arm, r in per_arm.items()
            }
    return {
        "config": {
            "n_episodes": n_episodes,
            "base_seed": base_seed,
            "tau_m": tau_m,
            "velocity": velocity,
            "rates": list(rates),
            "arms": list(arms),
        },
        "matrix": out,
    }


def _condition_summary(r: ConditionResult, keep_outcomes: bool) -> dict[str, Any]:
    d: dict[str, Any] = {
        "adr": r.adr,
        "detection_rate": r.detection_rate,
        "false_block_rate": r.false_block_rate,
        "completion_rate": r.completion_rate,
        "loss_mean_corrupted": r.loss_mean_corrupted,
        "loss_eff_corrupted": r.loss_eff_corrupted,
        "loss_quantiles": r.loss_quantiles,
        "recovery_ratio": r.recovery_ratio,
        "n_corrupted": r.n_corrupted,
    }
    if keep_outcomes:
        d["outcomes"] = r.outcomes
    return d


def _outcome_row(o: ArmOutcome, corrupted: bool) -> dict[str, Any]:
    return {
        "arm": o.arm,
        "corrupted": corrupted,
        "completed": o.completed,
        "detected": o.detected,
        "response": o.response,
        "substituted": o.substituted,
        "loss": o.loss,
        "material": o.material,
        "evidence_ids": list(o.evidence_ids),
    }
