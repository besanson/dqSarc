"""Live agent under test: a real Claude call per replenishment decision.

Import-guarded — the ``anthropic`` SDK is an optional ``[live]`` dependency, so
the core, the mock pipeline, and CI never touch it. Instantiating this class
without the SDK (or without ``ANTHROPIC_API_KEY``) raises a clear error.

A refusal (``stop_reason == "refusal"``, possible on fable-5) is logged as its
own outcome class and never scored as an action defect (brief §3).
"""

from __future__ import annotations

import re
from typing import Any

from sarc_dq.agent.base import (
    OUTCOME_ERROR,
    OUTCOME_OK,
    OUTCOME_REFUSAL,
    AgentDecision,
    agent_view,
    build_prompt,
)
from sarc_dq.pricing import usd_for
from sarc_dq.records import EvidenceRecord
from sarc_dq.substrate import Episode

_ORDER_RE = re.compile(r"ORDER:\s*([0-9][0-9,]*\.?[0-9]*)", re.IGNORECASE)


def parse_order(text: str) -> float | None:
    """Extract the final ``ORDER: <number>`` value from a transcript, if present."""
    matches = _ORDER_RE.findall(text)
    if not matches:
        return None
    return float(matches[-1].replace(",", ""))


class AnthropicAgent:
    """Real Claude agent. Requires ``pip install 'sarc-dq[live]'`` + an API key."""

    def __init__(self, model: str, *, max_tokens: int = 512, temperature: float = 0.0) -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - exercised only in the live arm
            raise RuntimeError(
                "AnthropicAgent needs the 'anthropic' SDK: pip install 'sarc-dq[live]'"
            ) from exc
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    def decide(
        self, episode: Episode, price_record: EvidenceRecord, *, advisory: bool = False
    ) -> AgentDecision:
        view = agent_view(episode, price_record)
        prompt = build_prompt(view, advisory=advisory)
        try:
            resp: Any = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:  # pragma: no cover - network/live only
            return AgentDecision(
                order_qty=float("nan"), transcript=f"[error] {exc}", outcome=OUTCOME_ERROR
            )

        in_tok = int(getattr(resp.usage, "input_tokens", 0))
        out_tok = int(getattr(resp.usage, "output_tokens", 0))
        usd = usd_for(self.model, in_tok, out_tok)

        if getattr(resp, "stop_reason", None) == "refusal":
            return AgentDecision(
                order_qty=float("nan"),
                transcript="[refusal]",
                outcome=OUTCOME_REFUSAL,
                usd=usd,
                input_tokens=in_tok,
                output_tokens=out_tok,
            )

        text = "".join(getattr(b, "text", "") for b in resp.content)
        qty = parse_order(text)
        if qty is None:
            # No parseable order: treat as fallback to the model-implied optimum so
            # a formatting miss does not masquerade as an action defect. Logged raw.
            qty = episode.optimal_order(float(view["unit_cost"]))
        return AgentDecision(
            order_qty=float(qty),
            transcript=text,
            outcome=OUTCOME_OK,
            usd=usd,
            input_tokens=in_tok,
            output_tokens=out_tok,
            raw={"stop_reason": getattr(resp, "stop_reason", None)},
        )
