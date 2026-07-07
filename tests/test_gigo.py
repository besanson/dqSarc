"""GIGO-Bench freeze: the committed reference verifies (drift guard)."""

from __future__ import annotations

import json
from pathlib import Path

from benchmarks.gigo.reproduce import _cells, _summary, _verify

_REF = Path("benchmarks/gigo/reference_summary.json")


def test_reference_exists_and_is_full_matrix() -> None:
    ref = json.loads(_REF.read_text())
    assert set(ref["config"]["arms"]) == {"A", "B", "C", "D", "E", "F"}
    assert ref["config"]["rates"] == [0.02, 0.05, 0.10, 0.20]
    assert len(_cells(ref)) == 8 * 4 * 6  # 192 cells


def test_reference_reproduces_within_tolerance() -> None:
    assert _verify(_summary(100), str(_REF)) == 0
