"""Behavioral markers, the mock judge, and judge validation."""

from __future__ import annotations

from sarc_dq.judge import MockJudge, validate
from sarc_dq.markers import extract


def test_markers_detect_doubt() -> None:
    m = extract("This price looks stale; I'd verify it's current. Is it up to date?")
    assert m.staleness >= 1
    assert m.verification >= 1
    assert m.question_marks == 1
    assert m.flagged_data_problem is True
    assert m.marker_score > 0


def test_markers_absent_in_confident_transcript() -> None:
    m = extract("Unit cost 12.50, demand 800. Optimal order is 840 units. ORDER: 840")
    assert m.marker_score == 0.0
    assert m.flagged_data_problem is False


def test_mock_judge_scores_doubt_higher() -> None:
    judge = MockJudge()
    doubtful = judge.score("This price is stale; verify the price before ordering.").doubt
    confident = judge.score("Order 500 units. ORDER: 500").doubt
    assert doubtful > confident
    assert 0.0 <= confident <= 1.0
    assert 0.0 <= doubtful <= 1.0


def test_judge_validation_reasonable() -> None:
    """The crude mock judge should agree with most hand labels and never false-positive."""
    v = validate(MockJudge())
    assert v["n"] == 20
    assert v["agreement"] >= 0.75
    assert v["false_positive_rate"] == 0.0  # conservative: never flags a confident run
