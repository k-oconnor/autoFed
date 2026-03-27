from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from autofed.agents.plan import GoodsSale, TickPlan, WagePayment

if TYPE_CHECKING:
    from autofed.world.state import WorldState


class AgentBackend(Protocol):
    def plan_tick(self, world: WorldState, tick: int) -> TickPlan:
        """Return validated-intent plan for this tick (engine enforces feasibility)."""
        ...


class ManualAgentBackend:
    """Deterministic policy for the Phase 0 demo."""

    __slots__ = ()

    def plan_tick(self, world: WorldState, tick: int) -> TickPlan:
        _ = tick
        firm = "firm"
        food = "food"
        price = world.posted_unit_prices[food]
        return TickPlan(
            wages=(
                WagePayment(firm, "hh_0", 50.0),
                WagePayment(firm, "hh_1", 50.0),
            ),
            sales=(
                GoodsSale("hh_0", firm, food, 1, price),
                GoodsSale("hh_1", firm, food, 1, price),
            ),
        )
