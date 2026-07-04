"""LLM-judge behavioral scoring + its hand-checkable validation set."""

from __future__ import annotations

from sarc_dq.judge.base import Judge, JudgeScore
from sarc_dq.judge.mock import MockJudge
from sarc_dq.judge.validation import CASES, Case, validate

__all__ = ["Judge", "JudgeScore", "MockJudge", "CASES", "Case", "validate", "make_judge"]


def make_judge(arm: str, model: str) -> Judge:
    """Construct the judge for an arm. ``mock`` is offline; ``live`` needs the SDK."""
    if arm == "mock":
        return MockJudge()
    if arm == "live":
        from sarc_dq.judge.anthropic_judge import AnthropicJudge

        return AnthropicJudge(model=model)
    raise ValueError(f"unknown arm {arm!r} (expected 'mock' or 'live')")
