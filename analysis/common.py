"""Shared, deterministic helpers for the post-hoc analytical layer.

Every function here is a $0 recomputation from committed artifacts: the frozen substrate
(``sarc_dq.substrate``, seeded), the frozen injectors (``sarc_dq.taxonomy``), and the
committed ``results/<exp>-live`` summaries read via ``git show``. No API, no reruns, no
modification of any committed value. The analysis explains the measurements; it never
replaces them.
"""

from __future__ import annotations

import json
import random
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sarc_dq.config import TAU_M_DEFAULT
from sarc_dq.substrate import (
    corruption_decision,
    episode_seed,
    make_episode,
    stratified_corrupt_indices,
)
from sarc_dq.taxonomy import get, registered

ROOT = Path(__file__).resolve().parents[1]
BASE_SEED = 20260707
N_EPISODES = 100
FIXED_N = 25
RATES = (0.02, 0.05, 0.10, 0.20)
TAU_M = TAU_M_DEFAULT

# The pinned committed result branches (mirror EXPERIMENT_STATUS.md / ingest_results.py).
BRANCHES = {
    "h1-full": "results/h1-full-live",
    "h1-ladder": "results/h1-ladder-live",
    "h2-detection": "results/h2-detection-live",
    "h3-frontier": "results/h3-frontier-live",
    "h4-recovery": "results/h4-recovery-live",
}

# Metadata channel each corruption class lives in, and the v1 predicate that covers it
# (None = no predicate in v1 = a declared coverage gap). Grounds the coverage accounting
# and the predicate ablations; taken from the frozen taxonomy/gate design.
CLASS_PREDICATE = {
    "stale_master_data": "freshness",
    "superseded_golden_record": "freshness",  # supersession = a freshness/version signal
    "schema_drift": "schema",
    "missing_mandatory_field": "completeness",
    "cross_source_contradiction": "consistency",
    "duplicate_vendor_conflicting_terms": "consistency",
    "silent_unit_change": None,  # v1.1 unit-consistency gap
    "plausible_outlier": None,  # v1.1 outlier gap
}


def load_summary(exp: str) -> dict[str, Any]:
    """Committed full result summary for ``exp`` (read straight from its branch)."""
    branch = BRANCHES[exp]
    out = subprocess.run(
        ["git", "show", f"origin/{branch}:reports/exp/{exp}_summary.json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    data: dict[str, Any] = json.loads(out.stdout)
    return data


@dataclass(frozen=True)
class OracleOutcome:
    """The model-independent (oracle) decision geometry for one corrupted episode."""

    index: int
    true_cost: float
    seen_cost: float
    q_clean: float
    q_corrupt: float
    clean_cost: float
    paired_loss: float  # realised_cost(q_corrupt) - realised_cost(q_clean), same demand
    material: bool


def corrupted_indices(rate: float, *, fixed_n: bool) -> list[int]:
    """Exact corrupted episode indices for a cell (reproduces the committed sampler)."""
    if fixed_n:
        return sorted(stratified_corrupt_indices(BASE_SEED, rate, N_EPISODES, FIXED_N))
    return [
        i
        for i in range(N_EPISODES)
        if corruption_decision(BASE_SEED, i, rate, n_episodes=N_EPISODES, fixed_n=None)[1]
    ]


def oracle_cell(cls_name: str, rate: float, *, fixed_n: bool = True) -> list[OracleOutcome]:
    """Oracle conversion for every corrupted episode of a (class, rate) cell.

    The 'oracle' agent acts on the newsvendor optimum for the price it is *shown* (the
    corrupted payload), so its paired loss and materiality are a closed-form property of
    the substrate and the injected corruption --- independent of any LLM. This is the
    analytical conversion the paper compares against the measured agent ADR.
    """
    cls = get(cls_name)
    out: list[OracleOutcome] = []
    for i in corrupted_indices(rate, fixed_n=fixed_n):
        ep = make_episode(episode_seed(BASE_SEED, i), i)
        corr_seed, corrupt = corruption_decision(
            BASE_SEED, i, rate, n_episodes=N_EPISODES, fixed_n=FIXED_N if fixed_n else None
        )
        if not corrupt:
            continue
        inj = cls.inject(ep.clean_price_record(), ep, random.Random(corr_seed + 1))
        seen = inj.evidence_set()[0].payload.get("unit_cost")
        if not isinstance(seen, (int, float)):
            # schema/missing corruptions carry no numeric price: the priced decision
            # cannot form, so there is no conversion geometry (matches the measured 0 ADR).
            out.append(
                OracleOutcome(i, ep.true_unit_cost, float("nan"), 0.0, 0.0, 0.0, 0.0, False)
            )
            continue
        c_true = ep.true_unit_cost
        q_clean = ep.optimal_order(c_true)
        q_corr = ep.optimal_order(float(seen))
        clean_cost = ep.realised_cost(q_clean)
        loss = ep.realised_cost(q_corr) - clean_cost
        out.append(
            OracleOutcome(
                i,
                c_true,
                float(seen),
                q_clean,
                q_corr,
                clean_cost,
                loss,
                loss >= TAU_M * clean_cost,
            )
        )
    return out


def oracle_conversion(cls_name: str, rate: float, *, fixed_n: bool = True) -> float:
    """Predicted oracle conversion probability for a (class, rate) cell."""
    cells = oracle_cell(cls_name, rate, fixed_n=fixed_n)
    return sum(o.material for o in cells) / len(cells) if cells else 0.0


def all_classes() -> list[str]:
    return list(registered())
