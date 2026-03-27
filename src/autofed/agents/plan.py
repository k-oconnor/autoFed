from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WagePayment:
    firm_id: str
    household_id: str
    amount: float


@dataclass(frozen=True)
class GoodsSale:
    buyer_id: str
    seller_id: str
    good_id: str
    quantity: int
    unit_price: float


@dataclass(frozen=True)
class TickPlan:
    wages: tuple[WagePayment, ...]
    sales: tuple[GoodsSale, ...]
