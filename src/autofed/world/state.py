from __future__ import annotations

from dataclasses import dataclass, field

from autofed.accounting.ledger import Ledger


@dataclass
class WorldState:
    """Authoritative economic state (money via ledger; goods on firm shelves)."""

    ledger: Ledger
    inventory: dict[str, dict[str, int]] = field(default_factory=dict)
    employment: dict[str, str] = field(default_factory=dict)
    # Good id -> unit price (single-seller MVP).
    posted_unit_prices: dict[str, float] = field(default_factory=dict)

    def firm_inventory(self, firm_id: str, good_id: str) -> int:
        return self.inventory.get(firm_id, {}).get(good_id, 0)

    def add_inventory(self, firm_id: str, good_id: str, delta: int) -> None:
        if firm_id not in self.inventory:
            self.inventory[firm_id] = {}
        cur = self.inventory[firm_id].get(good_id, 0)
        new = cur + delta
        if new < 0:
            raise ValueError(f"inventory would go negative: {firm_id}/{good_id} {cur} + {delta}")
        self.inventory[firm_id][good_id] = new


def demo_world() -> WorldState:
    """Small two-household, one-firm economy; CB nets to -1200 (private +1200)."""
    ledger = Ledger(
        {
            "cb": -1200.0,
            "firm": 1000.0,
            "hh_0": 100.0,
            "hh_1": 100.0,
        }
    )
    return WorldState(
        ledger=ledger,
        inventory={"firm": {"food": 100}},
        employment={"hh_0": "firm", "hh_1": "firm"},
        posted_unit_prices={"food": 10.0},
    )
