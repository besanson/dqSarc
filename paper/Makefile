# Paper build. `make paper` at the repo root regenerates macros then invokes this.
# CI (.github/workflows/paper.yml) compiles with a full TeX Live via latex-action.

.PHONY: all macros clean
all: sarc-dq.pdf

macros:
	python scripts/make_macros.py

# Two passes so the table/section references resolve.
sarc-dq.pdf: sarc-dq.tex generated/results.tex
	pdflatex -interaction=nonstopmode -halt-on-error sarc-dq.tex
	pdflatex -interaction=nonstopmode -halt-on-error sarc-dq.tex

generated/results.tex:
	python scripts/make_macros.py

clean:
	rm -f sarc-dq.aux sarc-dq.log sarc-dq.out sarc-dq.toc sarc-dq.pdf
