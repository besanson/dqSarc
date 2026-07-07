"""Part-4 experiment kits: dispatcher runs (mock) for every experiment id."""

from __future__ import annotations

import pytest

from benchmarks.experiments import EXPERIMENTS, run


@pytest.mark.parametrize("exp", sorted(EXPERIMENTS))
def test_experiment_runs_mock(exp: str) -> None:
    out = run(exp, n_episodes=6, arm_mode="mock")
    assert out["experiment"] == exp
    assert "matrix" in out and out["matrix"]  # produced a matrix slice
    # Only the arms the experiment declares appear in each cell.
    arms = set(EXPERIMENTS[exp][0])
    any_cell = next(iter(next(iter(out["matrix"].values())).values()))
    assert set(any_cell) == arms


def test_live_arm_is_gated_not_faked() -> None:
    with pytest.raises(SystemExit, match="not wired"):
        run("h1-full", n_episodes=4, arm_mode="live")


def test_every_experiment_has_a_prereg() -> None:
    from pathlib import Path

    for exp in EXPERIMENTS:
        assert Path(f"reports/prereg/{exp}.md").exists(), exp
        assert Path(f".github/workflows/exp-{exp}.yml").exists(), exp
