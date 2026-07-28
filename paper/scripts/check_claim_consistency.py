"""Fail CI if the manuscript, macros, and status records drift apart (reviewer item #14).

Checks machine-readable invariants (plus a few high-value forbidden stale phrases) so that
a valid experiment can never silently become ``[pending]`` in the paper, an invalid run can
never be ingested, and provenance can never be incomplete. Deterministic; no API calls.

Run: ``python paper/scripts/check_claim_consistency.py`` (also wired as ``make check-claims``
and run in CI). Exits non-zero with a list of violations.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "paper" / "data"
STATUS = ROOT / "reports" / "experiment_status.json"
GENERATED = ROOT / "paper" / "generated" / "results.tex"
README = ROOT / "README.md"

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
