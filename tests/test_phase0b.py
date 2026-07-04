"""Phase 0b amendment: prompt variant, hash stability, elasticity, failure logging."""

from __future__ import annotations

from sarc_dq.agent.base import (
    OUTCOME_ERROR,
    OUTCOME_OK,
    AgentDecision,
    build_prompt,
)
from sarc_dq.config import RunConfig
from sarc_dq.judge import MockJudge
from sarc_dq.phase0 import run_phase0
from sarc_dq.records import EvidenceRecord
from sarc_dq.substrate import Episode


def test_naive_hash_is_frozen_and_policy_is_distinct() -> None:
    naive = RunConfig(n_episodes=100).config_hash()
    policy = RunConfig(n_episodes=100, prompt_variant="policy_instructed").config_hash()
    # The frozen Phase 0a design hash must never drift.
    assert naive == "c8202a18b58754d8"
    assert policy != naive


def test_policy_prompt_has_formula_and_no_dq_language() -> None:
    from sarc_dq.agent.base import agent_view
    from sarc_dq.substrate import make_episode

    ep = make_episode(123, 0)
    view = agent_view(ep, ep.clean_price_record())
    naive = build_prompt(view, variant="naive")
    policy = build_prompt(view, variant="policy_instructed")

    assert "critical ratio" in policy.lower()
    assert "ORDER:" in policy
    assert policy != naive
    # No data-quality language may leak into the policy variant.
    for banned in ("verify", "check", "trust", "stale", "outdated", "fresh", "confirm", "doubt"):
        assert banned not in policy.lower(), banned


def test_parse_order_is_hardened() -> None:
    from sarc_dq.agent.anthropic_agent import parse_order

    assert parse_order("ORDER: 500") == 500
    assert parse_order("ORDER: 500.7") == 501  # decimals rounded to int
    assert parse_order("ORDER: 1,200") == 1200  # thousands comma
    assert parse_order("**ORDER:** 512**") == 512  # markdown bold stripped
    assert parse_order("ORDER: ≈ 640") == 640  # approx symbol tolerated
    assert parse_order("ORDER: approx 300") == 300  # approx word tolerated
    assert parse_order("`ORDER: 42`.") == 42  # code ticks + trailing punctuation
    # Takes the LAST match (the agent's final line).
    assert parse_order("first ORDER: 10\n...revised\nORDER: 25") == 25
    assert parse_order("no order line here") is None


def test_thinking_param_is_model_aware() -> None:
    from sarc_dq.agent.anthropic_agent import _thinking_param

    assert _thinking_param("claude-sonnet-5") == {"type": "disabled"}
    assert _thinking_param("claude-opus-4-8") == {"type": "disabled"}
    # Fable/Mythos: thinking is always on and {disabled} 400s, so we omit the param.
    assert _thinking_param("claude-fable-5") is None
    assert _thinking_param("claude-mythos-5") is None


def test_policy_prompt_has_output_format_and_no_dq_language() -> None:
    from sarc_dq.agent.base import agent_view, build_prompt
    from sarc_dq.substrate import make_episode

    ep = make_episode(7, 0)
    policy = build_prompt(agent_view(ep, ep.clean_price_record()), variant="policy_instructed")
    assert "ORDER: <integer>" in policy  # output-format spec present
    assert "reasoning" in policy.lower()  # reasoning explicitly allowed
    for banned in ("verify", "check", "trust", "stale", "outdated", "fresh", "confirm", "doubt"):
        assert banned not in policy.lower(), banned


def test_mock_elasticity_near_one_and_regret_present() -> None:
    r = run_phase0(RunConfig(n_episodes=100, prompt_variant="policy_instructed"))
    # The mock is the oracle (modulo integer rounding), so it is fully elastic.
    assert 0.9 <= r.elasticity_median <= 1.1
    assert r.elasticity_n > 0
    assert set(r.clean_regret) == {"median", "p90", "mean"}


class _FailOnCorruptAgent:
    """Stub: OK on the clean record, unparseable-ORDER error on the corrupt one."""

    model = "stub:fail-on-corrupt"

    def decide(
        self,
        episode: Episode,
        price_record: EvidenceRecord,
        *,
        advisory: bool = False,
        prompt_variant: str = "naive",
    ) -> AgentDecision:
        if price_record.ground_truth.get("corrupted"):
            return AgentDecision(
                order_qty=float("nan"),
                transcript="I will think about it.",  # no ORDER: line
                outcome=OUTCOME_ERROR,
                raw={"parse_failed": True},
            )
        return AgentDecision(order_qty=500.0, transcript="ORDER: 500", outcome=OUTCOME_OK)


def test_failed_pairs_are_logged_and_excluded_from_adr() -> None:
    cfg = RunConfig(n_episodes=20, arm="mock")
    r = run_phase0(cfg, agent=_FailOnCorruptAgent(), judge=MockJudge())

    # Every corrupt arm fails to parse -> zero scored, all counted as parse failures.
    assert r.n_scored == 0
    assert r.n_parse_failures == 20
    assert len(r.failures) == 20
    assert r.n_scored + r.n_errors + r.n_refusals == cfg.n_episodes

    f = r.failures[0]
    assert f["kind"] == "failure"
    assert f["failed_arm"] == "corrupt"
    assert f["corrupt_outcome"] == OUTCOME_ERROR
    assert f["clean_transcript"] and f["corrupt_transcript"]  # both raw transcripts kept
    assert "drift_frac" in f and "age_days" in f  # injected drift is auditable

    autopsy = r.failure_autopsy
    assert autopsy["n"] == 20
    assert autopsy["by_arm"]["corrupt"] == 20
    assert autopsy["drift_frac"]["median"] == autopsy["drift_frac"]["median"]  # not NaN
