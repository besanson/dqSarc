# SARC-DQ working paper

Build (needs a TeX Live toolchain; CI uses `xu-cheng/latex-action`):

```bash
make paper            # from repo root: regenerate macros + compile → paper/sarc-dq.pdf
# or, inside paper/:
python scripts/make_macros.py && make
```

**No result value is hand-authored.** `scripts/make_macros.py` reads every
`paper/data/**/reference_summary.json` and emits `generated/results.tex`; a value
that does not exist yet renders `\pending{<id>}` → "**--** `[pending: id]`". The
Phase 0 pilot numbers are real (from the `results/*-live` branches, vendored to
`paper/data/phase0/`); H1–H4 render `[pending]` until the Part-4 workflows are fired.

Every page carries a **DRAFT** watermark until claims sign-off. Citations marked
`⟨VERIFY⟩` are unverified pending web access and must be confirmed before the
watermark is lifted.
