"""Phase 0 smoke-test runner (brief §4). HARD STOP GATE after this completes.

Usage::

    python -m benchmarks.phase0_smoke                       # mock arm, 100 episodes, $0
    python -m benchmarks.phase0_smoke --episodes 100 --arm live   # real Claude (needs key)
    python -m benchmarks.phase0_smoke --out reports/SMOKE_TEST.md
    python -m benchmarks.phase0_smoke --verify reports/reference_smoke.json

The default arm is ``mock`` — deterministic, offline, $0 — so a fresh clone and
CI exercise the whole pipeline without an API key. The ``live`` arm runs the real
agent under test + the LLM judge and is the run that answers H1.

Writes three artefacts:
- ``--out`` markdown report (default ``reports/SMOKE_TEST.md``);
- a machine-readable summary JSON next to it (``*.summary.json``);
- a per-episode dual-channel JSONL log under ``reports/logs/`` (git-ignored).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from sarc_dq.config import RunConfig
from sarc_dq.phase0 import Phase0Result, run_phase0
from sarc_dq.report import render_markdown

# Metrics compared by --verify, with per-metric absolute tolerances. ADR/AUC are
# rates (abs tol), loss mean is relative-checked separately below.
_VERIFY_ABS = {"adr": 0.02, "marker_auc": 0.02, "judge_auc": 0.02, "flagged_fraction": 0.02}


def _write_logs(result: Phase0Result, report_path: Path) -> Path:
    log_dir = report_path.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"phase0_{result.config_hash}.jsonl"
    with log_path.open("w", encoding="utf-8") as fh:
        for ep in result.episodes:
            fh.write(json.dumps({"kind": "scored", **ep}, default=str) + "\n")
        # Failed/parse-fail pairs are excluded from ADR but written here so they
        # are auditable (outcome, both raw transcripts, injected drift).
        for fail in result.failures:
            fh.write(json.dumps(fail, default=str) + "\n")
    return log_path


def _summary_dict(result: Phase0Result) -> dict[str, Any]:
    return {
        "config_hash": result.config_hash,
        "config": result.config,
        "n_episodes": result.n_episodes,
        "n_scored": result.n_scored,
        "n_refusals": result.n_refusals,
        "n_errors": result.n_errors,
        "n_parse_failures": result.n_parse_failures,
        "adr": result.adr,
        "oracle_adr": result.oracle_adr,
        "loss_quantiles": result.loss_quantiles,
        "oracle_loss_quantiles": result.oracle_loss_quantiles,
        "loss_ci": result.loss_ci,
        "tail_ratio": result.tail_ratio,
        "heavy_tail_flag": result.heavy_tail_flag,
        "marker_auc": result.marker_auc,
        "judge_auc": result.judge_auc,
        "flagged_fraction": result.flagged_fraction,
        "judge_validation": result.judge_validation,
        "kill_verdict": result.kill_verdict,
        "kill_detail": result.kill_detail,
        "spend_usd": result.spend_usd,
        "elasticity_median": result.elasticity_median,
        "elasticity_n": result.elasticity_n,
        "clean_regret": result.clean_regret,
        "failure_autopsy": result.failure_autopsy,
    }


def _verify(summary: dict[str, Any], ref_path: str) -> int:
    ref = json.loads(Path(ref_path).read_text(encoding="utf-8"))
    failures = []
    for key, tol in _VERIFY_ABS.items():
        new = (
            float(summary[key])
            if not isinstance(summary[key], dict)
            else float(summary[key]["point"])
        )
        old = float(ref[key]) if not isinstance(ref[key], dict) else float(ref[key]["point"])
        if math.isnan(new) or math.isnan(old):
            continue
        if abs(new - old) > tol:
            failures.append((key, old, new, abs(new - old)))
    if failures:
        print("verify: FAILED")
        for key, old, new, drift in failures:
            print(f"  {key:<18} ref={old:.4f} new={new:.4f} drift={drift:.4f}")
        return 2
    print(f"verify: OK ({len(_VERIFY_ABS)} metrics within tolerance)")
    return 0


def main(argv: Any = None) -> int:
    parser = argparse.ArgumentParser(prog="benchmarks.phase0_smoke", description=__doc__)
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument(
        "--seeds",
        type=int,
        default=None,
        help="alias for --episodes (kept for make-target symmetry)",
    )
    parser.add_argument("--arm", choices=["mock", "live"], default="mock")
    parser.add_argument(
        "--prompt",
        choices=["naive", "policy_instructed"],
        default="naive",
        help="prompt variant; 'naive' (default) reproduces Phase 0a exactly",
    )
    parser.add_argument("--out", default="reports/SMOKE_TEST.md")
    parser.add_argument("--verify", default=None, help="reference summary JSON to check against")
    args = parser.parse_args(argv)

    n = args.seeds if args.seeds is not None else args.episodes
    config = RunConfig(n_episodes=n, arm=args.arm, prompt_variant=args.prompt)
    result = run_phase0(config)

    report_path = Path(args.out)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_markdown(result), encoding="utf-8")
    summary = _summary_dict(result)
    summary_path = report_path.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    log_path = _write_logs(result, report_path)

    print(
        f"Phase 0 [{args.arm}/{args.prompt}] — {result.n_scored}/{result.n_episodes} scored "
        f"({result.n_parse_failures} parse-fail), agent-ADR={result.adr:.1%}, "
        f"oracle-ADR={result.oracle_adr:.1%}, elasticity={result.elasticity_median:.2f}, "
        f"marker AUC={result.marker_auc['point']:.3f}, "
        f"judge AUC={result.judge_auc['point']:.3f}, verdict={result.kill_verdict}"
    )
    print(f"  report:  {report_path}")
    print(f"  summary: {summary_path}")
    print(f"  logs:    {log_path}")
    print(f"  spend:   ${result.spend_usd:.4f}")

    if args.verify:
        return _verify(summary, args.verify)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
