"""Produce a self-contained, submission-ready arXiv source from the working paper.

Reads ``paper/sarc-dq.tex``, inlines ``generated/results.tex`` (so the submission is a
single file with no \\input dependency), and strips the DRAFT scaffolding that must not
appear in a camera-ready:
  - the full-page DRAFT watermark,
  - the red "DRAFT / claims not yet signed off" banner under the title,
  - the ``\\verifyc`` citation-verification superscripts (rendered to nothing).

Writes ``paper/arxiv/sarc-dq.tex``. Re-runnable and deterministic. This is the arXiv
counterpart of ``make final``; it removes the watermark, so run it only when the claims
are signed off (see reports/CLAIMS_CHECKLIST.md).

NOTE: ``\\verifyc`` marked 14 citations for the author to confirm exist before submission.
This script only hides the marker so the PDF is clean; it does NOT verify the references.
Confirm those citations are real before uploading.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "paper" / "sarc-dq.tex"
GEN = ROOT / "paper" / "generated" / "results.tex"
OUT = ROOT / "paper" / "arxiv" / "sarc-dq.tex"


def build() -> str:
    tex = SRC.read_text(encoding="utf-8")
    macros = GEN.read_text(encoding="utf-8")

    # 1. Inline the generated macros in place of the \input, so the file is self-contained.
    tex = tex.replace("\\input{generated/results.tex}", macros.rstrip("\n"))

    # 2. Drop the DRAFT watermark: its definition and the shipout hook.
    tex = re.sub(
        r"% Robust DRAFT watermark.*?\\AddToShipoutPictureFG\{\\DraftMark\}\n",
        "",
        tex,
        flags=re.DOTALL,
    )

    # 3. Neutralise \verifyc (render nothing) rather than delete each call site.
    tex = tex.replace(
        r"\newcommand{\verifyc}{\textsuperscript{$\langle$VERIFY$\rangle$}}",
        r"\newcommand{\verifyc}{}",
    )

    # 4. Remove the red DRAFT banner line from \date{...}.
    tex = re.sub(
        r"\n\s*\\textcolor\{red\}\{\\textbf\{DRAFT\. Claims not yet signed off\..*?\}\}",
        "",
        tex,
        flags=re.DOTALL,
    )
    # Tidy the trailing "\\[2pt]" left dangling in \date after the banner is gone.
    tex = re.sub(r"\\today\s*\\\\\[2pt\]\s*\}", r"\\today}", tex)

    return tex


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(), encoding="utf-8")
    text = OUT.read_text(encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes)")
    # Check the real camera-ready conditions (not bare substrings: the word "pending" and a
    # "% ... watermark" comment are legitimately present and harmless).
    checks = {
        "watermark shipout hook removed": "\\AddToShipoutPictureFG{\\DraftMark}" not in text,
        "red DRAFT banner removed": "Claims not yet signed off" not in text,
        "verifyc renders nothing": "\\newcommand{\\verifyc}{}" in text,
        "no rendered [pending:] in body": "[pending:" not in text.replace(
            "[pending:~#1]", ""  # the \pending definition itself is fine
        ),
        "macros inlined (no \\input)": "\\input{generated/results.tex}" not in text,
        "document complete": "\\end{document}" in text,
    }
    for msg, ok in checks.items():
        print(f"  [{'ok' if ok else 'FAIL'}] {msg}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
