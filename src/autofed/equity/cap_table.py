from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from autofed.accounting.transaction import TransactionType

if TYPE_CHECKING:
    from autofed.accounting.ledger import Ledger


@dataclass
class EquityCapTable:
    """Firm ownership and simple cash-for-share trades at a posted equity price."""

    shares: dict[str, dict[str, int]] = field(default_factory=dict)
    posted_share_prices: dict[str, float] = field(default_factory=dict)

    def total_shares(self, firm_id: str) -> int:
        return sum(self.shares.get(firm_id, {}).values())

    def transfer_shares(
        self,
        firm_id: str,
        seller: str,
        buyer: str,
        quantity: int,
        ledger: Ledger,
        tick: int,
    ) -> None:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        price = self.posted_share_prices.get(firm_id)
        if price is None or price <= 0:
            raise ValueError(f"missing share price for {firm_id!r}")
        held = self.shares.setdefault(firm_id, {}).get(seller, 0)
        if held < quantity:
            raise ValueError("seller does not hold enough shares")
        total = quantity * price

        ledger.post_transfer(
            tick,
            buyer,
            seller,
            total,
            memo=f"equity trade {firm_id} x{quantity}",
            tx_type=TransactionType.TRANSFER,
        )
        self.shares[firm_id][seller] = held - quantity
        self.shares[firm_id][buyer] = self.shares[firm_id].get(buyer, 0) + quantity
