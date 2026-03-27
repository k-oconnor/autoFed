from autofed.accounting.ledger import Ledger
from autofed.world.firm import FirmRecipe
from autofed.world.oasis_config import OasisConfig
from autofed.world.patches import apply_new_goods, apply_recipe_adoptions
from autofed.world.state import WorldState


def test_apply_new_goods_registers_price() -> None:
    w = WorldState(
        ledger=Ledger({"cb": 0.0}),
        posted_unit_prices={"food": 1.0},
        good_categories={"food": "necessity"},
    )
    cfg = OasisConfig(max_new_goods_per_tick=5)
    n = apply_new_goods(
        w,
        [{"good_id": "kombucha", "initial_price": 4.5, "category": "normal"}],
        cfg,
    )
    assert n == 1
    assert w.posted_unit_prices["kombucha"] == 4.5
    assert w.good_categories["kombucha"] == "normal"


def test_apply_new_goods_rejects_bad_slug() -> None:
    w = WorldState(ledger=Ledger({"cb": 0.0}), posted_unit_prices={})
    cfg = OasisConfig()
    n = apply_new_goods(
        w,
        [{"good_id": "BadCase", "initial_price": 1.0, "category": "normal"}],
        cfg,
    )
    assert n == 0


def test_apply_new_goods_respects_cap() -> None:
    w = WorldState(ledger=Ledger({"cb": 0.0}), posted_unit_prices={})
    cfg = OasisConfig(max_new_goods_per_tick=1)
    items = [
        {"good_id": "a", "initial_price": 1.0, "category": "normal"},
        {"good_id": "b", "initial_price": 1.0, "category": "normal"},
    ]
    n = apply_new_goods(w, items, cfg)
    assert n == 1
    assert "a" in w.posted_unit_prices
    assert "b" not in w.posted_unit_prices


def test_apply_recipe_adoption() -> None:
    w = WorldState(
        ledger=Ledger({"cb": 0.0}),
        posted_unit_prices={"in": 1.0, "out": 2.0},
        firm_recipes={"firm": FirmRecipe("out", 1, {"in": 1})},
    )
    n = apply_recipe_adoptions(
        w,
        [{"firm_id": "firm", "recipe": {"output_good": "out", "output_qty": 2, "inputs": {"in": 2}}}],
    )
    assert n == 1
    assert w.firm_recipes["firm"].output_qty == 2
