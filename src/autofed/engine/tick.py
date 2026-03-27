from __future__ import annotations

from typing import TYPE_CHECKING

from autofed.agents.backend import AgentBackend

if TYPE_CHECKING:
    from autofed.world.state import WorldState


class TickEngine:
    """Runs one deterministic sequence: wages then goods sales (MVP)."""

    __slots__ = ("_backend",)

    def __init__(self, backend: AgentBackend) -> None:
        self._backend = backend

    def step(self, world: WorldState, tick: int) -> None:
        plan = self._backend.plan_tick(world, tick)

        for w in plan.wages:
            world.ledger.post_transfer(
                tick,
                w.firm_id,
                w.household_id,
                w.amount,
                memo=f"wage {w.household_id}",
            )

        for s in plan.sales:
            total = s.quantity * s.unit_price
            world.ledger.post_transfer(
                tick,
                s.buyer_id,
                s.seller_id,
                total,
                memo=f"purchase {s.good_id} x{s.quantity}",
            )
            world.add_inventory(s.seller_id, s.good_id, -s.quantity)

        world.ledger.validate_closed_economy()

    def run(self, world: WorldState, n_ticks: int, start_tick: int = 0) -> None:
        for t in range(start_tick, start_tick + n_ticks):
            self.step(world, t)
