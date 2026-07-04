"""SARC-DQ — runtime data-quality gating for agentic AI.

The third SARC pillar (SARC = obligations; Green SARC = cost/carbon; **SARC-DQ =
evidence quality**). Same thesis: enforcement *placement* beats model
intelligence. A data-quality predicate family + Pre-Action Gate wraps agent
retrieval, with downstream-only remediation (never writes to source systems).

This release covers the repository scaffold and the **Phase 0 smoke test** — the
first hard-stop gate, which asks whether the silent-failure effect exists at all.
Phases 1+ (taxonomy, predicate schema, harness, GIGO-Bench) land behind their
own gates.
"""

from __future__ import annotations

__version__ = "0.1.0"

from sarc_dq.config import RunConfig
from sarc_dq.records import EvidenceRecord, RecordMetadata
from sarc_dq.substrate import Episode, make_episode

__all__ = [
    "__version__",
    "RunConfig",
    "EvidenceRecord",
    "RecordMetadata",
    "Episode",
    "make_episode",
]
