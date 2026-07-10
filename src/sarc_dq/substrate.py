"""The IBP replenishment substrate: a priced single-period newsvendor decision.

Green SARC's IBP benchmark is a pure token-cost *simulation* — no decision
content, no LLM. SARC-DQ needs the opposite: a decision whose **quality depends
on a data value that can be corrupted**, priced in currency, so a wrong input
converts into a wrong action converts into a measurable loss.

We use the textbook single-period (newsvendor) replenishment decision, which the
IBP domain already prices via holding cost and stockout penalty (brief §2):

    cost(q; c, D) = c*q            # procurement at unit cost c
                  + h*max(q-D, 0)  # holding cost on leftovers
                  + s*max(D-q, 0)  # stockout penalty on shortage

The cost-minimising order solves ``F(q*) = (s - c) / (h + s)`` — so the optimal
order quantity depends on the **unit cost c**. That is the field the Phase 0
injector staleness corrupts. The world always charges the *true* cost c; only
the agent's *belief* about c is corrupted. A stale c ⇒ wrong critical ratio ⇒
wrong q ⇒ loss that is **non-negative in expectation** versus the clean
counterfactual. It is *not* non-negative on every seed: loss is scored on one
realised demand D, so a wrong order can occasionally get lucky (negative loss).
That is exactly why loss is reported as a *distribution* (median, P90, P99, mean
CI), not a point estimate.

Deterministic per seed: the realised demand D is drawn from a seeded RNG, so the
corrupted episode and its clean twin share the same D and the same true c — every
comparison is paired (brief §4).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from sarc_dq.records import EvidenceRecord, RecordMetadata


def _norm_cdf(x: float) -> float:
    """Standard normal CDF via the error function (stdlib only)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_ppf(p: float) -> float:
    """Inverse standard normal CDF (Acklam's rational approximation).

    Accurate to ~1.15e-9 over the open interval; sufficient for order quantities.
    Kept dependency-free (no scipy) to preserve the zero-dependency core.
    """
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in the open interval (0, 1)")
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00, 3.754408661907416e00]
    p_low = 0.02425
    p_high = 1.0 - p_low
    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    if p <= p_high:
        q = p - 0.5
        r = q * q
        return (
            (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
            * q
            / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
        )
    q = math.sqrt(-2.0 * math.log(1.0 - p))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
        (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
    )


@dataclass(frozen=True)
class Episode:
    """One replenishment decision: parameters, the truth, and the realised demand.

    All fields are drawn deterministically from the episode seed. ``true_unit_cost``
    is the cost the world charges; the *record* the agent reads may carry a stale
    value instead (that is the injector's job).
    """

    episode_id: str
    sku: str
    mean_demand: float
    sigma_demand: float
    holding_cost: float  # h — per leftover unit
    stockout_penalty: float  # s — per short unit
    true_unit_cost: float  # c — the world's true price
    as_of_day: int  # simulated day the true price was set
    now_day: int  # simulated "today"
    realised_demand: float

    def critical_ratio(self, unit_cost: float) -> float:
        """Newsvendor critical ratio (s - c) / (h + s) for a believed unit cost."""
        cr = (self.stockout_penalty - unit_cost) / (self.holding_cost + self.stockout_penalty)
        return min(max(cr, 1e-6), 1.0 - 1e-6)

    def optimal_order(self, believed_unit_cost: float) -> float:
        """Cost-minimising order quantity given a *believed* unit cost."""
        z = _norm_ppf(self.critical_ratio(believed_unit_cost))
        return max(0.0, self.mean_demand + self.sigma_demand * z)

    def realised_cost(self, order_qty: float) -> float:
        """Currency cost of ordering ``order_qty``, priced at the TRUE unit cost."""
        d = self.realised_demand
        procurement = self.true_unit_cost * order_qty
        holding = self.holding_cost * max(order_qty - d, 0.0)
        stockout = self.stockout_penalty * max(d - order_qty, 0.0)
        return procurement + holding + stockout

    def clean_price_record(self) -> EvidenceRecord:
        """The uncorrupted price record: fresh, true value, current metadata."""
        return EvidenceRecord(
            record_id=f"{self.sku}:price",
            payload={
                "sku": self.sku,
                "unit_cost": round(self.true_unit_cost, 4),
                "currency": "USD",
            },
            metadata=RecordMetadata(
                source="erp.pricing",
                as_of_day=self.now_day,  # fresh: as-of == today
                retrieved_day=self.now_day,
                version=1,
            ),
            ground_truth={
                "true_unit_cost": self.true_unit_cost,
                "corrupted": False,
                "corruption_class": None,
            },
        )


def make_episode(seed: int, index: int) -> Episode:
    """Draw one replenishment episode deterministically from a seed.

    Parameter ranges are chosen so the critical ratio stays interior (c < s) and
    a plausible 90–180-day-stale price moves the order enough to matter, without
    the environment being pathological. These are Phase 0 defaults, not tuned on
    any evaluation outcome (brief §11: nothing tuned on eval seeds).
    """
    rng = random.Random(seed)
    mean_demand = rng.uniform(400.0, 1200.0)
    sigma_demand = mean_demand * rng.uniform(0.15, 0.35)
    true_unit_cost = rng.uniform(8.0, 22.0)
    # Stockout penalty comfortably above unit cost so CR is interior and positive.
    stockout_penalty = true_unit_cost * rng.uniform(2.5, 5.0)
    holding_cost = true_unit_cost * rng.uniform(0.15, 0.45)
    now_day = 2000 + index
    as_of_day = now_day  # true price is current; staleness is injected downstream
    realised_demand = max(0.0, rng.gauss(mean_demand, sigma_demand))
    return Episode(
        episode_id=f"ep{index:04d}",
        sku=f"SKU-{rng.randint(10000, 99999)}",
        mean_demand=mean_demand,
        sigma_demand=sigma_demand,
        holding_cost=holding_cost,
        stockout_penalty=stockout_penalty,
        true_unit_cost=true_unit_cost,
        as_of_day=as_of_day,
        now_day=now_day,
        realised_demand=realised_demand,
    )


def episode_seed(base_seed: int, i: int) -> int:
    """Rate-independent per-episode seed (shared episode population across rates)."""
    return (base_seed * 1_000_003 + i) & 0x7FFFFFFF


def _corr_seed(base_seed: int, i: int, rate: float) -> int:
    rate_key = int(round(rate * 1_000_000))
    return (episode_seed(base_seed, i) * 2_654_435_761 + rate_key) & 0x7FFFFFFF


def stratified_corrupt_indices(
    base_seed: int, rate: float, n_episodes: int, fixed_n: int
) -> frozenset[int]:
    """The exact ``fixed_n`` corrupted episode indices for a fixed-count cell.

    Used when ``rate`` is a **stratification label** rather than a prevalence: each
    cell corrupts exactly ``fixed_n`` episodes (chosen by a rate-seeded shuffle), so
    per-corrupted metrics (ADR, detection) have a stable, equal n across cells. The
    per-rate seed keeps the four label cells independent (not the same episodes).
    """
    rate_key = int(round(rate * 1_000_000))
    idxs = list(range(n_episodes))
    random.Random((base_seed * 40_503 + rate_key) & 0x7FFFFFFF).shuffle(idxs)
    return frozenset(idxs[: min(fixed_n, n_episodes)])


def corruption_decision(
    base_seed: int,
    i: int,
    rate: float,
    *,
    n_episodes: int | None = None,
    fixed_n: int | None = None,
) -> tuple[int, bool]:
    """Corruption draw for episode ``i``. Returns ``(corr_seed, corrupt)``.

    Default (``fixed_n=None``): a rate-DEPENDENT Bernoulli draw at probability ``rate``
    — so each ``(class, rate)`` cell is an INDEPENDENT sample. A rate-independent draw
    (the pre-fix behaviour) made the corrupted sets nested across rates and byte-
    identical whenever no draw fell between two adjacent rates (0.02 and 0.05 shared
    the same five episodes). The episode itself (``episode_seed``) stays rate-
    independent, so the demand population is shared while the corruption mask is not.

    Fixed-count (``fixed_n`` set, needs ``n_episodes``): exactly ``fixed_n`` episodes
    per cell are corrupted (rate as a stratification label). Used by the H1/H2 re-runs
    so ADR/detection rest on an equal n per cell (addendum 2026-07-09).
    """
    corr_seed = _corr_seed(base_seed, i, rate)
    if fixed_n is not None:
        if n_episodes is None:
            raise ValueError("fixed_n requires n_episodes")
        corrupt = i in stratified_corrupt_indices(base_seed, rate, n_episodes, fixed_n)
    else:
        corrupt = random.Random(corr_seed).random() < rate
    return corr_seed, corrupt
