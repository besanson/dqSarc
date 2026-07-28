"""Stage 2B --- one authentic, verbatim transcript excerpt of a metadata-borne stale-price
episode, extracted deterministically from committed data (no reruns, no API).

Source note (deviation, documented honestly). The excerpt is required to be verbatim from a
committed metadata-borne stale-price episode. The two branches named in the request
(``h1-full-live``, ``phase0c-live``) carry *no* transcript text: ``h1-full-live`` has no
transcript log, and ``phase0c-live``'s log stores only parsed numeric fields. The only committed
branch that retains verbatim agent transcripts is ``phase0b-live`` --- the sibling frozen branch
of the *same* Phase-0 stale-price pilot --- so the excerpt is sourced from there. Within that
log, transcripts were logged only for parse-failure *pairs*; we select a pair whose *clean twin*
parse-failed (``failed_arm == 'clean'``) while the *corrupt arm* produced coherent reasoning, and
we quote that corrupt-arm transcript. The caption states this precisely: it is an illustrative
excerpt, not a scored episode and not proof of the aggregate.

The selection is deterministic and reproducible; the excerpt is copied byte-for-byte (only
LaTeX-necessary escapes are applied, documented in ``ESCAPES``; every replacement renders the
same glyph, so the visible text is identical to the source). Writes:

  * ``analysis/out/transcript_provenance.json`` --- source branch/SHA/file, run id, seed, index,
    the raw excerpt, and its SHA-256 (so the paper's excerpt is always traceable to source);
  * ``paper/generated/transcript.tex`` --- the LaTeX-safe boxed figure the paper inputs.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from typing import Any

from analysis.common import ROOT

BRANCH = "origin/results/phase0b-live"
LOG_PATH = "reports/logs/phase0_e785bdc87009b84c.jsonl"
OUT_JSON = ROOT / "analysis" / "out" / "transcript_provenance.json"
OUT_TEX = ROOT / "paper" / "generated" / "transcript.tex"
MAX_LINES = 6
# Any of these in the transcript would be an expressed doubt / data-quality warning; their
# absence (checked on the verbatim text) is what substantiates the "no warning" claim, since the
# scored-only doubt/flag fields are not logged on failure records.
HEDGE_TERMS = (
    "stale",
    "outdated",
    "verify",
    "uncertain",
    "however",
    "warning",
    "data quality",
    "data-quality",
    "suspicious",
    "caveat",
    "unsure",
    "flag",
)

# LaTeX escape map (documented, reversible). Standard specials plus the three Unicode math
# glyphs present in the source; each math replacement renders the identical glyph, so the
# visible text is unchanged. Order matters: backslash first.
ESCAPES: list[tuple[str, str]] = [
    ("\\", "\\textbackslash{}"),
    ("&", "\\&"),
    ("%", "\\%"),
    ("$", "\\$"),
    ("#", "\\#"),
    ("_", "\\_"),
    ("{", "\\{"),
    ("}", "\\}"),
    ("~", "\\textasciitilde{}"),
    ("^", "\\textasciicircum{}"),
    ("\u2212", "$-$"),  # MINUS SIGN
    ("\u2248", "$\\approx$"),  # ALMOST EQUAL TO
    ("\u00d7", "$\\times$"),  # MULTIPLICATION SIGN
]


def _git_show(rev: str, path: str) -> str:
    out = subprocess.run(
        ["git", "show", f"{rev}:{path}"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return out.stdout


def _rev_parse(rev: str) -> str:
    out = subprocess.run(
        ["git", "rev-parse", rev], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


def _select() -> dict[str, Any]:
    """Deterministically pick the illustrative episode from the committed phase0b log.

    Criteria: a parse-failure pair whose corrupt arm is intact (``failed_arm == 'clean'``) and
    coherent (contains an ORDER), with no expressed doubt or data-quality flag, on a genuine
    stale-price corruption (shown price != true price). Tie-break by (line count, length, index)
    so the shortest, earliest qualifying excerpt wins.
    """
    records = [json.loads(line) for line in _git_show(BRANCH, LOG_PATH).splitlines() if line]
    cands: list[tuple[int, int, int, dict[str, Any]]] = []
    for d in records:
        ct = d.get("corrupt_transcript") or ""
        low = ct.lower()
        if (
            d.get("kind") == "failure"
            and d.get("is_parse_failure")
            and d.get("failed_arm") == "clean"  # clean twin failed; corrupt arm intact
            and "ORDER:" in ct  # coherent decision present
            and not any(term in low for term in HEDGE_TERMS)  # no expressed doubt / DQ warning
            and d.get("stale_unit_cost") != d.get("true_unit_cost")  # genuine stale corruption
        ):
            n_lines = ct.count("\n") + 1
            if 4 <= n_lines <= MAX_LINES:
                cands.append((n_lines, len(ct), int(d["index"]), d))
    if not cands:
        raise RuntimeError("no qualifying committed transcript episode found")
    cands.sort(key=lambda t: (t[0], t[1], t[2]))
    return cands[0][3]


def _escape(text: str) -> str:
    for src, dst in ESCAPES:
        text = text.replace(src, dst)
    return text


def _tex_body(excerpt: str) -> str:
    """Render the verbatim excerpt as LaTeX lines (empty lines preserved as blank breaks)."""
    lines = excerpt.split("\n")
    out = []
    for i, ln in enumerate(lines):
        esc = _escape(ln) if ln else "~"
        out.append(esc + ("\\\\" if i < len(lines) - 1 else ""))
    return "\n".join(out)


def build() -> dict[str, Any]:
    d = _select()
    sha = _rev_parse(BRANCH)
    excerpt = d["corrupt_transcript"]
    digest = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
    run_id = f"phase0b-live@{sha[:12]}:{LOG_PATH.split('/')[-1]}"
    return {
        "source_branch": BRANCH,
        "source_sha": sha,
        "source_file": LOG_PATH,
        "experiment": "phase0b (stale-price newsvendor pilot)",
        "run_id": run_id,
        "episode_index": int(d["index"]),
        "episode_seed": int(d["seed"]),
        "corruption_class": "stale_master_data",
        "true_unit_cost": d["true_unit_cost"],
        "stale_unit_cost": d["stale_unit_cost"],
        "age_days": d["age_days"],
        "record_kind": d["kind"],
        "is_parse_failure": bool(d["is_parse_failure"]),
        "failed_arm": d["failed_arm"],
        "no_hedge_verified": not any(t in excerpt.lower() for t in HEDGE_TERMS),
        "excerpt": excerpt,
        "excerpt_sha256": digest,
        "escape_map_version": 1,
        "provenance_note": (
            "Verbatim corrupt-arm transcript from a committed Phase-0b parse-failure pair "
            "(clean twin parse-failed; corrupt arm intact). Sourced from phase0b-live because the "
            "requested branches carry no transcript text. Illustrative only."
        ),
    }


def render_tex(p: dict[str, Any]) -> str:
    body = _tex_body(p["excerpt"])
    seed = p["episode_seed"]
    run_id = _escape(p["run_id"])
    stale = p["stale_unit_cost"]
    true = p["true_unit_cost"]
    return (
        "% AUTO-GENERATED by analysis/transcript.py (make analysis). Do not edit.\n"
        "% Verbatim excerpt from committed data; provenance + SHA-256 in\n"
        "% analysis/out/transcript_provenance.json.\n"
        "\\begin{figure}[t]\\centering\n"
        "\\fbox{\\parbox{0.92\\linewidth}{\\ttfamily\\footnotesize\n"
        f"{body}\n"
        "}}\n"
        "\\caption{Verbatim corrupt-arm transcript from a committed Phase-0b stale-price episode "
        f"(shown price \\${stale} vs.\\ true \\${true}), included only to illustrate the "
        "aggregate silence result---not a scored episode and not proof of the aggregate. "
        "The agent computes the order directly from the stale price and emits \\texttt{ORDER} "
        "with no expressed doubt or data-quality warning. The record is a logged parse-failure "
        "pair whose "
        "clean twin failed to parse while the corrupt arm stayed coherent. Run ID: "
        f"\\texttt{{{run_id}}}; episode seed: \\texttt{{{seed}}}. Text is byte-for-byte from the "
        "source (only LaTeX-necessary escapes applied); see "
        "\\texttt{analysis/out/transcript\\_provenance.json}.}\n"
        "\\label{fig:transcript}\n"
        "\\end{figure}\n"
    )


def main() -> int:
    p = build()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(p, indent=2) + "\n", encoding="utf-8")
    OUT_TEX.parent.mkdir(parents=True, exist_ok=True)
    OUT_TEX.write_text(render_tex(p), encoding="utf-8")
    print(f"wrote {OUT_JSON.relative_to(ROOT)} and {OUT_TEX.relative_to(ROOT)}")
    dig = p["excerpt_sha256"][:16]
    print(f"  index={p['episode_index']} seed={p['episode_seed']} sha256={dig}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
