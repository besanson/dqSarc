LINT_PATHS = src tests benchmarks

.PHONY: install test lint format-check format typecheck quality smoke reproduce verify clean

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

clean:
	rm -rf artifacts dist build .pytest_cache .mypy_cache .ruff_cache *.egg-info
