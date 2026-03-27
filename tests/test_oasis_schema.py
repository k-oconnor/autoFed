import json

from autofed.agents.oasis.schemas import (
    build_tick_plan_from_parsed,
    merge_tick_plans,
    parse_oasis_json,
    tick_plan_has_economic_content,
)
from autofed.agents.plan import GoodsSale, TickPlan, WagePayment
from autofed.world.state import demo_world


def test_parse_oasis_json_roundtrip() -> None:
    raw = {
        "tick_plan": {"wages": []},
        "feed_posts": [],
        "new_goods": [{"good_id": "x", "initial_price": 1.0, "category": "normal"}],
    }
    p = parse_oasis_json(json.dumps(raw))
    assert p.new_goods[0]["good_id"] == "x"


def test_tick_plan_has_economic_content() -> None:
    assert not tick_plan_has_economic_content({})
    assert not tick_plan_has_economic_content({"wages": []})
    assert tick_plan_has_economic_content({"wages": [{"firm_id": "f", "household_id": "h", "amount": 1.0}]})


def test_merge_prefers_llm_when_non_empty() -> None:
    w = demo_world()
    manual = TickPlan(
        wages=(WagePayment("firm", "hh_0", 10.0),),
        sales=(),
    )
    llm = TickPlan(
        wages=(WagePayment("firm", "hh_0", 99.0),),
        sales=(),
    )
    m = merge_tick_plans(llm, manual)
    assert m.wages[0].amount == 99.0
    llm_empty = TickPlan(wages=(), sales=(GoodsSale("hh_0", "firm", "food", 1, 10.0),))
    manual2 = TickPlan(wages=manual.wages, sales=())
    m2 = merge_tick_plans(llm_empty, manual2)
    assert m2.wages == manual.wages
    assert len(m2.sales) == 1


def test_build_tick_plan_filters_bad_good() -> None:
    w = demo_world()
    tp = {
        "sales": [
            {
                "buyer_id": "hh_0",
                "seller_id": "firm",
                "good_id": "nonexistent",
                "quantity": 1,
                "unit_price": 1.0,
            }
        ]
    }
    plan = build_tick_plan_from_parsed(tp, w)
    assert plan.sales == ()
