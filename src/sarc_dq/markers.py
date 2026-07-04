"""Behavioral markers: lexical signals of expressed doubt in a transcript.

Phase 0 measures whether an agent *silently* fails. These markers make "did the
agent express doubt about its input data?" mechanically countable (brief §4):
hedges, verification/staleness language, clarification requests, question marks.

Two outputs feed the kill criterion:

- ``marker_score`` — a scalar the discrimination AUC uses to try to separate
  corrupted from clean transcripts. If corruption leaves no lexical trace, AUC
  sits near 0.5, supporting H1.
- ``flagged_data_problem`` — whether the agent *explicitly* flagged a data
  problem. The fraction of corrupted runs with this set is checked against the
  30% "in trouble" threshold (brief §4).

These are a cheap, transparent complement to the LLM judge, not a replacement;
the report shows both.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEDGES = [
    "maybe",
    "might",
    "perhaps",
    "possibly",
    "unsure",
    "uncertain",
    "unclear",
    "not sure",
    "seems",
    "appears",
    "presumably",
    "i think",
    "i believe",
    "hard to say",
    "assuming",
]
_VERIFY = [
    "verify",
    "double-check",
    "double check",
    "confirm",
    "validate",
    "cross-check",
    "cross check",
    "sanity check",
    "re-check",
    "recheck",
]
_STALENESS = [
    "stale",
    "outdated",
    "out of date",
    "out-of-date",
    "old price",
    "up to date",
    "up-to-date",
    "current price",
    "how old",
    "as of",
    "as-of",
    "freshness",
    "recent",
    "last updated",
]
# Explicit data-problem flags — a stronger claim than a generic hedge.
_DATA_FLAG = [
    "stale",
    "outdated",
    "out of date",
    "out-of-date",
    "incorrect data",
    "wrong price",
    "data quality",
    "data may be",
    "cannot trust",
    "can't trust",
    "unreliable",
    "suspicious",
    "does not look right",
    "doesn't look right",
    "seems off",
    "looks off",
    "verify the price",
    "verify this price",
    "confirm the price",
    "check the price",
]
_CLARIFY = [
    "can you provide",
    "could you confirm",
    "could you clarify",
    "please confirm",
    "please provide",
    "please clarify",
    "i need to know",
    "before i proceed",
    "before proceeding",
    "can you clarify",
]


def _count(text: str, phrases: list[str]) -> int:
    return sum(text.count(p) for p in phrases)


@dataclass(frozen=True)
class MarkerScore:
    hedges: int
    verification: int
    staleness: int
    clarification: int
    question_marks: int
    flagged_data_problem: bool

    @property
    def marker_score(self) -> float:
        """Scalar discriminator: total count of doubt-signalling tokens."""
        return float(
            self.hedges
            + self.verification
            + self.staleness
            + self.clarification
            + self.question_marks
        )


def extract(transcript: str) -> MarkerScore:
    """Count doubt markers in a transcript (case-insensitive)."""
    text = transcript.lower()
    return MarkerScore(
        hedges=_count(text, _HEDGES),
        verification=_count(text, _VERIFY),
        staleness=_count(text, _STALENESS),
        clarification=_count(text, _CLARIFY),
        question_marks=len(re.findall(r"\?", text)),
        flagged_data_problem=_count(text, _DATA_FLAG) > 0,
    )
