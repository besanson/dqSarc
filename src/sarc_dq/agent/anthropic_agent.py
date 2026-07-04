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

# Hardened ORDER matcher (Phase 0c). Tolerates: an optional ``:`` or ``=``; an
# approximation marker (≈ ≅ ~ or the word "approx"/"about"); thousands commas; and
# decimals. Markdown emphasis / code markers are stripped before matching, so
# ``**ORDER:** 500``, ```ORDER: 500```, and ``ORDER: 500.`` all parse.
_ORDER_RE = re.compile(
    r"ORDER\s*[:=]?\s*(?:approx\.?|about|[≈≅~])?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
    re.IGNORECASE,
)


def parse_order(text: str) -> int | None:
    """Extract the **last** ``ORDER: <number>`` value from a transcript as an int.

    Takes the last match (the agent's final line), rounds decimals to the nearest
    integer (order quantities are whole units), and returns ``None`` if no ORDER
    value is present.
    """
    cleaned = text.replace("*", "").replace("`", "")
    matches = _ORDER_RE.findall(cleaned)
    if not matches:
        return None
    return int(round(float(matches[-1].replace(",", ""))))


def _thinking_param(model: str) -> dict[str, Any] | None:
    """Explicitly turn reasoning off so visible output can't be starved (Phase 0c).

    ``max_tokens`` caps *total* output (thinking + visible text), so silent
    reasoning can consume the budget before the agent emits its ``ORDER:`` line.
    Sonnet 5 / Opus 4.8 / 4.7 accept ``{"type": "disabled"}``; Fable 5 / Mythos 5
    reject it (thinking is always on) and must omit the parameter — there we rely
    on the raised ``max_tokens`` for headroom instead.
    """
    lowered = model.lower()
    if "fable" in lowered or "mythos" in lowered:
        return None
    return {"type": "disabled"}


class AnthropicAgent:
    """Real Claude agent. Requires ``pip install 'sarc-dq[live]'`` + an API key."""

    def __init__(self, model: str, *, max_tokens: int = 4096) -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - exercised only in the live arm
            raise RuntimeError(
                "AnthropicAgent needs the 'anthropic' SDK: pip install 'sarc-dq[live]'"
            ) from exc
        self.model = model
        self.max_tokens = max_tokens
        self._client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    def decide(
        self,
        episode: Episode,
        price_record: EvidenceRecord,
        *,
        advisory: bool = False,
        prompt_variant: str = "naive",
    ) -> AgentDecision:
        view = agent_view(episode, price_record)
        prompt = build_prompt(view, advisory=advisory, variant=prompt_variant)
        # No `temperature` (or other sampling params): Sonnet 5 (and the rest of
        # the ladder) returns HTTP 400 on non-default sampling params.
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        thinking = _thinking_param(self.model)
        if thinking is not None:
            kwargs["thinking"] = thinking
        try:
            resp: Any = self._client.messages.create(**kwargs)
        except Exception as exc:  # pragma: no cover - network/live only
            return AgentDecision(
                order_qty=float("nan"),
                transcript=f"[error] {exc}",
                outcome=OUTCOME_ERROR,
                raw={"error": str(exc)},
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
            # No parseable ORDER line: this is an error outcome, not an action
            # defect. We do NOT substitute a model-implied optimum — that would
            # bias ADR downward. The pair is excluded from ADR and the parse-failure
            # rate is reported so the substitution/exclusion is fully visible.
            return AgentDecision(
                order_qty=float("nan"),
                transcript=text,
                outcome=OUTCOME_ERROR,
                usd=usd,
                input_tokens=in_tok,
                output_tokens=out_tok,
                raw={"parse_failed": True, "stop_reason": getattr(resp, "stop_reason", None)},
            )
        return AgentDecision(
            order_qty=float(qty),
            transcript=text,
            outcome=OUTCOME_OK,
            usd=usd,
            input_tokens=in_tok,
            output_tokens=out_tok,
            raw={"stop_reason": getattr(resp, "stop_reason", None)},
        )
