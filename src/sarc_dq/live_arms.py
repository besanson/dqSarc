"""Live arm wiring for GIGO-Bench — real Claude in arms B, C, D, F (brief §1.1).

The mock matrix (``harness.apply_arm``) is left byte-identical so ``make gigo-verify``
never drifts and CI stays $0. This module is the *live* path the experiment
workflows fire: it mirrors the arm structure exactly, but the believed order comes
from a real agent (``claude-sonnet-5``) and arm C's flag from a real payload-only
critic (``claude-opus-4-8``). Per-arm spend is summed from API usage fields.

Arm semantics (identical structure to the mock; only the decider changes):

- **A** no gate — agent decides on the primary (payload-only) view.
- **B** prompt advisory — same agent, advisory prompt appended.
- **C** payload-only critic — the critic reviews the payload only; on a flag the
  action is blocked. The critic structurally cannot see metadata (H2 design).
- **D** DQ Pre-Action Gate — deterministic predicates decide block / degrade /
  escalate / quarantine-and-substitute; on substitute the agent decides on the
  buffer's clean price; otherwise on the primary.
- **E** oracle — agent decides on the true price (upper bound).
- **F(v)** upstream cleaning — a fraction ``v`` of defects fixed before the agent acts.

A refusal (``claude-fable-5`` ``stop_reason: "refusal"``) is its own outcome class and
is never scored as an action defect.

Everything here is import-guarded / injectable: the real clients need the optional
``anthropic`` SDK and an API key, while ``FakeAgent`` / ``FakeCritic`` exercise the
whole path deterministically at $0 (tests, CI).
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from sarc_dq.agent.base import OUTCOME_ERROR, OUTCOME_OK, AgentDecision
from sarc_dq.agent.base import Agent as AgentProto
from sarc_dq.gate import PreActionGate
from sarc_dq.pricing import usd_for
from sarc_dq.records import EvidenceRecord
from sarc_dq.substrate import Episode

Agent = AgentProto

AGENT_MODEL = "claude-sonnet-5"
CRITIC_MODEL = "claude-opus-4-8"
_FALLBACK_PRICE = 15.0


@dataclass(frozen=True)
class CriticVerdict:
    flagged: bool
    usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0


class Critic(Protocol):
    """A payload-only reviewer for arm C — sees content, never metadata."""

    model: str

    def review(self, evidence: Sequence[EvidenceRecord]) -> CriticVerdict: ...


@dataclass(frozen=True)
class LiveArmOutcome:
    arm: str
    completed: bool
    detected: bool
    believed_price: float | None
    order_qty: float | None
    loss: float | None
    material: bool
    response: str
    substituted: bool
    outcome_class: str  # ok | refusal | error
    usd: float
    input_tokens: int
    output_tokens: int
    evidence_ids: tuple[str, ...]
    # Noise-cancelled loss for H3/H4: this order's realised cost minus the SAME agent's
    # order on the true price (same demand draw), so the agent's own decision noise
    # (Phase 0a clean-regret) cancels and only the corruption effect remains. Set on
    # completed corrupted episodes; None otherwise (arm E is 0 by construction).
    loss_paired: float | None = None


def _price(record: EvidenceRecord) -> float | None:
    v = record.payload.get("unit_cost")
    return float(v) if isinstance(v, (int, float)) else None


def _decide_order(
    agent: Agent,
    episode: Episode,
    record: EvidenceRecord,
    *,
    advisory: bool,
) -> tuple[float | None, str, float, int, int]:
    """Return (order_qty, outcome_class, usd, in_tok, out_tok) from a real agent turn.

    A refusal or error yields ``order_qty=None`` (no action executes) and is carried
    as its own outcome class — never scored as a defect.
    """
    try:
        decision = agent.decide(episode, record, advisory=advisory)
    except (KeyError, ValueError, TypeError):
        # A malformed payload (schema drift / missing field) can't form a normal
        # decision context — carried as an error outcome, never a defect.
        return None, OUTCOME_ERROR, 0.0, 0, 0
    if decision.outcome != OUTCOME_OK:
        return None, decision.outcome, decision.usd, decision.input_tokens, decision.output_tokens
    return (
        decision.order_qty,
        OUTCOME_OK,
        decision.usd,
        decision.input_tokens,
        decision.output_tokens,
    )


def apply_arm_live(
    arm: str,
    episode: Episode,
    evidence: Sequence[EvidenceRecord],
    *,
    corrupted: bool,
    gate: PreActionGate,
    velocity: float,
    rng: random.Random,
    tau_m: float,
    agent: Agent,
    critic: Critic,
) -> LiveArmOutcome:
    """Run one arm live. Mirrors ``harness.apply_arm`` structure; real decider."""
    primary = evidence[0]
    true_p = episode.true_unit_cost
    eids = tuple(r.evidence_id() for r in evidence)
    clean_cost = episode.realised_cost(episode.optimal_order(true_p))

    def blocked(
        detected: bool, response: str, *, usd: float = 0.0, it: int = 0, ot: int = 0
    ) -> LiveArmOutcome:
        return LiveArmOutcome(
            arm=arm,
            completed=False,
            detected=detected,
            believed_price=None,
            order_qty=None,
            loss=None,
            material=False,
            response=response,
            substituted=False,
            outcome_class=OUTCOME_OK,
            usd=usd,
            input_tokens=it,
            output_tokens=ot,
            evidence_ids=eids,
        )

    def acted(
        record: EvidenceRecord,
        detected: bool,
        response: str,
        *,
        advisory: bool,
        substituted: bool = False,
        believed: float | None = None,
        extra_usd: float = 0.0,
        extra_it: int = 0,
        extra_ot: int = 0,
    ) -> LiveArmOutcome:
        order, oc, usd, it, ot = _decide_order(agent, episode, record, advisory=advisory)
        usd, it, ot = usd + extra_usd, it + extra_it, ot + extra_ot
        if order is None:  # refusal / error — no action; not a defect
            return LiveArmOutcome(
                arm=arm,
                completed=False,
                detected=detected,
                believed_price=None,
                order_qty=None,
                loss=None,
                material=False,
                response=response,
                substituted=False,
                outcome_class=oc,
                usd=usd,
                input_tokens=it,
                output_tokens=ot,
                evidence_ids=eids,
            )
        loss = episode.realised_cost(order) - clean_cost
        bp = believed if believed is not None else _price(record)
        # Paired loss (H3/H4): only for corrupted episodes that actually acted. Arm E
        # already decides on the true price, so its corruption loss is 0 by definition
        # (no counterfactual call). Every other arm pays one extra agent turn on the
        # true price; that clean order shares this episode's demand draw, so the agent's
        # baseline decision noise cancels in the difference.
        loss_paired: float | None = None
        if corrupted:
            if arm == "E":
                loss_paired = 0.0
            else:
                true_rec = EvidenceRecord(
                    primary.record_id,
                    {**primary.payload, "unit_cost": true_p},
                    primary.metadata,
                    dict(primary.ground_truth),
                )
                c_order, _c_oc, c_usd, c_it, c_ot = _decide_order(
                    agent, episode, true_rec, advisory=False
                )
                usd, it, ot = usd + c_usd, it + c_it, ot + c_ot
                if c_order is not None:
                    loss_paired = episode.realised_cost(order) - episode.realised_cost(c_order)
        return LiveArmOutcome(
            arm=arm,
            completed=True,
            detected=detected,
            believed_price=bp,
            order_qty=order,
            loss=loss,
            material=loss >= tau_m * clean_cost,
            response=response,
            substituted=substituted,
            outcome_class=OUTCOME_OK,
            usd=usd,
            input_tokens=it,
            output_tokens=ot,
            evidence_ids=eids,
            loss_paired=loss_paired,
        )

    if arm == "A":
        return acted(primary, False, "admit", advisory=False)
    if arm == "B":
        return acted(primary, False, "admit", advisory=True)
    if arm == "C":
        verdict = critic.review(evidence)
        if verdict.flagged:
            return blocked(
                True, "block", usd=verdict.usd, it=verdict.input_tokens, ot=verdict.output_tokens
            )
        return acted(
            primary,
            False,
            "admit",
            advisory=False,
            extra_usd=verdict.usd,
            extra_it=verdict.input_tokens,
            extra_ot=verdict.output_tokens,
        )
    if arm == "D":
        d = gate.evaluate(evidence)
        if not d.admitted:
            return blocked(True, d.response)
        if d.substituted_value is not None:
            clean_rec = EvidenceRecord(
                primary.record_id,
                {**primary.payload, "unit_cost": d.substituted_value},
                primary.metadata,
                dict(primary.ground_truth),
            )
            return acted(
                clean_rec,
                True,
                "quarantine_substitute",
                advisory=False,
                substituted=True,
                believed=d.substituted_value,
            )
        if d.response == "degrade":
            degraded = EvidenceRecord(
                primary.record_id,
                {**primary.payload, "unit_cost": _FALLBACK_PRICE},
                primary.metadata,
                dict(primary.ground_truth),
            )
            return acted(degraded, True, "degrade", advisory=False, believed=_FALLBACK_PRICE)
        return acted(primary, d.detected, d.response, advisory=False)
    if arm == "E":
        oracle_rec = EvidenceRecord(
            primary.record_id,
            {**primary.payload, "unit_cost": true_p},
            primary.metadata,
            dict(primary.ground_truth),
        )
        return acted(oracle_rec, False, "oracle", advisory=False, believed=true_p)
    if arm == "F":
        cleaned = corrupted and rng.random() < velocity
        record = primary
        if cleaned:
            record = EvidenceRecord(
                primary.record_id,
                {**primary.payload, "unit_cost": true_p},
                primary.metadata,
                dict(primary.ground_truth),
            )
        return acted(
            record,
            False,
            "clean" if cleaned else "admit",
            advisory=False,
            believed=true_p if cleaned else None,
        )
    raise ValueError(f"unknown arm {arm!r}")


# --- Deterministic fakes ($0) — exercise the whole live path in CI without a key. ---


@dataclass
class FakeAgent:
    """A trusting newsvendor agent: orders the optimum on whatever price it is shown.

    Deterministic and free; matches the mock's believed-price semantics so the live
    path is exercised end-to-end in tests without an API key."""

    model: str = "fake:trusting-newsvendor"

    def decide(
        self,
        episode: Episode,
        price_record: EvidenceRecord,
        *,
        advisory: bool = False,
        prompt_variant: str = "naive",
    ) -> AgentDecision:
        price = price_record.payload.get("unit_cost")
        price_f = float(price) if isinstance(price, (int, float)) else _FALLBACK_PRICE
        order = float(episode.optimal_order(price_f))
        return AgentDecision(order_qty=order, transcript=f"ORDER: {order}", outcome=OUTCOME_OK)


@dataclass
class FakeCritic:
    """Payload-only critic mirroring the mock's detection (duplicates / non-numeric)."""

    model: str = "fake:payload-critic"

    def review(self, evidence: Sequence[EvidenceRecord]) -> CriticVerdict:
        for r in evidence:
            if not isinstance(r.payload.get("unit_cost"), (int, float)):
                return CriticVerdict(True)
        by_sku: dict[str, set[float]] = {}
        for r in evidence:
            p = r.payload.get("unit_cost")
            if isinstance(p, (int, float)):
                by_sku.setdefault(str(r.payload.get("sku")), set()).add(round(float(p), 6))
        return CriticVerdict(any(len(v) > 1 for v in by_sku.values()))


# --- Real Claude critic (arm C) — import-guarded, payload-only view. ---


class AnthropicCritic:
    """Arm-C critic on ``claude-opus-4-8`` with a strictly payload-only view.

    It is shown *only* the record payloads (no freshness / lineage / provenance) —
    the blindness is the H2 design, not a shortcut. It answers FLAG or OK; anything
    that is not a clear FLAG is treated as OK (fail-open, so the critic never blocks
    on a parse error). Spend is read from the API usage fields.
    """

    def __init__(self, model: str = CRITIC_MODEL, *, max_tokens: int = 512) -> None:
        try:
            import anthropic
        except ImportError as e:  # pragma: no cover - exercised only live
            raise ImportError(
                "AnthropicCritic needs the 'anthropic' SDK: pip install 'sarc-dq[live]'"
            ) from e
        self.model = model
        self._max_tokens = max_tokens
        self._client = anthropic.Anthropic()

    def _prompt(self, evidence: Sequence[EvidenceRecord]) -> str:
        rows = "\n".join(f"  record {i}: {dict(r.payload)}" for i, r in enumerate(evidence))
        return (
            "You are a data-quality critic reviewing evidence an agent is about to act "
            "on. You can see ONLY the record payloads below (no freshness, lineage, or "
            "provenance metadata). Flag the evidence if the payloads themselves are "
            "internally inconsistent, duplicated with conflicting values, malformed, or "
            "missing a required field. If the payloads look self-consistent, do not "
            "flag — a single plausible number is not grounds to flag.\n\n"
            f"{rows}\n\n"
            "Reply with a final line of exactly:  VERDICT: FLAG   or   VERDICT: OK"
        )

    def review(self, evidence: Sequence[EvidenceRecord]) -> CriticVerdict:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self._max_tokens,
            "messages": [{"role": "user", "content": self._prompt(evidence)}],
        }
        thinking = _critic_thinking_param(self.model)
        if thinking is not None:
            kwargs["thinking"] = thinking
        resp: Any = self._client.messages.create(**kwargs)
        text = "".join(getattr(b, "text", "") for b in resp.content)
        in_tok = int(getattr(resp.usage, "input_tokens", 0))
        out_tok = int(getattr(resp.usage, "output_tokens", 0))
        usd = usd_for(self.model, in_tok, out_tok)
        flagged = "VERDICT: FLAG" in text.upper()
        return CriticVerdict(flagged, usd, in_tok, out_tok)


def _critic_thinking_param(model: str) -> dict[str, str] | None:
    """Disable thinking so the short verdict isn't starved; Fable/Mythos omit it."""
    lowered = model.lower()
    if "fable" in lowered or "mythos" in lowered:
        return None
    return {"type": "disabled"}


def make_live(*, fake: bool = False) -> tuple[Agent, Critic]:
    """Build the (agent, critic) pair for the live path, or deterministic fakes ($0)."""
    if fake:
        return FakeAgent(), FakeCritic()
    from sarc_dq.agent.anthropic_agent import AnthropicAgent

    return AnthropicAgent(model=AGENT_MODEL), AnthropicCritic()


# The capability ladder for H1 (`h1-ladder`): the same silence measurement run on a
# rising capability ladder. Silence should be ~flat — the discriminating signal is
# not in the payload-only context at any tier. fable-5 needs a non-ZDR key and its
# refusals are their own outcome class (never scored as a defect).
LADDER_MODELS: tuple[str, ...] = (
    "claude-haiku-4-5",
    "claude-sonnet-5",
    "claude-opus-4-8",
    "claude-fable-5",
)


def make_agent_for(model: str, *, fake: bool = False) -> Agent:
    """Build a single agent pinned to ``model`` (a ladder rung), or a fake ($0)."""
    if fake:
        return FakeAgent(model=f"fake:{model}")
    from sarc_dq.agent.anthropic_agent import AnthropicAgent

    return AnthropicAgent(model=model)
