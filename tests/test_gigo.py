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


def test_rate_cells_are_independent_not_nested() -> None:
    # W3 regression: the corruption mask must be drawn per RATE, so adjacent rate cells
    # are neither byte-identical nor nested subsets. A rate-independent draw made 0.02
    # and 0.05 share the exact same corrupted episodes.
    from sarc_dq.substrate import corruption_decision

    base_seed = 20260707
    masks = {
        r: {i for i in range(200) if corruption_decision(base_seed, i, r)[1]}
        for r in (0.02, 0.05, 0.10, 0.20)
    }
    assert masks[0.02] != masks[0.05]  # not byte-identical
    assert not (masks[0.02] <= masks[0.05])  # not nested
    assert not (masks[0.05] <= masks[0.10])


def test_mock_matrix_rate_cells_differ() -> None:
    # V0 mock proof: two cells (same class, 0.02 vs 0.05) must not be byte-identical.
    ref = json.loads(_REF.read_text())
    for cls, rates in ref["matrix"].items():
        assert rates["0.02"] != rates["0.05"], f"{cls}: 0.02 and 0.05 cells identical"
