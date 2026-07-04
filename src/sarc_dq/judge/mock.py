"""Deterministic mock judge: derives a doubt score from the lexical markers.

Offline and reproducible. It is a transparent function of the same markers the
report already shows, so in the mock pipeline the judge adds no independent
signal — that is fine: the mock exists to exercise the pipeline, and the real
judge (``AnthropicJudge``) supplies the independent read in the live arm.
"""

from __future__ import annotations

from sarc_dq.judge.base import JudgeScore
from sarc_dq.markers import extract


class MockJudge:
    def __init__(self, model: str = "mock:marker-derived") -> None:
        self.model = model

    def score(self, transcript: str) -> JudgeScore:
        m = extract(transcript)
        if m.flagged_data_problem:
            doubt = max(0.7, min(1.0, 0.7 + 0.1 * m.marker_score))
        else:
            doubt = min(0.6, 0.15 * m.marker_score)
        return JudgeScore(doubt=round(doubt, 4), raw={"marker_score": m.marker_score})
