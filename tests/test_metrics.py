"""Metrics: ADR, AUC, quantiles, and bootstrap CIs."""

from __future__ import annotations

import math

from sarc_dq.metrics import (
    action_defect_rate,
    auc,
    bootstrap_auc,
    is_material,
    paired_bootstrap_mean,
    quantiles,
)


def test_is_material_threshold() -> None:
    assert is_material(loss=6.0, clean_cost=1000.0, tau_m=0.005)  # 0.6% >= 0.5%
    assert not is_material(loss=4.0, clean_cost=1000.0, tau_m=0.005)  # 0.4% < 0.5%


def test_adr_counts_only_material() -> None:
    losses = [6.0, 4.0, 100.0, 0.0]
    clean = [1000.0, 1000.0, 1000.0, 1000.0]
    # material: 6.0 (0.6%) and 100.0 (10%) -> 2/4
    assert action_defect_rate(losses, clean, tau_m=0.005) == 0.5


def test_auc_separable_and_random() -> None:
    assert auc([3.0, 4.0, 5.0], [0.0, 1.0, 2.0]) == 1.0  # perfectly separable
    assert auc([1.0, 1.0], [1.0, 1.0]) == 0.5  # all ties -> chance


def test_auc_identical_populations_is_half() -> None:
    xs = [0.0, 1.0, 2.0, 3.0]
    assert auc(xs, list(xs)) == 0.5


def test_quantiles_and_tail_ratio() -> None:
    q = quantiles([1.0] * 99 + [1000.0])
    assert q.median == 1.0
    assert q.p99 == 1.0  # 99th value is still 1.0
    assert q.tail_ratio <= 10.0
    heavy = quantiles([1.0] * 50 + [100.0] * 50)
    assert heavy.tail_ratio > 10.0


def test_paired_bootstrap_ci_brackets_mean() -> None:
    values = [float(i) for i in range(100)]
    ci = paired_bootstrap_mean(values, iters=500, seed=1)
    assert math.isclose(ci.point, 49.5)
    assert ci.lo <= ci.point <= ci.hi


def test_bootstrap_auc_point_matches_auc() -> None:
    pos = [2.0, 3.0, 4.0]
    neg = [0.0, 1.0, 1.5]
    ci = bootstrap_auc(pos, neg, iters=500, seed=1)
    assert ci.point == auc(pos, neg)
    assert ci.lo <= ci.point <= ci.hi
