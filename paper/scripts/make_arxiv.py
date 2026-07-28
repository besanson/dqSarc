"""Produce a self-contained, submission-ready arXiv source from the working paper.

Reads ``paper/sarc-dq.tex`` and produces ``paper/arxiv/sarc-dq.tex`` plus every figure it
references, so the ``paper/arxiv`` tree compiles on its own with no dependency on the
repository source layout. Specifically it:

  1. inlines all generated macro/content files (``generated/results.tex``,
     ``generated/analysis.tex``, ``generated/transcript.tex``) in place of their ``\\input``;
  2. strips the working-only DRAFT watermark and the red author-review banner;
  3. copies every referenced figure (``figures/analysis/*.pdf``) into
     ``paper/arxiv/figures/analysis/`` at the same relative path the TeX uses;
  4. fails if any generated file is missing, any referenced figure is missing, or any
     ``\\input{generated/...}`` survives inlining;
  5. writes a deterministic upload manifest (``paper/arxiv/MANIFEST.txt``).

Re-runnable and deterministic. It removes the watermark, so run it only when claims are
signed off. Labels, citations, macros, appendix content, and figure paths are preserved.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"
SRC = PAPER / "sarc-dq.tex"
ARXIV = PAPER / "arxiv"
OUT = ARXIV / "sarc-dq.tex"
MANIFEST = ARXIV / "MANIFEST.txt"
# Generated files inlined in place of their \input, in the order they appear.
GENERATED = ("results.tex", "analysis.tex", "transcript.tex")


def build_tex() -> str:
    tex = SRC.read_text(encoding="utf-8")

    # 1. Inline every generated file (fail loudly if one is missing).
    for name in GENERATED:
        path = PAPER / "generated" / name
        if not path.exists():
            raise FileNotFoundError(f"generated file not found: {path.relative_to(ROOT)}")
        body = path.read_text(encoding="utf-8").rstrip("\n")
        needle = f"\\input{{generated/{name}}}"
        if needle not in tex:
            raise RuntimeError(f"expected {needle} in {SRC.name}; cannot inline {name}")
        tex = tex.replace(needle, body)

    # 2. Drop the DRAFT watermark (definition + shipout hook).
    tex = re.sub(
        r"% Robust DRAFT watermark.*?\\AddToShipoutPictureFG\{\\DraftMark\}\n",
        "",
        tex,
        flags=re.DOTALL,
    )
    # graphicx stays (needed for \includegraphics); drop its watermark-referencing comment
    # so no stray "DRAFT" mention survives in the camera-ready source.
    tex = tex.replace(
        "\\usepackage{graphicx} % \\rotatebox for the DRAFT watermark",
        "\\usepackage{graphicx} % \\includegraphics + \\rotatebox",
    )
    # 3. Remove the red author-review banner from \date{...} and tidy the dangling break.
    tex = re.sub(r"\n\s*\\textcolor\{red\}\{\\textbf\{DRAFT.*?\}\}", "", tex, flags=re.DOTALL)
    tex = re.sub(r"\\today\s*\\\\\[2pt\]\s*\}", r"\\today}", tex)

    # 4. No \input{generated/...} may survive.
    leftover = re.findall(r"\\input\{generated/[^}]*\}", tex)
    if leftover:
        raise RuntimeError(f"unresolved generated \\input remain: {leftover}")
    return tex


def copy_figures(tex: str) -> list[str]:
    """Copy every referenced figure into the arxiv tree at its exact relative path."""
    rels = sorted(set(re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", tex)))
    copied: list[str] = []
    for rel in rels:
        rel_path = rel if rel.lower().endswith(".pdf") else rel + ".pdf"
        src = PAPER / rel_path
        if not src.exists():
            raise FileNotFoundError(f"referenced figure missing: {src.relative_to(ROOT)}")
        dst = ARXIV / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        copied.append(rel_path)
    return copied


def main() -> int:
    ARXIV.mkdir(parents=True, exist_ok=True)
    # Deterministic clean slate for the figures tree (avoid stale leftovers).
    fig_root = ARXIV / "figures"
    if fig_root.exists():
        shutil.rmtree(fig_root)

    tex = build_tex()
    OUT.write_text(tex, encoding="utf-8")
    figures = copy_figures(tex)

    # Mandatory upload files (compilation inputs): the single .tex + the figure PDFs.
    upload = sorted(["sarc-dq.tex", *figures])
    MANIFEST.write_text(
        "# arXiv upload manifest (mandatory compilation files).\n"
        "# MANIFEST.txt itself is an AUDIT file and need not be uploaded.\n"
        + "\n".join(upload)
        + "\n",
        encoding="utf-8",
    )

    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes)")
    print(f"copied {len(figures)} figures into {fig_root.relative_to(ROOT)}")
    checks = {
        "watermark shipout hook removed": "\\AddToShipoutPictureFG{\\DraftMark}" not in tex,
        "red DRAFT banner removed": "\\textcolor{red}{\\textbf{DRAFT" not in tex,
        "no verify markers remain": "\\verifyc" not in tex,
        "macros inlined (no generated \\input)": "\\input{generated/" not in tex,
        "appendix preserved (app:analysis)": "app:analysis" in tex,
        "document complete": "\\end{document}" in tex,
    }
    for msg, ok in checks.items():
        print(f"  [{'ok' if ok else 'FAIL'}] {msg}")
    print(f"manifest ({len(upload)} mandatory upload files) -> {MANIFEST.relative_to(ROOT)}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
