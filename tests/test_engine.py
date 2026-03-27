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
    assert w.firm_inventory("firm", "food") == 98
    assert w.ledger.cash["firm"] == 1000.0 - 100.0 + 20.0
    assert w.ledger.cash["hh_0"] == 100.0 - 10.0 + 50.0


def test_multi_tick() -> None:
    w = demo_world()
    TickEngine(ManualAgentBackend()).run(w, 5, start_tick=0)
    w.ledger.validate_closed_economy()
    assert w.firm_inventory("firm", "food") == 100 - 2 * 5
