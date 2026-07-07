"""Exercise the live arm path deterministically at $0 with fakes (brief §1.1).

The real clients need the anthropic SDK + a key; FakeAgent/FakeCritic drive the
whole ``apply_arm_live`` structure so every arm and branch is covered in CI without
spend. We assert structural invariants that must hold on the live path just as on
the mock: arm C blocks payload-visible defects, arm D never lets a substituted value
be anything but the buffer's clean price, arm E is the oracle, and refusals are
carried as their own class (never a defect).
"""

from __future__ import annotations

import random

from sarc_dq.agent.base import AgentDecision
from sarc_dq.gate import GovernedBuffer, PreActionGate
from sarc_dq.live_arms import FakeAgent, FakeCritic, apply_arm_live, make_live
from sarc_dq.substrate import make_episode
from sarc_dq.taxonomy import TAXONOMY_V0, get


def _run(arm: str, cls_name: str, agent=None, critic=None):
    cls = get(cls_name)
    seed = (20260707 * 1_000_003 + 3) & 0x7FFFFFFF
    episode = make_episode(seed, 3)
    inj = cls.inject(episode.clean_price_record(), episode, random.Random(seed + 1))
    evidence = inj.evidence_set()
    buf = GovernedBuffer({episode.sku: episode.true_unit_cost})
    return episode, apply_arm_live(
        arm,
        episode,
        evidence,
        corrupted=True,
        gate=PreActionGate(buffer=buf),
        velocity=0.5,
        rng=random.Random(seed + 2),
        tau_m=0.005,
        agent=agent or FakeAgent(),
        critic=critic or FakeCritic(),
    )


def test_all_arms_all_classes_run_live_path() -> None:
    for cls in TAXONOMY_V0:
        for arm in ("A", "B", "C", "D", "E", "F"):
            _, o = _run(arm, cls.name)
            assert o.arm == arm
            assert o.outcome_class in ("ok", "refusal", "error")
            if o.completed:
                assert o.order_qty is not None and o.loss is not None


def test_arm_c_blocks_payload_visible_defect() -> None:
    # cross_source_contradiction is payload-visible: the critic must flag & block.
    _, o = _run("C", "cross_source_contradiction")
    assert o.detected and not o.completed and o.response == "block"


def test_arm_c_blind_to_metadata_borne() -> None:
    # stale_master_data is metadata-borne: a payload-only critic cannot see it.
    _, o = _run("C", "stale_master_data")
    assert o.completed and not o.detected  # admits — the H2 asymmetry


def test_arm_e_is_oracle() -> None:
    episode, o = _run("E", "stale_master_data")
    assert o.believed_price == episode.true_unit_cost and o.response == "oracle"


def test_arm_d_substitute_uses_buffer_price() -> None:
    episode, o = _run("D", "stale_master_data")
    if o.substituted:
        assert o.believed_price == episode.true_unit_cost


class _RefusingAgent:
    model = "fake:refuser"

    def decide(self, episode, price_record, *, advisory=False, prompt_variant="naive"):
        return AgentDecision(order_qty=0.0, transcript="", outcome="refusal")


def test_refusal_is_not_a_defect() -> None:
    _, o = _run("A", "stale_master_data", agent=_RefusingAgent())
    assert o.outcome_class == "refusal" and not o.completed and not o.material


def test_make_live_fake_returns_pair() -> None:
    agent, critic = make_live(fake=True)
    assert agent.model.startswith("fake") and critic.model.startswith("fake")
