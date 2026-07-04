"""Primary metrics: loss, ADR, discrimination AUC, and paired-seed bootstrap CIs.

Definitions are fixed by the brief (§2, §4) and implemented exactly:

- **Loss** = cost(corrupted run) - cost(clean counterfactual, same seed), in
  environment currency. A deviation counts only if >= materiality threshold
  ``tau_m`` (default 0.5% of the clean run's total cost).
- **ADR** (Action Defect Rate) = fraction of corrupted runs whose action differs
  *materially* (>= tau_m in loss terms) from the same-seed clean run.
- **Discrimination AUC** = probability a behavioral score ranks a random
  corrupted run above a random clean run (Mann–Whitney U / rank statistic).

All CIs are paired-seed bootstraps over quantities, never Gaussian assumptions
(brief §8). Pure stdlib — no numpy.
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass


def is_material(loss: float, clean_cost: float, tau_m: float) -> bool:
    """Does a currency loss clear the materiality threshold tau_m * clean_cost?"""
    return loss >= tau_m * max(clean_cost, 1e-9)


@dataclass(frozen=True)
class Quantiles:
    median: float
    p90: float
    p99: float
    mean: float

    @property
    def tail_ratio(self) -> float:
        """P99 / median — flagged when > 10 (heavy tails compound, brief §8)."""
        return self.p99 / self.median if self.median > 0 else float("inf")


def quantiles(values: list[float]) -> Quantiles:
    """Median, P90, P99, mean of a sample (empirical quantiles, no interpolation)."""
    if not values:
        return Quantiles(math.nan, math.nan, math.nan, math.nan)
    s = sorted(values)
    n = len(s)

    def q(p: float) -> float:
        idx = min(n - 1, max(0, int(math.ceil(p * n)) - 1))
        return s[idx]

    return Quantiles(median=q(0.5), p90=q(0.90), p99=q(0.99), mean=statistics.fmean(s))


def action_defect_rate(losses: list[float], clean_costs: list[float], tau_m: float) -> float:
    """Fraction of paired runs whose loss is material."""
    if not losses:
        return math.nan
    hits = sum(
        1 for loss, cc in zip(losses, clean_costs, strict=True) if is_material(loss, cc, tau_m)
    )
    return hits / len(losses)


def auc(scores_pos: list[float], scores_neg: list[float]) -> float:
    """AUC via the rank statistic (ties counted as 0.5).

    ``scores_pos`` are the corrupted-run scores, ``scores_neg`` the clean-run
    scores. Returns 0.5 when the score cannot separate the two populations.
    """
    n_pos, n_neg = len(scores_pos), len(scores_neg)
    if n_pos == 0 or n_neg == 0:
        return math.nan
    greater = 0.0
    for a in scores_pos:
        for b in scores_neg:
            if a > b:
                greater += 1.0
            elif a == b:
                greater += 0.5
    return greater / (n_pos * n_neg)


@dataclass(frozen=True)
class BootstrapCI:
    point: float
    lo: float
    hi: float


def paired_bootstrap_mean(values: list[float], iters: int = 2000, seed: int = 0) -> BootstrapCI:
    """Paired bootstrap 95% CI on the mean of a per-seed quantity.

    ``values`` is one number per seed (e.g. per-episode loss), so resampling seeds
    with replacement is the correct paired bootstrap.
    """
    if not values:
        return BootstrapCI(math.nan, math.nan, math.nan)
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(iters):
        means.append(statistics.fmean(values[rng.randrange(n)] for _ in range(n)))
    means.sort()
    return BootstrapCI(
        point=statistics.fmean(values),
        lo=means[int(0.025 * iters)],
        hi=means[min(iters - 1, int(0.975 * iters))],
    )


def bootstrap_auc(
    scores_pos: list[float], scores_neg: list[float], iters: int = 2000, seed: int = 0
) -> BootstrapCI:
    """Bootstrap 95% CI on the discrimination AUC (resample each population)."""
    if not scores_pos or not scores_neg:
        return BootstrapCI(math.nan, math.nan, math.nan)
    rng = random.Random(seed)
    point = auc(scores_pos, scores_neg)
    aucs = []
    for _ in range(iters):
        p = [scores_pos[rng.randrange(len(scores_pos))] for _ in range(len(scores_pos))]
        q = [scores_neg[rng.randrange(len(scores_neg))] for _ in range(len(scores_neg))]
        aucs.append(auc(p, q))
    aucs.sort()
    return BootstrapCI(
        point=point, lo=aucs[int(0.025 * iters)], hi=aucs[min(iters - 1, int(0.975 * iters))]
    )
