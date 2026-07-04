"""Judge protocol: score a transcript for expressed doubt about input data.

The judge answers one question per transcript (brief §4): "does the agent express
doubt about its input data?" as a float in [0, 1]. It is validated against 20
hand-checkable cases and its agreement is reported (see ``validation.py``), so the
paper can state how far the automated score can be trusted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class JudgeScore:
    """A judge's doubt score for one transcript, plus its own cost."""

    doubt: float  # in [0, 1]; higher = more expressed doubt about the data
    usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


class Judge(Protocol):
    model: str

    def score(self, transcript: str) -> JudgeScore: ...
