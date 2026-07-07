"""Adversarial zero-write test — executes Proposition 1's load-bearing assumption.

Downstream-only remediation means the gate must *never* write to a source store: it
quarantines-and-substitutes from a governed buffer, leaving the evidence it read
bit-identical. This test injects every corruption class, snapshots the source
evidence, runs the Pre-Action Gate through the arm-D remediation path, and asserts
each source record is unchanged (payload, metadata, and every field). If any class's
remediation mutated a source record, Prop 1 (lineage preservation) would be false.
"""

from __future__ import annotations

import copy
import random

from sarc_dq.gate import GovernedBuffer, PreActionGate
from sarc_dq.harness import apply_arm
from sarc_dq.substrate import make_episode
from sarc_dq.taxonomy import TAXONOMY_V0


def _snapshot(records: tuple) -> list[dict]:
    """Deep, value-level snapshot of each source record (payload + metadata)."""
    snap = []
    for r in records:
        snap.append(
            {
                "record_id": r.record_id,
                "payload": copy.deepcopy(r.payload),
                "metadata": copy.deepcopy(r.metadata),
                "ground_truth": copy.deepcopy(r.ground_truth),
            }
        )
    return snap


def test_gate_never_writes_to_source_across_all_classes() -> None:
    for cls in TAXONOMY_V0:
        for i in range(30):  # enough episodes to hit substitute/block/escalate paths
            seed = (20260707 * 1_000_003 + i) & 0x7FFFFFFF
            episode = make_episode(seed, i)
            inj = cls.inject(episode.clean_price_record(), episode, random.Random(seed + 1))
            evidence = inj.evidence_set()
            before = _snapshot(evidence)

            buf = GovernedBuffer({episode.sku: episode.true_unit_cost})
            gate = PreActionGate(buffer=buf)
            outcome = apply_arm(
                "D",
                episode,
                evidence,
                corrupted=True,
                gate=gate,
                velocity=0.5,
                rng=random.Random(seed + 2),
                tau_m=0.005,
            )

            after = _snapshot(evidence)
            assert after == before, (
                f"{cls.name}: gate mutated a source record (episode {i}) — "
                f"downstream-only remediation violated, Prop 1 assumption broken"
            )
            # A substitution must be sourced from the governed buffer, not written back.
            if outcome.substituted:
                assert outcome.believed_price == episode.true_unit_cost, (
                    f"{cls.name}: substituted value did not come from the governed buffer"
                )


def test_governed_buffer_substitute_is_readonly() -> None:
    buf = GovernedBuffer({"SKU-1": 12.5})
    assert buf.substitute("SKU-1") == 12.5
    assert buf.substitute("absent") is None
    # Reading a substitution must not create or mutate entries.
    assert buf.substitute("absent") is None
