from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LLMCallBudget:
    """Tiered LLM call cap per tick (spec §8.2)."""

    max_per_tick: int
    used_this_tick: int = 0
    total_calls: int = 0

    def reset_tick(self) -> None:
        self.used_this_tick = 0

    def consume(self, n: int = 1) -> None:
        if n <= 0:
            return
        if self.used_this_tick + n > self.max_per_tick:
            msg = f"LLM call budget exceeded: {self.used_this_tick + n} > {self.max_per_tick}"
            raise RuntimeError(msg)
        self.used_this_tick += n
        self.total_calls += n
