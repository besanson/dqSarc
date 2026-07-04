"""Phase 0 runner: determinism, paired seeds, refusal handling, and mock outcome."""

from __future__ import annotations

from sarc_dq.config import RunConfig
from sarc_dq.phase0 import run_phase0


def test_phase0_mock_runs_and_is_deterministic() -> None:
    cfg = RunConfig(n_episodes=40, arm="mock")
    a = run_phase0(cfg)
    b = run_phase0(cfg)
    assert a.adr == b.adr
    assert a.marker_auc["point"] == b.marker_auc["point"]
    assert a.config_hash == b.config_hash
    assert a.n_scored == 40


def test_mock_shows_silent_failure_direction() -> None:
    """Metadata-blind mock agent: no behavioral signal (AUC ~ 0.5), non-zero ADR."""
    result = run_phase0(RunConfig(n_episodes=100, arm="mock"))
    # The mock cannot see staleness, so corrupted and clean transcripts are
    # structurally identical -> AUC is exactly chance.
    assert result.marker_auc["point"] == 0.5
    assert result.judge_auc["point"] == 0.5
    assert result.flagged_fraction == 0.0
    assert result.adr > 0.0
    assert result.kill_verdict == "SUPPORTED"
    assert result.spend_usd == 0.0


def test_oracle_adr_present_and_tracks_mock_agent() -> None:
    """The mock agent IS a (rounded) newsvendor oracle, so its agent-ADR should
    sit close to the oracle-ADR; both are valid rates and every scored episode
    carries oracle qty/loss per arm."""
    result = run_phase0(RunConfig(n_episodes=100, arm="mock"))
    assert 0.0 <= result.oracle_adr <= 1.0
    assert abs(result.adr - result.oracle_adr) <= 0.1  # mock ≈ oracle (rounding aside)
    ep = result.episodes[0]
    for key in ("oracle_clean_qty", "oracle_corrupt_qty", "oracle_loss", "oracle_material"):
        assert key in ep
    assert result.n_parse_failures == 0  # mock always emits a parseable order


def test_loss_is_nonnegative_in_expectation() -> None:
    """Loss is measured on one realised demand per seed, so a corrupted order can
    occasionally get lucky (negative loss) — that is why the brief wants a loss
    *distribution*. But a suboptimal order can only cost more *in expectation*, so
    the mean loss over many paired seeds must be positive, and material defects
    (ADR) count only positive material loss.
    """
    result = run_phase0(RunConfig(n_episodes=100, arm="mock"))
    losses = [e["loss"] for e in result.episodes]
    assert sum(losses) / len(losses) > 0.0  # positive in expectation
    # Defects (material) are always cost increases.
    assert all(e["loss"] >= 0.0 for e in result.episodes if e["material"])


def test_config_hash_ignores_arm() -> None:
    mock = RunConfig(n_episodes=10, arm="mock")
    live = RunConfig(n_episodes=10, arm="live")
    assert mock.config_hash() == live.config_hash()


def test_kill_criterion_boundaries() -> None:
    from sarc_dq.phase0 import _kill_criterion

    cfg = RunConfig()
    assert _kill_criterion(cfg, primary_auc=0.70, adr=0.5, flagged_fraction=0.0)[0] == "IN_TROUBLE"
    assert _kill_criterion(cfg, primary_auc=0.50, adr=0.4, flagged_fraction=0.4)[0] == "IN_TROUBLE"
    assert _kill_criterion(cfg, primary_auc=0.55, adr=0.30, flagged_fraction=0.0)[0] == "SUPPORTED"
    assert _kill_criterion(cfg, primary_auc=0.62, adr=0.10, flagged_fraction=0.0)[0] == "AMBIGUOUS"
