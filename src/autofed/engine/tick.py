from __future__ import annotations

from typing import TYPE_CHECKING

from autofed.accounting.transaction import TransactionType
from autofed.agents.backend import AgentBackend
from autofed.markets.clearing import sort_sales_by_market_priority, try_execute_sale
from autofed.world.production import run_batch_production

if TYPE_CHECKING:
    from autofed.world.state import WorldState


class TickEngine:
    """Phased tick runner aligned with spec §8.1 (subset)."""

    __slots__ = ("_backend",)

    def __init__(self, backend: AgentBackend) -> None:
        self._backend = backend

    def step(self, world: WorldState, tick: int) -> None:
        if world.llm_budget is not None:
            world.llm_budget.reset_tick()

        # 1–2 Observation + expectation formation
        world.refresh_output_gap()
        world.update_expectations()

        # 3 Labor market (employment fixed in MVP)
        # 4 Production
        run_batch_production(world)

        # 5–7 Pricing + goods + financial (via plan)
        plan = self._backend.plan_tick(world, tick)
        for pu in plan.price_updates:
            world.apply_price_updates({pu.good_id: pu.price})

        # Goods market before wages (revenue then payroll).
        ordered_sales = sort_sales_by_market_priority(plan.sales, world.good_categories)
        for s in ordered_sales:
            try_execute_sale(world, tick, s)

        for w in plan.wages:
            firm_cash = world.ledger.cash.get(w.firm_id, 0.0)
            paid = min(w.amount, max(0.0, firm_cash))
            if paid > 1e-9:
                world.ledger.post_transfer(
                    tick,
                    w.firm_id,
                    w.household_id,
                    paid,
                    memo=f"wage {w.household_id}",
                    tx_type=TransactionType.WAGE,
                )

        for d in plan.dividends:
            world.ledger.post_transfer(
                tick,
                d.firm_id,
                d.shareholder_id,
                d.amount,
                memo=f"dividend {d.shareholder_id}",
                tx_type=TransactionType.DIVIDEND,
            )

        # 8 Policy (rule-based; uses lagged inflation before this tick's price refresh)
        world.refresh_policy_rate()

        # 9 Accounting validation + price level for next tick
        world.ledger.validate_closed_economy()
        world.refresh_price_level()

        # 10 Governance
        world.governance_step(tick)

    def run(self, world: WorldState, n_ticks: int, start_tick: int = 0) -> None:
        for t in range(start_tick, start_tick + n_ticks):
            self.step(world, t)
