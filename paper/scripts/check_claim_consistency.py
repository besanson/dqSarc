"""Fail CI if the manuscript, macros, and status records drift apart (reviewer item #14).

Checks machine-readable invariants (plus a few high-value forbidden stale phrases) so that
a valid experiment can never silently become ``[pending]`` in the paper, an invalid run can
never be ingested, and provenance can never be incomplete. Deterministic; no API calls.

Run: ``python paper/scripts/check_claim_consistency.py`` (also wired as ``make check-claims``
and run in CI). Exits non-zero with a list of violations.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "paper" / "data"
STATUS = ROOT / "reports" / "experiment_status.json"
GENERATED = ROOT / "paper" / "generated" / "results.tex"
ANALYSIS = ROOT / "paper" / "generated" / "analysis.tex"
TRANSCRIPT_TEX = ROOT / "paper" / "generated" / "transcript.tex"
TRANSCRIPT_PROV = ROOT / "analysis" / "out" / "transcript_provenance.json"
README = ROOT / "README.md"

# Short H2 macro keys per class (mirror make_macros.py / stats_tables.py); the interval
# check verifies every row of Table 2 carries a Wilson lower and upper bound for C and D.
H2_KEYS = ("Cross", "Dup", "Missing", "Outlier", "Schema", "Unit", "Stale", "Superseded")
# H3/H4 residual-loss point macros (results.tex) that must each carry a bootstrap interval.
RESIDUAL_MACROS = (
    "HthreeGateResid",
    "HthreeCriticResid",
    "HfourStaleLossA",
    "HfourStaleLossD",
)

PRIMARY = {"h1-full", "h1-ladder", "h2-detection", "h3-frontier", "h4-recovery"}
OPTIONAL = {"ablations", "tier2-validation"}  # may remain pending
# Required non-null provenance fields. ``instrumentation`` is checked separately: it must be
# a present key (recorded), but may be null for runs that predate the cap-hardening tag
# (h1-full, h2-detection ran on the corrected harness before api-error-aware instrumentation).
PROV_FIELDS = ("branch", "sha", "run_id", "config_hash", "spend_usd", "cells")
# Res<Cap> macro name per primary experiment (must not be \pending).
RES_MACRO = {
    "h1-full": "ResHoneFull",
    "h1-ladder": "ResHoneLadder",
    "h2-detection": "ResHtwo",
    "h3-frontier": "ResHthree",
    "h4-recovery": "ResHfour",
}
# Forbidden stale phrases in README (a valid experiment must not read as unrun).
FORBIDDEN_README = [
    "have not been run",
    "[pending] under a DRAFT watermark",
    "H1–H4 stay pending",
    "H1-H4 stay pending",
]


def _load(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def _macros(text: str) -> dict[str, str]:
    """Parse ``\\newcommand{\\Name}{value}`` pairs from a generated .tex file."""
    return dict(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}\{(.*?)\}", text))


def _to_float(s: str) -> float | None:
    """Numeric value of a macro body, tolerating a trailing LaTeX percent sign."""
    try:
        return float(s.replace("\\%", "").replace("%", "").strip())
    except ValueError:
        return None


def check_intervals() -> list[str]:
    """Stage 2A: verify the H2 Wilson / H3-H4 bootstrap interval macros are complete and ordered.

    All scientific values are read from the generated outputs (results.tex, analysis.tex);
    nothing is hard-coded here.
    """
    errs: list[str] = []
    if not ANALYSIS.exists():
        return [f"missing generated {ANALYSIS.relative_to(ROOT)} (run `make analysis`)"]
    res = _macros(GENERATED.read_text(encoding="utf-8"))
    an = _macros(ANALYSIS.read_text(encoding="utf-8"))

    def num(store: dict[str, str], name: str) -> float | None:
        return _to_float(store[name]) if name in store else None

    # H2: every class row carries a lower+upper Wilson bound for critic (C) and gate (D),
    # ordered lo <= point <= hi against the results.tex point estimate.
    for key in H2_KEYS:
        for arm in ("C", "G"):
            lo_name, hi_name = f"HtwoCI{key}{arm}Lo", f"HtwoCI{key}{arm}Hi"
            pt_name = f"HtwoDet{key}{arm}"
            for nm in (lo_name, hi_name):
                if nm not in an:
                    errs.append(f"H2 interval macro \\{nm} missing from analysis.tex")
                elif "\\pending" in an[nm]:
                    errs.append(f"H2 interval macro \\{nm} is \\pending")
            lo, hi, pt = num(an, lo_name), num(an, hi_name), num(res, pt_name)
            if lo is not None and hi is not None and lo > hi:
                errs.append(f"H2 {key}{arm}: lower {lo} exceeds upper {hi}")
            if pt is not None and lo is not None and lo > pt + 1e-9:
                errs.append(f"H2 {key}{arm}: lower {lo} exceeds point {pt}")
            if pt is not None and hi is not None and pt > hi + 1e-9:
                errs.append(f"H2 {key}{arm}: point {pt} exceeds upper {hi}")

    # H3/H4: each paper-facing residual-loss point has a bootstrap lower+upper bound, ordered.
    for base in RESIDUAL_MACROS:
        lo_name, hi_name = f"{base}Lo", f"{base}Hi"
        for nm in (lo_name, hi_name):
            if nm not in an:
                errs.append(f"residual interval macro \\{nm} missing from analysis.tex")
            elif "\\pending" in an[nm]:
                errs.append(f"residual interval macro \\{nm} is \\pending")
        lo, hi, pt = num(an, lo_name), num(an, hi_name), num(res, base)
        if lo is not None and hi is not None and lo > hi:
            errs.append(f"{base}: lower {lo} exceeds upper {hi}")
        # Percentile bootstrap of the mean brackets the sample mean; enforce ordering.
        if pt is not None and lo is not None and lo > pt + 1e-6:
            errs.append(f"{base}: lower {lo} exceeds point {pt}")
        if pt is not None and hi is not None and pt > hi + 1e-6:
            errs.append(f"{base}: point {pt} exceeds upper {hi}")

    # Macro count matches the table: 8 classes x 2 arms x 2 bounds = 32 H2 interval macros.
    n_h2 = sum(1 for k in an if k.startswith("HtwoCI"))
    if n_h2 != len(H2_KEYS) * 4:
        errs.append(f"expected {len(H2_KEYS) * 4} H2 interval macros, found {n_h2}")
    return errs


# Documented LaTeX escape map, re-derived here (stdlib-only, no analysis import) so the check
# is an INDEPENDENT verification that the paper's excerpt matches the committed source. Must
# stay in sync with analysis/transcript.py ESCAPES.
_TX_ESCAPES = [
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
    ("−", "$-$"),
    ("≈", "$\\approx$"),
    ("×", "$\\times$"),
]


def _tx_escape(text: str) -> str:
    for src, dst in _TX_ESCAPES:
        text = text.replace(src, dst)
    return text


def _tx_body(excerpt: str) -> str:
    lines = excerpt.split("\n")
    out = []
    for i, ln in enumerate(lines):
        esc = _tx_escape(ln) if ln else "~"
        out.append(esc + ("\\\\" if i < len(lines) - 1 else ""))
    return "\n".join(out)


def check_transcript() -> list[str]:
    """Stage 2B: the paper's transcript excerpt is traceable, hash-verified, and byte-for-byte
    the committed source under the documented escapes."""
    errs: list[str] = []
    if not TRANSCRIPT_PROV.exists() or not TRANSCRIPT_TEX.exists():
        return ["transcript provenance/tex missing (run `make analysis`)"]
    prov = _load(TRANSCRIPT_PROV)
    excerpt = prov.get("excerpt", "")
    # Hash integrity: stored digest matches the excerpt bytes.
    digest = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
    if digest != prov.get("excerpt_sha256"):
        errs.append("transcript excerpt SHA-256 does not match stored provenance hash")
    tex = TRANSCRIPT_TEX.read_text(encoding="utf-8")
    # Byte-for-byte: the independently escaped excerpt body must appear verbatim in the .tex.
    if _tx_body(excerpt) not in tex:
        errs.append("paper transcript body does not match escaped committed excerpt")
    # Traceability: run id (LaTeX-escaped) and episode seed appear in the generated caption.
    if _tx_escape(str(prov.get("run_id", ""))) not in tex:
        errs.append("transcript.tex missing provenance run_id")
    if str(prov.get("episode_seed", "")) not in tex:
        errs.append("transcript.tex missing provenance episode_seed")
    return errs


def check() -> list[str]:
    errs: list[str] = []
    manifest = _load(STATUS)
    valid = {e["experiment"]: e for e in manifest["valid_experiments"]}
    invalid_shas = {r["commit_sha"] for r in manifest["invalid_runs_retained_for_audit"]}
    generated = GENERATED.read_text(encoding="utf-8")

    # 1. Every primary experiment is valid + ingested in the manifest, with full provenance.
    for exp in sorted(PRIMARY):
        if exp not in valid:
            errs.append(f"{exp}: not present as a valid experiment in {STATUS.name}")
            continue
        e = valid[exp]
        if e.get("validity") != "VALID":
            errs.append(f"{exp}: validity != VALID in manifest")
        ref = DATA / exp / "reference_summary.json"
        if not ref.exists():
            errs.append(f"{exp}: missing ingested {ref.relative_to(ROOT)}")
            continue
        prov = _load(ref).get("provenance", {})
        missing = [f for f in PROV_FIELDS if not prov.get(f) and prov.get(f) != 0]
        if missing:
            errs.append(f"{exp}: incomplete provenance, missing {missing}")
        if "instrumentation" not in prov:
            errs.append(f"{exp}: provenance lacks the 'instrumentation' key")
        # 2. Manifest SHA agrees with the ingested summary's provenance SHA.
        if prov.get("sha") and e.get("commit_sha") and prov["sha"] != e["commit_sha"]:
            errs.append(f"{exp}: manifest SHA {e['commit_sha']} != ingested SHA {prov['sha']}")
        # 3. No ingested summary carries an invalid-run SHA.
        if prov.get("sha") in invalid_shas:
            errs.append(f"{exp}: ingested SHA {prov['sha']} is an INVALID run")

    # 4. Every primary experiment has a non-pending Res<Cap> macro.
    for exp, name in RES_MACRO.items():
        m = re.search(rf"\\newcommand\{{\\{name}\}}\{{(.*?)\}}", generated)
        if not m:
            errs.append(f"{exp}: macro \\{name} not found in generated results")
        elif "\\pending" in m.group(1):
            errs.append(f"{exp}: macro \\{name} is still \\pending")

    # 5. No generated comment says H1-H4 are awaiting execution.
    if re.search(r"pending until fired", generated):
        errs.append("generated results.tex still says 'pending until fired'")

    # 6. README must not claim H1-H4 are unrun.
    readme = README.read_text(encoding="utf-8")
    for phrase in FORBIDDEN_README:
        if phrase in readme:
            errs.append(f"README contains stale phrase: {phrase!r}")

    # 7. Stage 2A: statistical interval macros are complete, non-pending, and ordered.
    errs += check_intervals()

    # 8. Stage 2B: the transcript excerpt is hash-verified and matches the committed source.
    errs += check_transcript()

    return errs


def main() -> int:
    errs = check()
    if errs:
        print("CLAIM CONSISTENCY: FAIL")
        for e in errs:
            print(f"  - {e}")
        return 1
    print("CLAIM CONSISTENCY: OK (primary H1-H4 valid+ingested+non-pending; provenance complete)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
