from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TransactionType(str, Enum):
    """Spec-aligned transaction categories (append-only ledger schema)."""

    WAGE = "wage"
    PURCHASE = "purchase"
    DIVIDEND = "dividend"
    TAX = "tax"
    LOAN = "loan"
    REPAYMENT = "repayment"
    TRANSFER = "transfer"
    INTEREST = "interest"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"


@dataclass(frozen=True)
class Transaction:
    """Single logical transfer (from -> to), auditable row."""

    tick: int
    from_entity: str
    to_entity: str
    amount: float
    currency: str
    type: TransactionType
    good_id: str | None
    memo: str
