"""Agents: the payload-only decision interface, a mock, and a live Claude agent."""

from __future__ import annotations

from sarc_dq.agent.base import (
    OUTCOME_ERROR,
    OUTCOME_OK,
    OUTCOME_REFUSAL,
    Agent,
    AgentDecision,
    agent_view,
    build_prompt,
)
from sarc_dq.agent.mock import MockAgent

__all__ = [
    "Agent",
    "AgentDecision",
    "MockAgent",
    "OUTCOME_OK",
    "OUTCOME_REFUSAL",
    "OUTCOME_ERROR",
    "agent_view",
    "build_prompt",
]


def make_agent(arm: str, model: str) -> Agent:
    """Construct the agent for an arm. ``mock`` is offline; ``live`` needs the SDK."""
    if arm == "mock":
        return MockAgent()
    if arm == "live":
        from sarc_dq.agent.anthropic_agent import AnthropicAgent

        return AnthropicAgent(model=model)
    raise ValueError(f"unknown arm {arm!r} (expected 'mock' or 'live')")
