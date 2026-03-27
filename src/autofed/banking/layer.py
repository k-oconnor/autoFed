from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BankingLayer:
    """Optional inside-money bookkeeping (spec §5.4 sketch; deposits + loans)."""

    enabled: bool = False
    bank_id: str = "bank"
    deposits: dict[str, float] = field(default_factory=dict)
    loans_payable: dict[str, float] = field(default_factory=dict)

    def grant_loan_creates_deposit(self, borrower: str, amount: float) -> None:
        """Textbook loans-create-deposits: borrower deposit ↑ and loan ↑ (bank books off-ledger)."""
        if not self.enabled or amount <= 0:
            return
        self.deposits[borrower] = self.deposits.get(borrower, 0.0) + amount
        self.loans_payable[borrower] = self.loans_payable.get(borrower, 0.0) + amount

    def deposit_money_supply(self) -> float:
        return sum(self.deposits.values())
