"""Longer YAML runs stay solvent with sales-before-wages + clearing."""

from pathlib import Path

from autofed.agents.backend import ManualAgentBackend
from autofed.config.loader import load_economy_yaml
from autofed.engine.tick import TickEngine

ROOT = Path(__file__).resolve().parents[1]


def test_economy_yaml_runs_40_ticks_without_overdraft() -> None:
    w = load_economy_yaml(ROOT / "config" / "economy.yaml")
    TickEngine(ManualAgentBackend()).run(w, 40)
    w.ledger.validate_closed_economy()
