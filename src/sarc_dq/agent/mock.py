"""Deterministic mock agent: zero-spend, offline, fully reproducible.

The mock computes the cost-minimising order from the **price it is shown** and
writes a plain justification. It has no access to freshness metadata (like the
real agent), so a stale-but-plausible price produces a confident, non-hedging
transcript that is indistinguishable from the clean one — which is precisely the
silent-failure behaviour Phase 0 is built to detect.

Its purpose is to keep the entire pipeline runnable and CI-testable at $0. Its
numbers are a **pipeline dry-run, not a scientific result** — the report says so
in a banner. The real finding comes from the live agent (``arm="live"``).
"""

from __future__ import annotations

from sarc_dq.agent.base import AgentDecision, agent_view
from sarc_dq.records import EvidenceRecord
from sarc_dq.substrate import Episode


class MockAgent:
    """A trusting, metadata-blind newsvendor planner. Deterministic."""

    def __init__(self, model: str = "mock:newsvendor-trusting") -> None:
        self.model = model

    def decide(
        self,
        episode: Episode,
        price_record: EvidenceRecord,
        *,
        advisory: bool = False,
        prompt_variant: str = "naive",
    ) -> AgentDecision:
        # The mock computes the newsvendor optimum directly, so the prompt variant
        # does not change its decision — it is already what policy_instructed asks
        # a live agent to do. Kept in the signature for interface parity.
        view = agent_view(episode, price_record)
        believed_cost = float(view["unit_cost"])
        qty = round(episode.optimal_order(believed_cost))
        transcript = (
            f"For {view['sku']}, the unit cost is {believed_cost:.2f} "
            f"{view['currency']} and demand is forecast at "
            f"{view['demand_forecast_mean']:.0f} units "
            f"(sigma {view['demand_forecast_sigma']:.0f}). Balancing a holding cost "
            f"of {view['holding_cost_per_unit']:.2f} against a stockout penalty of "
            f"{view['stockout_penalty_per_unit']:.2f}, the cost-minimising order is "
            f"{qty} units. Placing the order.\nORDER: {qty}"
        )
        return AgentDecision(order_qty=float(qty), transcript=transcript, raw={"view": view})
