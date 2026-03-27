from __future__ import annotations

from autofed.agents.backend import ManualAgentBackend
from autofed.agents.plan import TickPlan
from autofed.world.state import WorldState


class StubLLMAgentBackend:
    """Placeholder LLM backend: enforces call budget then defers to manual policy."""

    __slots__ = ("_inner",)

    def __init__(self, inner: ManualAgentBackend | None = None) -> None:
        self._inner = inner or ManualAgentBackend()

    def plan_tick(self, world: WorldState, tick: int) -> TickPlan:
        if world.llm_budget is not None:
            world.llm_budget.consume(1)
        return self._inner.plan_tick(world, tick)
