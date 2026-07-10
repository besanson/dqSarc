"""Running spend ledger against the $1000 envelope.

Sums ``total_usd`` across every committed ``results/<exp>-live`` summary (plus the
Phase 0 pilot) and reports the total against the cap. Every VERIFICATION report must
paste this output, computed BEFORE any tag is pushed (autonomous-mode brief, item 3).

    python scripts/spend_ledger.py

Reads committed branches via ``git show`` so it reflects the true on-branch state,
not the working tree. Exit code 1 if the total meets or exceeds the envelope.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

ENVELOPE_USD = 1000.0
PHASE0_USD = 5.13  # 0a+0b+0c, from reports/PHASE0_CLOSEOUT.md (frozen)
EXPERIMENTS = (
    "h1-full",
    "h1-ladder",
    "h2-detection",
    "h3-frontier",
    "h4-recovery",
    "ablations",
    "tier2-validation",
)


def _summary(exp: str) -> dict[str, Any] | None:
    ref = f"origin/results/{exp}-live:reports/exp/{exp}_summary.json"
    try:
        out = subprocess.check_output(["git", "show", ref], text=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return None
    try:
        data: dict[str, Any] = json.loads(out)
        return data
    except json.JSONDecodeError:
        return None


def main() -> int:
    print(f"SPEND LEDGER — envelope ${ENVELOPE_USD:.0f}")
    print(f"  {'phase0 (0a+0b+0c)':28s} ${PHASE0_USD:8.2f}  [frozen pilot]")
    total = PHASE0_USD
    for exp in EXPERIMENTS:
        s = _summary(exp)
        if s is None:
            print(f"  {exp:28s} {'—':>9s}  (not run)")
            continue
        usd = float(s.get("total_usd", 0.0) or 0.0)
        cfg = s.get("config", {})
        tag = f"prompt={cfg.get('prompt_variant')} sampling={cfg.get('sampling')}"
        total += usd
        print(f"  {exp:28s} ${usd:8.2f}  {tag}")
    pct = 100.0 * total / ENVELOPE_USD
    print(f"  {'-' * 40}")
    print(f"  {'RUNNING TOTAL':28s} ${total:8.2f}  ({pct:.1f}% of envelope)")
    if total >= ENVELOPE_USD:
        print("  ENVELOPE EXCEEDED — stop; do not fire.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
