from autofed.accounting.ledger import Ledger
from autofed.agents.plan import GoodsSale, TickPlan, WagePayment
from autofed.engine.tick import TickEngine
from autofed.markets.clearing import sort_sales_by_market_priority, try_execute_sale


class _PlanBackend:
    def __init__(self, plan: TickPlan) -> None:
        self._plan = plan

    def plan_tick(self, world: object, tick: int) -> TickPlan:
        return self._plan


def test_priority_necessity_before_luxury_when_cash_constrained() -> None:
    """Luxury listed first in plan, but necessity clears first; buyer can only afford one unit."""
    ledger = Ledger({"cb": -15.0, "firm": 0.0, "hh_0": 15.0})
    from autofed.world.state import WorldState

    w = WorldState(
        ledger=ledger,
        inventory={"firm": {"bread": 1, "jam": 1}},
        posted_unit_prices={"bread": 10.0, "jam": 10.0},
        good_categories={"bread": "necessity", "jam": "luxury"},
        household_ids=("hh_0",),
    )
    plan = TickPlan(
        wages=(),
        sales=(
            GoodsSale("hh_0", "firm", "jam", 1, 10.0),
            GoodsSale("hh_0", "firm", "bread", 1, 10.0),
        ),
    )
    TickEngine(_PlanBackend(plan)).step(w, 0)
    assert w.firm_inventory("firm", "bread") == 0
    assert w.firm_inventory("firm", "jam") == 1
    assert w.ledger.cash["hh_0"] == 5.0


def test_sort_sales_order() -> None:
    sales = (
        GoodsSale("a", "f", "lux", 1, 1.0),
        GoodsSale("b", "f", "nec", 1, 1.0),
    )
    cats = {"lux": "luxury", "nec": "necessity"}
    out = sort_sales_by_market_priority(sales, cats)
    assert out[0].good_id == "nec"


def test_wage_skipped_when_firm_cash_zero() -> None:
    ledger = Ledger({"cb": -100.0, "firm": 0.0, "hh_0": 100.0})
    from autofed.world.state import WorldState

    w = WorldState(ledger=ledger, household_ids=("hh_0",))
    plan = TickPlan(wages=(WagePayment("firm", "hh_0", 50.0),), sales=())
    TickEngine(_PlanBackend(plan)).step(w, 0)
    assert w.ledger.cash["hh_0"] == 100.0
    assert w.ledger.cash["firm"] == 0.0


def test_rationing_insufficient_stock() -> None:
    ledger = Ledger({"cb": -50.0, "firm": 0.0, "hh_0": 100.0})
    from autofed.world.state import WorldState

    w = WorldState(
        ledger=ledger,
        inventory={"firm": {"bread": 0}},
        posted_unit_prices={"bread": 10.0},
        good_categories={"bread": "necessity"},
    )
    ok = try_execute_sale(w, 0, GoodsSale("hh_0", "firm", "bread", 1, 10.0))
    assert ok is False
    assert w.ledger.cash["hh_0"] == 100.0
