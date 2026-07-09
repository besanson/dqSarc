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


def test_live_resumes_and_checkpoints(tmp_path) -> None:
    # First run leaves a checkpoint file; a second run resumes (no recompute) and the
    # summary is unchanged. Concurrency>1 must not change results (deterministic seeds).
    out = tmp_path / "h2.json"
    r1 = run(
        "h2-detection", n_episodes=6, arm_mode="live", fake=True, concurrency=4, out_path=str(out)
    )
    assert out.exists() and r1["cells_done"] == r1["cells_total"]
    r2 = run(
        "h2-detection", n_episodes=6, arm_mode="live", fake=True, concurrency=1, out_path=str(out)
    )
    assert r2["matrix"] == r1["matrix"]  # resumed: identical, concurrency-invariant


def test_live_resume_discards_stale_axis_checkpoint(tmp_path) -> None:
    # A pre-fix summary (old schema: config.arms, no config.axis) must NOT be resumed —
    # its cells would be marked done and never recompute the newly-added loss/recovery.
    # h1-ladder is the sharp case: old cells keyed by arm "A", new axis keyed by model.
    import json

    out = tmp_path / "h1-ladder.json"
    out.write_text(
        json.dumps(
            {
                "config": {"arms": ["A"]},  # old schema, no "axis"
                "matrix": {"stale_price": {"0.20": {"A": {"adr": 0.0}}}},
                "total_usd": 99.0,
            }
        ),
        encoding="utf-8",
    )
    r = run("h1-ladder", n_episodes=4, arm_mode="live", fake=True, out_path=str(out))
    # Fresh run: cells keyed by model, not by stale "A"; stale total_usd not carried in.
    any_cell = next(iter(next(iter(r["matrix"].values())).values()))
    assert "A" not in any_cell
    assert r["total_usd"] < 99.0


def test_live_deadline_stops_gracefully(tmp_path) -> None:
    out = tmp_path / "h1.json"
    r = run(
        "h1-full", n_episodes=4, arm_mode="live", fake=True, max_minutes=0.0, out_path=str(out)
    )
    # A zero budget stops before doing work, but still writes a (partial) summary.
    assert r["stopped_early"] is not None and r["stopped_early"]["reason"] == "deadline"
    assert out.exists()


def test_live_api_error_burst_aborts_and_saves_partial(tmp_path) -> None:
    # A systemic API failure (e.g. out of credits) must not crash the run or lose
    # spend: it aborts gracefully, records the reason, and keeps partial results.
    from benchmarks.experiments import _run_live_matrix

    class _BoomAgent:
        model = "fake:boom"

        def decide(self, *a, **k):
            raise RuntimeError("credit balance is too low")

    class _OkCritic:
        model = "fake:critic"

        def review(self, evidence):
            from sarc_dq.live_arms import CriticVerdict

            return CriticVerdict(False)

    import sarc_dq.live_arms as la

    orig = la.make_live
    la.make_live = lambda fake=False: (_BoomAgent(), _OkCritic())  # type: ignore[assignment]
    try:
        r = _run_live_matrix(arms=("A",), n_episodes=4, fake=False, error_budget=4)
    finally:
        la.make_live = orig
    assert r["stopped_early"] is not None and r["stopped_early"]["reason"] == "api_errors"


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


def test_fill_recovery_ratio_math() -> None:
    # H4 recovery on real-shaped (positive-loss) data: A is the ungated ceiling, E the
    # oracle floor, D the gate under test. ratio = (effA - effD)/(effA - effE).
    from benchmarks.experiments import fill_recovery_ratio

    matrix = {
        "stale_price": {
            "0.20": {
                "A": {"loss_eff_corrupted": 100.0},
                "D": {"loss_eff_corrupted": 20.0},
                "E": {"loss_eff_corrupted": 0.0},
            }
        }
    }
    fill_recovery_ratio(matrix)
    # (100 - 20) / (100 - 0) = 0.8
    assert matrix["stale_price"]["0.20"]["D"]["recovery_ratio"] == 0.8


def test_fill_recovery_ratio_skips_degenerate_span() -> None:
    # If A and E have equal effective loss (no recoverable span), the ratio is left
    # unset rather than dividing by ~0 or emitting a nonsense number.
    from benchmarks.experiments import fill_recovery_ratio

    matrix = {
        "c": {
            "0.05": {
                "A": {"loss_eff_corrupted": 5.0},
                "D": {"loss_eff_corrupted": 5.0},
                "E": {"loss_eff_corrupted": 5.0},
            }
        }
    }
    fill_recovery_ratio(matrix)
    assert "recovery_ratio" not in matrix["c"]["0.05"]["D"]


def test_h4_live_cells_carry_loss_and_recovery_keys() -> None:
    # h4-recovery must emit loss metrics on every arm and a recovery_ratio slot on D.
    out = run("h4-recovery", n_episodes=6, arm_mode="live", fake=True)
    any_cell = next(iter(next(iter(out["matrix"].values())).values()))
    assert set(any_cell) == {"A", "D", "E"}
    for arm in ("A", "D", "E"):
        assert "loss_mean_corrupted" in any_cell[arm]
        assert "loss_eff_corrupted" in any_cell[arm]


def test_h4_paired_loss_gives_zero_oracle_floor_and_populates_recovery() -> None:
    # The paired-loss fix (v2): arm E acts on the true price, so its corruption loss is
    # 0 by construction on EVERY cell — the recovery denominator's floor. Arm A carries
    # a positive corruption loss, so (effA - effE) > 0 and recovery_ratio populates.
    out = run("h4-recovery", n_episodes=40, arm_mode="live", fake=True)
    assert out["config"]["loss_model"] == "paired-counterfactual-v2"
    m = out["matrix"]
    pooled = {a: [0.0, 0] for a in ("A", "D", "E")}
    recovered = 0
    for rates in m.values():
        for cell in rates.values():
            for a in ("A", "D", "E"):
                assert cell["E"]["loss_eff_corrupted"] == 0.0  # oracle floor, exact
                pooled[a][0] += cell[a]["loss_eff_corrupted"] * cell[a]["n_corrupted"]
                pooled[a][1] += cell[a]["n_corrupted"]
            if cell["D"].get("recovery_ratio") is not None:
                recovered += 1
    la = pooled["A"][0] / pooled["A"][1]
    le = pooled["E"][0] / pooled["E"][1]
    assert le == 0.0 and la > 0.0  # positive pooled corruption loss above a zero floor
    assert recovered > 0  # at least some cells have a well-defined recovery ratio


def test_paired_materiality_zeros_the_oracle_adr() -> None:
    # ADR is judged on corruption-induced (paired) loss, not raw loss-vs-optimum. Arm E
    # acts on the true price, so it has zero corruption loss and therefore ZERO ADR on
    # every cell — the agent-noise control. Under the old raw-loss materiality an oracle
    # on clean data scored ADR ~0.73; this test guards against that regression.
    out = run("h4-recovery", n_episodes=40, arm_mode="live", fake=True)
    for rates in out["matrix"].values():
        for cell in rates.values():
            assert cell["E"]["adr"] == 0.0  # oracle: no corruption defects, ever


def test_live_resume_discards_stale_loss_model(tmp_path) -> None:
    # A checkpoint written under an older loss model must NOT be resumed — its cells
    # carry incomparable numbers. Same-axis but stale loss_model => recompute fresh.
    import json

    out = tmp_path / "h4.json"
    out.write_text(
        json.dumps(
            {
                "config": {"axis": ["A", "D", "E"], "loss_model": "raw-v1"},
                "matrix": {"stale_price": {"0.20": {"A": {"loss_eff_corrupted": 999.0}}}},
                "total_usd": 42.0,
            }
        ),
        encoding="utf-8",
    )
    r = run("h4-recovery", n_episodes=4, arm_mode="live", fake=True, out_path=str(out))
    assert r["total_usd"] < 42.0  # stale checkpoint discarded, not carried forward


def test_h1_ladder_sweeps_four_models() -> None:
    # h1-ladder sweeps arm A across the capability ladder: each cell is keyed by model
    # id (not arm), one per rung.
    from sarc_dq.live_arms import LADDER_MODELS

    out = run("h1-ladder", n_episodes=4, arm_mode="live", fake=True)
    assert out["config"]["axis_kind"] == "ladder_models"
    any_cell = next(iter(next(iter(out["matrix"].values())).values()))
    assert set(any_cell) == set(LADDER_MODELS)


def test_every_experiment_has_a_prereg() -> None:
    from pathlib import Path

    for exp in EXPERIMENTS:
        assert Path(f"reports/prereg/{exp}.md").exists(), exp
        assert Path(f".github/workflows/exp-{exp}.yml").exists(), exp
