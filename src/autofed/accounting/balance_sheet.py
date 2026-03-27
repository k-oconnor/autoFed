from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass
class BalanceSheet:
    """Per-entity balance snapshot (spec §7.1 subset; extend over time)."""

    entity_id: str
    cash: float = 0.0
    deposits: dict[str, float] = field(default_factory=dict)
    inventory: dict[str, float] = field(default_factory=dict)
    loans_payable: float = 0.0
    equity_holdings: dict[str, int] = field(default_factory=dict)

    @property
    def net_worth(self) -> float:
        dep = sum(self.deposits.values())
        inv_val = sum(self.inventory.values())
        return self.cash + dep + inv_val - self.loans_payable

    @classmethod
    def from_ledger_cash(
        cls,
        entity_id: str,
        cash_map: Mapping[str, float],
        *,
        deposits: dict[str, float] | None = None,
        inventory: dict[str, float] | None = None,
        loans_payable: float = 0.0,
        equity_holdings: dict[str, int] | None = None,
    ) -> BalanceSheet:
        return cls(
            entity_id=entity_id,
            cash=float(cash_map.get(entity_id, 0.0)),
            deposits=dict(deposits or {}),
            inventory=dict(inventory or {}),
            loans_payable=loans_payable,
            equity_holdings=dict(equity_holdings or {}),
        )
