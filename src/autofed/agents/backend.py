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
    """Deterministic policy: legacy single-firm demo or multi-entity from world metadata."""

    __slots__ = ("_wage", "_purchase_units", "_consumer_good_priority")

    def __init__(
        self,
        wage: float = 50.0,
        purchase_units: int = 1,
        consumer_good_priority: tuple[str, ...] = ("bread", "food", "flour"),
    ) -> None:
        self._wage = wage
        self._purchase_units = purchase_units
        self._consumer_good_priority = consumer_good_priority

    def plan_tick(self, world: WorldState, tick: int) -> TickPlan:
        _ = tick
        if world.household_ids:
            return self._multi_plan(world)
        firm = "firm"
        if not world.firm_is_active(firm):
            return TickPlan()
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

    def _wage_for_household(self, world: WorldState, hh: str) -> float:
        p = world.persona(hh)
        mult = 0.88 + 0.24 * (1.0 - p.risk_aversion)
        if p.goals.primary == "status":
            mult += 0.05
        return self._wage * mult

    def _purchase_units_for_household(self, world: WorldState, hh: str, good: str) -> int:
        p = world.persona(hh)
        price = float(world.posted_unit_prices.get(good, 0.0))
        cash = float(world.ledger.cash.get(hh, 0.0))
        risk_scale = 0.55 + 0.45 * (1.0 - p.risk_aversion)
        u = max(0, int(round(self._purchase_units * risk_scale)))
        if p.goals.primary == "growth" and price > 0 and cash >= 2.0 * price * max(1, u):
            u += 1
        if p.goals.primary == "stability":
            u = min(u, self._purchase_units)
        if p.goals.min_consumption_units is not None:
            u = max(u, p.goals.min_consumption_units)
        if price <= 0:
            return 0
        max_afford = int(cash // price)
        return max(0, min(u, max_afford))

    def _multi_plan(self, world: WorldState) -> TickPlan:
        wages: list[WagePayment] = []
        sales: list[GoodsSale] = []
        for hh in world.household_ids:
            firm = world.employment.get(hh)
            if firm and world.firm_is_active(firm):
                wages.append(WagePayment(firm, hh, self._wage_for_household(world, hh)))
            good = self._pick_consumer_good(world)
            if firm and world.firm_is_active(firm) and good:
                price = world.posted_unit_prices[good]
                qty = self._purchase_units_for_household(world, hh, good)
                if qty > 0:
                    sales.append(GoodsSale(hh, firm, good, qty, price))
        return TickPlan(wages=tuple(wages), sales=tuple(sales))

    def _pick_consumer_good(self, world: WorldState) -> str | None:
        for gid in self._consumer_good_priority:
            if gid in world.posted_unit_prices:
                return gid
        return next(iter(world.posted_unit_prices), None)
