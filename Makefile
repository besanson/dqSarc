LINT_PATHS = src tests benchmarks

.PHONY: install test lint format-check format typecheck quality smoke reproduce verify \
        gigo-reproduce gigo-verify calibrate calibrate-check paper clean

install:
	pip install -e ".[dev]"

test:
	python -m pytest -q

lint:
	ruff check $(LINT_PATHS)

format-check:
	ruff format --check $(LINT_PATHS)

format:
	ruff check --fix $(LINT_PATHS)
	ruff format $(LINT_PATHS)

typecheck:
	mypy src/sarc_dq benchmarks

quality: lint format-check typecheck test

# Phase 0 smoke test (HARD STOP GATE). With no ANTHROPIC_API_KEY this runs the
# deterministic mock agent + mock judge — a $0 pipeline dry-run, clearly
# watermarked as such in the report. Export ANTHROPIC_API_KEY and pass
# --arm live to run the real 200-episode experiment.
smoke:
	python -m benchmarks.phase0_smoke --out reports/SMOKE_TEST.md

# `reproduce` / `verify` become meaningful once GIGO-Bench is frozen (Phase 3).
# In Phase 0 they alias the smoke pipeline so the make targets exist from day one.
reproduce: smoke

verify:
	python -m benchmarks.phase0_smoke --verify reports/reference_smoke.json

# GIGO-Bench (Part 3, frozen). reproduce runs the full class×rate×arm matrix;
# verify re-runs and checks per-cell tolerances against the committed reference.
gigo-reproduce:
	python -m benchmarks.gigo.reproduce --out artifacts/gigo_summary.json

gigo-verify:
	python -m benchmarks.gigo.reproduce --verify benchmarks/gigo/reference_summary.json

# Regenerate the research-calibrated taxonomy (v1 YAML + CALIBRATION.md + veto screen).
calibrate:
	python scripts/calibrate_taxonomy.py

# CI: fail if the committed calibration artifacts are stale.
calibrate-check:
	python scripts/calibrate_taxonomy.py --check

# Regenerate the paper's result macros from all reference_summary.json files and
# compile (needs a LaTeX toolchain; CI uses xu-cheng/latex-action).
paper:
	python paper/scripts/make_macros.py
	$(MAKE) -C paper

# Self-contained, submission-ready arXiv source (macros inlined; DRAFT watermark,
# banner, and verify markers stripped). Run only when claims are signed off.
arxiv:
	python paper/scripts/ingest_results.py
	python paper/scripts/make_macros.py
	python paper/scripts/make_arxiv.py
	@echo "arXiv source: paper/arxiv/sarc-dq.tex (single file; compile with pdflatex x2)"

clean:
	rm -rf artifacts dist build .pytest_cache .mypy_cache .ruff_cache *.egg-info
