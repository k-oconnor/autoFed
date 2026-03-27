"""Goods market: category priority (spec §5.1) and rationing when cash or stock binds."""

from __future__ import annotations

from autofed.accounting.transaction import TransactionType
from autofed.agents.plan import GoodsSale

# Lower clears first: necessities before luxuries.
_CATEGORY_RANK: dict[str, int] = {
    "necessity": 0,
    "normal": 1,
    "luxury": 2,
    "veblen": 3,
    "production_input": 10,
    "capital_good": 11,
    "labor": 12,
}


def category_priority_rank(good_categories: dict[str, str], good_id: str) -> int:
    cat = good_categories.get(good_id, "normal")
    return _CATEGORY_RANK.get(cat, 5)


def sort_sales_by_market_priority(
    sales: tuple[GoodsSale, ...],
    good_categories: dict[str, str],
) -> list[GoodsSale]:
    """Stable sort: category priority, then buyer id (deterministic rationing tie-break)."""
    return sorted(
        sales,
        key=lambda s: (category_priority_rank(good_categories, s.good_id), s.buyer_id),
    )


def try_execute_sale(world: object, tick: int, sale: GoodsSale) -> bool:
    """Execute one sale if buyer has cash and seller has stock; otherwise no-op (rationing)."""
    from autofed.world.state import WorldState

    w: WorldState = world  # type: ignore[assignment]
    total = sale.quantity * sale.unit_price
    buyer_cash = w.ledger.cash.get(sale.buyer_id, 0.0)
    if buyer_cash + 1e-9 < total:
        return False
    if w.firm_inventory(sale.seller_id, sale.good_id) < sale.quantity:
        return False
    w.ledger.post_transfer(
        tick,
        sale.buyer_id,
        sale.seller_id,
        total,
        memo=f"purchase {sale.good_id} x{sale.quantity}",
        tx_type=TransactionType.PURCHASE,
        good_id=sale.good_id,
    )
    w.add_inventory(sale.seller_id, sale.good_id, -sale.quantity)
    return True
