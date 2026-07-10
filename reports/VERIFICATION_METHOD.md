# VERIFICATION METHOD (autonomous mode)

How self-verification is done when the human does not review diffs/reports/results.
Each stage writes `reports/VERIFICATION-<date>-<stage>.md` with **literal command
outputs**. A stage passes only if ALL its checks pass; any failure ⇒ stop, commit the
failing report, spend nothing, end (FAILURE PROTOCOL).

## Amended V0 freeze check (supersedes the brief's original)

The frozen files are the Phase 0 record and the original PREREG files. The check is:

> **No modification of existing lines in frozen files** (append-only extension is
> permitted — new sections, new files, dated addenda), **and `make verify` green.**

Concretely, for each frozen path, `git diff <base>..HEAD -- <path>` must show **no
removed or changed existing lines** (additions/new files are allowed). Frozen paths:
`reports/PHASE0*_PREREG.md`, `reports/prereg/<exp>.md` (originals),
`src/sarc_dq/phase0.py`, `.github/workflows/phase0*.yml`, and the Phase 0 config hash
`c8202a18b58754d8` must still verify. Corrections live in `reports/prereg/
ADDENDUM-*.md`, never by editing an original.

## Running spend ledger (required in every VERIFICATION report)

Before any experiment tag is pushed, paste the output of:

    python scripts/spend_ledger.py

It sums `total_usd` across every committed `results/<exp>-live` summary (+ the frozen
Phase 0 pilot) against the **$1000** envelope and exits non-zero if the envelope is
met or exceeded. A stage that would push spend to/over the envelope does not fire.
