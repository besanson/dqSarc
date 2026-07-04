"""Render a Phase 0 result to ``reports/SMOKE_TEST.md`` (brief §4 deliverable).

Every number here comes from the :class:`~sarc_dq.phase0.Phase0Result` passed in
— nothing is hand-entered (brief §8, §11). When the run used the offline mock
arm, a loud banner marks the report a **pipeline dry-run, not a scientific
result**, so a reader never mistakes it for the real H1 finding.
"""

from __future__ import annotations

from typing import Any

from sarc_dq.phase0 import Phase0Result


def _ascii_hist(values: list[float], bins: int = 10, width: int = 40) -> list[str]:
    if not values:
        return ["  (no data)"]
    lo, hi = min(values), max(values)
    if hi <= lo:
        return [f"  all values == {lo:.2f}"]
    step = (hi - lo) / bins
    counts = [0] * bins
    for v in values:
        idx = min(bins - 1, int((v - lo) / step))
        counts[idx] += 1
    peak = max(counts) or 1
    lines = []
    for b in range(bins):
        left = lo + b * step
        bar = "#" * int(width * counts[b] / peak)
        lines.append(f"  {left:12.1f} | {bar} {counts[b]}")
    return lines


def render_markdown(result: Phase0Result) -> str:
    r = result
    mock = str(r.config.get("arm")) == "mock"
    lines: list[str] = []
    lines.append("# SMOKE_TEST — SARC-DQ Phase 0")
    lines.append("")
    lines.append("> **DRAFT — research artifact.**")
    if mock:
        lines.append(">")
        lines.append(
            "> ⚠️ **PIPELINE DRY-RUN, NOT A SCIENTIFIC RESULT.** This run used the "
            "offline, deterministic **mock agent + mock judge** (arm=`mock`, $0, no "
            "API). It exists to prove the Phase 0 pipeline runs end-to-end and the "
            "metrics/kill-criterion wiring is correct. The real H1 question is answered "
            "only by the **live** arm (`--arm live`, real Claude), which the human runs "
            "on their own infrastructure with an API key. Do **not** cite these numbers."
        )
    lines.append("")
    lines.append(f"- **config hash:** `{r.config_hash}`")
    lines.append(
        f"- **arm:** `{r.config.get('arm')}`  ·  **agent:** `{r.config.get('agent_model')}`"
        f"  ·  **judge:** `{r.config.get('judge_model')}`"
    )
    lines.append("- **corruption class:** `stale_unit_price` (metadata-borne)")
    lines.append(
        f"- **episodes:** {r.n_episodes} corrupted + {r.n_episodes} clean "
        f"(same seeds)  ·  **scored:** {r.n_scored}  ·  "
        f"**refusals:** {r.n_refusals}  ·  **errors:** {r.n_errors} "
        f"(of which unparseable ORDER: {r.n_parse_failures})"
    )
    parse_fail_rate = r.n_parse_failures / r.n_episodes if r.n_episodes else 0.0
    lines.append(
        f"- **parse-failure rate:** {parse_fail_rate:.1%} — unparseable ORDER lines are "
        "excluded from ADR (no optimum is substituted, so ADR is not biased down)."
    )
    lines.append(
        f"- **tau_m (materiality):** {float(r.config.get('tau_m', 0)) * 100:.2f}% of clean cost"
    )
    lines.append("")

    lines.append("## Headline")
    lines.append("")
    lines.append("| metric | value |")
    lines.append("|---|---|")
    lines.append(f"| Action Defect Rate — agent | **{r.adr:.1%}** |")
    lines.append(
        f"| Action Defect Rate — oracle (perfect metadata-blind solver) | {r.oracle_adr:.1%} |"
    )
    lines.append(
        f"| Behavioral marker AUC | {r.marker_auc['point']:.3f} "
        f"[{r.marker_auc['lo']:.3f}, {r.marker_auc['hi']:.3f}] |"
    )
    lines.append(
        f"| LLM-judge doubt AUC | {r.judge_auc['point']:.3f} "
        f"[{r.judge_auc['lo']:.3f}, {r.judge_auc['hi']:.3f}] |"
    )
    lines.append(f"| Explicit data-flag fraction (corrupted) | {r.flagged_fraction:.1%} |")
    lines.append(f"| **Kill-criterion verdict** | **{r.kill_verdict}** |")
    lines.append("")
    lines.append(f"**Verdict detail:** {r.kill_detail}")
    lines.append("")

    lines.append("## Loss distribution (currency)")
    lines.append("")
    lines.append("Loss = cost(corrupted) − cost(clean counterfactual), same seed.")
    lines.append("")
    lq = r.loss_quantiles
    lines.append("| median | P90 | P99 | mean | mean 95% CI (paired bootstrap) |")
    lines.append("|---|---|---|---|---|")
    lines.append(
        f"| {lq['median']:.2f} | {lq['p90']:.2f} | {lq['p99']:.2f} | {lq['mean']:.2f} | "
        f"[{r.loss_ci['lo']:.2f}, {r.loss_ci['hi']:.2f}] |"
    )
    lines.append("")
    tail = "⚠️ heavy tail (P99/median > 10)" if r.heavy_tail_flag else "P99/median within 10×"
    lines.append(f"- tail ratio P99/median = {r.tail_ratio:.1f} — {tail}")
    olq = r.oracle_loss_quantiles
    lines.append(
        f"- oracle loss (perfect metadata-blind solver): median {olq['median']:.2f}, "
        f"P90 {olq['p90']:.2f}, mean {olq['mean']:.2f} — the loss the stale price forces "
        "through the *optimal* rule, before any LLM decision noise."
    )
    lines.append("")
    lines.append("```")
    lines.append("loss histogram (lower bound of bin | count):")
    lines.extend(_ascii_hist([e["loss"] for e in r.episodes]))
    lines.append("```")
    lines.append("")

    lines.append("## Judge validation (20 hand-checkable cases)")
    lines.append("")
    v = r.judge_validation
    lines.append(
        f"- agreement: **{v['agreement']:.0%}**  ·  doubt recall: {v['doubt_recall']:.0%}"
        f"  ·  no-doubt recall: {v['no_doubt_recall']:.0%}"
        f"  ·  false-positive rate: {v['false_positive_rate']:.0%}"
    )
    lines.append("")

    lines.append("## Example transcripts")
    lines.append("")
    silent = _example_silent_failure(r)
    clean = _example_clean(r)
    if silent is not None:
        lines.append("**A silent failure** (material loss, no expressed doubt):")
        lines.append("")
        lines.append("```")
        lines.append(
            f"seed={silent['seed']}  true_cost={silent['true_unit_cost']:.2f}  "
            f"stale_cost={silent['stale_unit_cost']:.2f}  age={silent['age_days']}d"
        )
        lines.append(
            f"clean order   = {silent['clean_qty']:.0f}  → cost {silent['clean_cost']:.2f}"
        )
        lines.append(
            f"corrupt order = {silent['corrupt_qty']:.0f}  → cost {silent['corrupt_cost']:.2f}"
        )
        lines.append(
            f"loss          = {silent['loss']:.2f}  (material={silent['material']}, "
            f"doubt={silent['doubt_corrupt']:.2f}, flagged={silent['flagged_corrupt']})"
        )
        lines.append("```")
        lines.append("")
    if clean is not None:
        lines.append("**A clean run** (same seed, uncorrupted price):")
        lines.append("")
        lines.append("```")
        lines.append(
            f"seed={clean['seed']}  order={clean['clean_qty']:.0f}  "
            f"cost={clean['clean_cost']:.2f}  doubt={clean['doubt_clean']:.2f}"
        )
        lines.append("```")
        lines.append("")

    lines.append("## Spend")
    lines.append("")
    lines.append(
        f"- total API spend this run: **${r.spend_usd:.4f}**"
        + ("  (mock arm — $0 by construction)" if mock else "")
    )
    lines.append("")
    lines.append("## Raw logs")
    lines.append("")
    lines.append(
        "Per-episode dual-channel records (cost + evidence) are written to "
        "`reports/logs/phase0_<config_hash>.jsonl` (git-ignored). Re-run with "
        "`make smoke`."
    )
    lines.append("")
    return "\n".join(lines)


def _example_silent_failure(r: Phase0Result) -> dict[str, Any] | None:
    candidates = [e for e in r.episodes if e["material"] and not e["flagged_corrupt"]]
    if not candidates:
        return None
    return max(candidates, key=lambda e: e["loss"])


def _example_clean(r: Phase0Result) -> dict[str, Any] | None:
    return r.episodes[0] if r.episodes else None
