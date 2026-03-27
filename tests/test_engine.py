from autofed.agents.backend import ManualAgentBackend
from autofed.engine.tick import TickEngine
from autofed.world.state import demo_world


def test_demo_world_starts_balanced() -> None:
    w = demo_world()
    w.ledger.validate_closed_economy()


def test_one_tick_money_and_inventory() -> None:
    w = demo_world()
    TickEngine(ManualAgentBackend()).step(w, 0)
    w.ledger.validate_closed_economy()
    # hh_0 (stability) buys 1 unit; hh_1 (growth) buys 2 when cash allows.
    assert w.firm_inventory("firm", "food") == 97
    assert abs(w.ledger.cash["firm"] - 930.0) < 0.02
    assert abs(w.ledger.cash["hh_0"] - 138.2) < 0.02
    assert abs(w.ledger.cash["hh_1"] - 131.8) < 0.02


def test_multi_tick() -> None:
    w = demo_world()
    TickEngine(ManualAgentBackend()).run(w, 5, start_tick=0)
    w.ledger.validate_closed_economy()
    assert w.firm_inventory("firm", "food") == 100 - 3 * 5
