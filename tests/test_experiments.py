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


def test_live_fake_path_runs_at_zero_dollars() -> None:
    # The live path is wired; --fake exercises it deterministically at $0 in CI.
    out = run("h2-detection", n_episodes=8, arm_mode="live", fake=True)
    assert out["arm_mode"] == "live" and out["total_usd"] == 0.0
    # Arm C blocks a payload-visible defect (detection>0); D detects it too.
    cell = out["matrix"]["cross_source_contradiction"]["0.20"]
    assert cell["C"]["detection_rate"] > 0.0 and cell["D"]["detection_rate"] > 0.0


def test_live_real_path_is_import_gated() -> None:
    # Without the optional anthropic SDK, the real (non-fake) live path refuses to
    # silently no-op — it raises rather than pretending to have run.
    try:
        import anthropic  # noqa: F401
    except ImportError:
        with pytest.raises((ImportError, RuntimeError)):
            run("h1-full", n_episodes=2, arm_mode="live", fake=False)
    else:  # SDK present (e.g. [live] extra) — skip; we won't spend to prove it.
        pytest.skip("anthropic SDK installed; real live path would require a key/spend")


def test_every_experiment_has_a_prereg() -> None:
    from pathlib import Path

    for exp in EXPERIMENTS:
        assert Path(f"reports/prereg/{exp}.md").exists(), exp
        assert Path(f".github/workflows/exp-{exp}.yml").exists(), exp
