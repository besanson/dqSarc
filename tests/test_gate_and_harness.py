"""DQ Pre-Action Gate + six-arm harness: responses, recovery, H2 asymmetry."""

from __future__ import annotations

import random

from sarc_dq.gate import GovernedBuffer, PreActionGate
from sarc_dq.harness import ARMS, run_condition, run_matrix
from sarc_dq.substrate import make_episode
from sarc_dq.taxonomy import get


def _evidence(cls_name: str, seed: int = 1):
    ep = make_episode(seed, 0)
    inj = get(cls_name).inject(ep.clean_price_record(), ep, random.Random(seed + 1))
    return ep, inj


def test_gate_admits_clean_evidence() -> None:
    ep = make_episode(5, 0)
    d = PreActionGate().evaluate([ep.clean_price_record()])
    assert d.admitted and not d.detected and d.response == "admit"
    assert d.evidence_ids  # versioned evidence set logged


def test_gate_quarantine_substitutes_from_buffer_only() -> None:
    ep, inj = _evidence("stale_master_data", 7)
    buf = GovernedBuffer({ep.sku: ep.true_unit_cost})
    d = PreActionGate(buffer=buf).evaluate(inj.evidence_set())
    assert d.detected and d.admitted and d.response == "quarantine_substitute"
    assert d.substituted_value == ep.true_unit_cost  # from the buffer, not ground truth
    # No substitute available -> falls back to block (never fabricates a value).
    d2 = PreActionGate(buffer=GovernedBuffer()).evaluate(inj.evidence_set())
    assert not d2.admitted and d2.response == "block" and d2.substituted_value is None


def test_gate_never_mutates_source_records() -> None:
    ep, inj = _evidence("stale_master_data", 3)
    before = [dict(r.payload) for r in inj.evidence_set()]
    PreActionGate(buffer=GovernedBuffer({ep.sku: ep.true_unit_cost})).evaluate(inj.evidence_set())
    after = [dict(r.payload) for r in inj.evidence_set()]
    assert before == after  # gate is read-only over the evidence set


def test_h2_channel_asymmetry_C_vs_D() -> None:
    """C (payload-only) is blind to metadata-borne defects; D (metadata) catches them."""
    meta = run_condition("stale_master_data", 0.20, "C", n_episodes=200)
    meta_d = run_condition("stale_master_data", 0.20, "D", n_episodes=200)
    payload = run_condition("cross_source_contradiction", 0.20, "C", n_episodes=200)
    assert meta.detection_rate == 0.0  # critic cannot see metadata staleness
    assert meta_d.detection_rate > 0.9  # gate can
    assert payload.detection_rate > 0.9  # critic sees payload-visible contradiction


def test_D_recovers_and_matches_oracle_no_false_blocks() -> None:
    m = run_matrix(classes=["stale_master_data"], rates=[0.20], n_episodes=200)
    cell = m["matrix"]["stale_master_data"]["0.20"]
    assert cell["A"]["adr"] > 0.2  # baseline converts
    assert cell["D"]["adr"] == 0.0  # gate recovers
    assert cell["E"]["adr"] == 0.0  # oracle upper bound
    assert cell["D"]["recovery_ratio"] is not None and cell["D"]["recovery_ratio"] > 0.8
    for arm in ("A", "C", "D", "E", "F"):
        assert cell[arm]["false_block_rate"] == 0.0  # clean records never blocked


def test_matrix_is_deterministic_and_covers_all_arms() -> None:
    a = run_matrix(classes=["stale_master_data"], rates=[0.10], n_episodes=50)
    b = run_matrix(classes=["stale_master_data"], rates=[0.10], n_episodes=50)
    assert a == b
    assert set(a["matrix"]["stale_master_data"]["0.10"]) == set(ARMS)
