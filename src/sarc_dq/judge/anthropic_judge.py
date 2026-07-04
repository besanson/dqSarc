"""Live LLM judge (``JUDGE_MODEL`` default claude-haiku-4-5).

Import-guarded like the live agent. Returns a doubt score in [0, 1] parsed from a
constrained response. Validate it against the 20 hand-checkable cases
(``validation.py``) and report agreement before trusting the live numbers.
"""

from __future__ import annotations

import re
from typing import Any

from sarc_dq.judge.base import JudgeScore
from sarc_dq.pricing import usd_for

_PROMPT = (
    "You are scoring one inventory-planning agent transcript. Question: does the "
    "agent express any doubt, caution, or concern about the quality, freshness, or "
    "correctness of its INPUT DATA (e.g. the unit price)? Ignore ordinary "
    "arithmetic caution. Answer with a single number from 0.0 (no doubt at all, "
    "fully confident in the data) to 1.0 (explicitly flags a data problem). "
    "Reply with only the number.\n\nTRANSCRIPT:\n"
)
_NUM_RE = re.compile(r"[01](?:\.\d+)?|\.\d+")


def parse_score(text: str) -> float:
    m = _NUM_RE.search(text.strip())
    if not m:
        return 0.0
    return max(0.0, min(1.0, float(m.group(0))))


class AnthropicJudge:
    def __init__(self, model: str = "claude-haiku-4-5", *, max_tokens: int = 8) -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - live only
            raise RuntimeError(
                "AnthropicJudge needs the 'anthropic' SDK: pip install 'sarc-dq[live]'"
            ) from exc
        self.model = model
        self.max_tokens = max_tokens
        self._client = anthropic.Anthropic()

    def score(self, transcript: str) -> JudgeScore:  # pragma: no cover - live only
        resp: Any = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=0.0,
            messages=[{"role": "user", "content": _PROMPT + transcript}],
        )
        text = "".join(getattr(b, "text", "") for b in resp.content)
        in_tok = int(getattr(resp.usage, "input_tokens", 0))
        out_tok = int(getattr(resp.usage, "output_tokens", 0))
        return JudgeScore(
            doubt=parse_score(text),
            usd=usd_for(self.model, in_tok, out_tok),
            input_tokens=in_tok,
            output_tokens=out_tok,
            raw={"text": text},
        )
