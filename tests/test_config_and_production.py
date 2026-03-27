from pathlib import Path

import pytest

from autofed.agents.backend import ManualAgentBackend
from autofed.config.loader import load_economy_yaml
from autofed.engine.tick import TickEngine

ROOT = Path(__file__).resolve().parents[1]


def test_load_yaml_economy_balanced() -> None:
    path = ROOT / "config" / "economy.yaml"
    w = load_economy_yaml(path)
    w.ledger.validate_closed_economy()
    assert "mill" in w.firm_recipes
    assert "bakery" in w.firm_recipes


def test_supply_chain_produces_goods() -> None:
    path = ROOT / "config" / "economy.yaml"
    w = load_economy_yaml(path)
    flour_0 = w.firm_inventory("mill", "flour")
    bread_0 = w.firm_inventory("bakery", "bread")
    TickEngine(ManualAgentBackend()).step(w, 0)
    assert w.firm_inventory("mill", "flour") > flour_0
    assert w.firm_inventory("bakery", "bread") > bread_0


@pytest.mark.parametrize("ticks", [1, 3])
def test_yaml_runs_multiple_ticks(ticks: int) -> None:
    w = load_economy_yaml(ROOT / "config" / "economy.yaml")
    TickEngine(ManualAgentBackend()).run(w, ticks)
    w.ledger.validate_closed_economy()
