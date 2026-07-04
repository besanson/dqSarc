"""Substrate: determinism, newsvendor optimality, and the paired-loss property."""

from __future__ import annotations

import math

from sarc_dq.substrate import _norm_ppf, make_episode


def test_norm_ppf_known_values() -> None:
    assert math.isclose(_norm_ppf(0.5), 0.0, abs_tol=1e-6)
    assert math.isclose(_norm_ppf(0.975), 1.959964, abs_tol=1e-4)
    assert math.isclose(_norm_ppf(0.025), -1.959964, abs_tol=1e-4)


def test_episode_is_deterministic_per_seed() -> None:
    a = make_episode(seed=123, index=0)
    b = make_episode(seed=123, index=0)
    assert a == b


def test_critical_ratio_interior_and_monotone() -> None:
    ep = make_episode(seed=7, index=3)
    # c < s by construction, so CR is strictly interior.
    cr = ep.critical_ratio(ep.true_unit_cost)
    assert 0.0 < cr < 1.0
    # A higher believed unit cost lowers the critical ratio (order less).
    assert ep.critical_ratio(ep.true_unit_cost * 1.5) < cr


def test_true_price_order_is_cost_minimising() -> None:
    """The order computed from the TRUE cost must not be beaten by nearby orders."""
    ep = make_episode(seed=42, index=1)
    q_star = ep.optimal_order(ep.true_unit_cost)
    # q* minimises EXPECTED cost; on a single realised demand it need not be the
    # per-sample minimum, so we check the expectation via a demand average.
    for delta in (-50.0, -10.0, 10.0, 50.0):
        # Perturbing the order and re-pricing at true cost should not systematically
        # help: check the expected cost over the demand distribution instead.
        assert _expected_cost(ep, q_star) <= _expected_cost(ep, q_star + delta) + 1e-6


def _expected_cost(ep: object, q: float) -> float:
    """Monte-Carlo expected cost of order q under the episode's demand law."""
    import random as _r

    from sarc_dq.substrate import Episode

    assert isinstance(ep, Episode)
    rng = _r.Random(999)
    total = 0.0
    n = 4000
    for _ in range(n):
        d = max(0.0, rng.gauss(ep.mean_demand, ep.sigma_demand))
        proc = ep.true_unit_cost * q
        hold = ep.holding_cost * max(q - d, 0.0)
        stock = ep.stockout_penalty * max(d - q, 0.0)
        total += proc + hold + stock
    return total / n


def test_wrong_price_never_reduces_expected_cost() -> None:
    """Ordering off a wrong believed price can only match or raise expected cost."""
    ep = make_episode(seed=8, index=2)
    q_true = ep.optimal_order(ep.true_unit_cost)
    q_wrong = ep.optimal_order(ep.true_unit_cost * 0.6)  # believing a cheaper price
    assert _expected_cost(ep, q_wrong) >= _expected_cost(ep, q_true) - 1e-6
