"""Firm exit (distress) and entry (CB-funded template)."""

from autofed.accounting.ledger import Ledger
from autofed.agents.backend import ManualAgentBackend
from autofed.agents.expectations import ExpectationState
from autofed.config.loader import load_economy_yaml
from autofed.engine.tick import TickEngine
from autofed.world.firm import FirmGovernance, FirmRecipe
from autofed.world.firm_lifecycle import (
    FirmEntryTemplate,
    FirmLifecycleParams,
    enter_firm_from_template,
    exit_firm,
    firm_net_worth,
    lifecycle_end_of_tick,
)
from autofed.world.state import WorldState

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _closed_world_for_exit() -> WorldState:
    ledger = Ledger({"cb": -100.0, "corp": 100.0, "hh_0": 0.0, "hh_1": 0.0})
    recipe = FirmRecipe(output_good="g", output_qty=0, inputs={})
    return WorldState(
        ledger=ledger,
        inventory={"corp": {}},
        employment={"hh_0": "corp", "hh_1": "corp"},
        posted_unit_prices={"g": 1.0},
        firm_recipes={"corp": recipe},
        governance={
            "corp": FirmGovernance(firm_id="corp", ceo_agent_id="c", evaluate_every_n_ticks=0)
        },
        household_ids=("hh_0", "hh_1"),
        firm_ids=("corp",),
        expectations={
            "hh_0": ExpectationState(0.02),
            "hh_1": ExpectationState(0.02),
        },
    )


def test_exit_firm_severance_and_employment_clear() -> None:
    w = _closed_world_for_exit()
    exit_firm(w, "corp", tick=7)
    assert "corp" not in w.firm_recipes
    assert w.employment.get("hh_0") is None
    assert w.ledger.cash["corp"] == 0.0
    assert abs(w.ledger.cash["hh_0"] - 50.0) < 1e-6
    assert abs(w.ledger.cash["hh_1"] - 50.0) < 1e-6
    w.ledger.validate_closed_economy()
    assert "corp" in w.exited_firm_ids


def test_lifecycle_exits_on_negative_net_worth_streak() -> None:
    ledger = Ledger({"cb": 200.0, "corp": -500.0, "hh_0": 150.0, "hh_1": 150.0})
    w = WorldState(
        ledger=ledger,
        inventory={"corp": {}},
        employment={"hh_0": "corp"},
        posted_unit_prices={},
        firm_recipes={"corp": FirmRecipe("x", 0, {})},
        household_ids=("hh_0", "hh_1"),
        firm_ids=("corp",),
        lifecycle_params=FirmLifecycleParams(exit_negative_net_worth_ticks=1),
    )
    assert firm_net_worth(w, "corp") < 0
    lifecycle_end_of_tick(w, tick=0)
    assert "corp" not in w.firm_recipes
    assert "hh_0" not in w.employment
    w.ledger.validate_closed_economy()


def test_enter_firm_from_template_funds_from_cb() -> None:
    ledger = Ledger({"cb": -500.0, "hh_0": 500.0})
    w = WorldState(
        ledger=ledger,
        posted_unit_prices={"bread": 10.0},
        household_ids=("hh_0",),
        firm_ids=(),
        firm_recipes={},
    )
    tpl = FirmEntryTemplate(
        initial_cash=200.0,
        inventory={"bread": 5},
        recipe=FirmRecipe("bread", 1, {"wheat": 1}),
    )
    fid = enter_firm_from_template(w, tick=1, template=tpl)
    assert fid == "entrant_1"
    assert w.firm_recipes[fid].output_good == "bread"
    assert w.firm_inventory(fid, "bread") == 5
    assert abs(w.ledger.cash["cb"] - (-700.0)) < 1e-6
    assert abs(w.ledger.cash[fid] - 200.0) < 1e-6
    w.ledger.validate_closed_economy()


def test_manual_backend_skips_inactive_employer() -> None:
    w = WorldState(
        ledger=Ledger({"cb": 0.0, "ghost": 0.0, "hh_0": 0.0}),
        posted_unit_prices={"food": 1.0},
        employment={"hh_0": "ghost"},
        household_ids=("hh_0",),
        firm_recipes={},
    )
    plan = ManualAgentBackend().plan_tick(w, 0)
    assert plan.wages == ()
    assert plan.sales == ()


def test_tick_engine_runs_lifecycle_and_validates() -> None:
    ledger = Ledger({"cb": 200.0, "corp": -500.0, "hh_0": 150.0, "hh_1": 150.0})
    w = WorldState(
        ledger=ledger,
        inventory={"corp": {}},
        employment={"hh_0": "corp"},
        posted_unit_prices={"food": 10.0},
        good_categories={"food": "necessity"},
        firm_recipes={"corp": FirmRecipe("food", 0, {})},
        household_ids=("hh_0", "hh_1"),
        firm_ids=("corp",),
        expectations={"hh_0": ExpectationState(0.02), "hh_1": ExpectationState(0.02)},
        lifecycle_params=FirmLifecycleParams(exit_negative_net_worth_ticks=1),
    )
    # No inventory for food: planned sales no-op; wage 0 avoids ledger noise before exit.
    TickEngine(ManualAgentBackend(wage=0.0)).step(w, 0)
    assert "corp" not in w.firm_recipes
    w.ledger.validate_closed_economy()


def test_load_yaml_without_firm_lifecycle_defaults() -> None:
    w = load_economy_yaml(ROOT / "config" / "economy.yaml")
    assert w.lifecycle_params.exit_negative_net_worth_ticks == 0
    assert w.entry_template is None
