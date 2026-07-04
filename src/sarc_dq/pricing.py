"""USD pricing table for the cost channel (brief §6, dual-channel logging).

The cost channel is deliberately paper-grade. USD is the currency the paper
reports (never raw token counts across model tiers — different tokenizers, brief
§3). Prices below are the standard published per-MTok rates for the Gate 0 model
ladder (confirm against the current price sheet before a final camera-ready).

Note: ``claude-sonnet-5`` carries an introductory promotion of **$2 / $10** per
MTok through **Aug 31**; the table uses the standard **$3 / $15** so spend is not
under-reported. Set ``SARC_DQ_PRICING`` to bill the promo rate for a run inside
the window.

Override at runtime with ``SARC_DQ_PRICING`` (a JSON object
``{"model": {"input": <usd_per_token>, "output": <usd_per_token>}}``) or by
editing this table. Unknown models fall back to ``_FALLBACK`` and are flagged.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

# USD per single token (i.e. per-MTok price / 1e6). Standard published rates.
_TABLE: dict[str, dict[str, float]] = {
    "claude-haiku-4-5": {"input": 1.0e-6, "output": 5.0e-6},  # $1 / $5
    "claude-sonnet-5": {"input": 3.0e-6, "output": 15.0e-6},  # $3 / $15 (intro $2/$10 to Aug 31)
    "claude-opus-4-8": {"input": 5.0e-6, "output": 25.0e-6},  # $5 / $25
    "claude-fable-5": {"input": 10.0e-6, "output": 50.0e-6},  # $10 / $50
}
_FALLBACK = {"input": 3.0e-6, "output": 15.0e-6}


@dataclass(frozen=True)
class Price:
    input_per_token: float
    output_per_token: float
    is_estimate: bool  # True when the model was not found and the fallback was used


def _load_overrides() -> dict[str, dict[str, float]]:
    raw = os.environ.get("SARC_DQ_PRICING")
    if not raw:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("SARC_DQ_PRICING must be a JSON object")
    return parsed


def price_for(model: str) -> Price:
    """Return the per-token USD price for ``model`` (env overrides win)."""
    table = {**_TABLE, **_load_overrides()}
    entry = table.get(model)
    if entry is None:
        return Price(_FALLBACK["input"], _FALLBACK["output"], is_estimate=True)
    return Price(float(entry["input"]), float(entry["output"]), is_estimate=False)


def usd_for(model: str, input_tokens: int, output_tokens: int) -> float:
    """USD cost of one call from its token usage."""
    p = price_for(model)
    return input_tokens * p.input_per_token + output_tokens * p.output_per_token
