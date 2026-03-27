"""Agent personas: YAML load, seed-stable stochastic draws, backend scaling."""

import textwrap
from pathlib import Path

import pytest

from autofed.agents.backend import ManualAgentBackend
from autofed.agents.persona import (
    AgentPersona,
    draw_persona_traits,
    merge_yaml_persona,
    persona_to_snapshot_dict,
)
from autofed.config.loader import load_economy_yaml
from autofed.engine.tick import TickEngine
from autofed.accounting.ledger import Ledger
from autofed.world.state import WorldState, demo_world

ROOT = Path(__file__).resolve().parents[1]


def test_draw_persona_traits_deterministic_per_rng() -> None:
    import random

    rng = random.Random(12345)
    a = draw_persona_traits("entrepreneur", rng)
    rng2 = random.Random(12345)
    b = draw_persona_traits("entrepreneur", rng2)
    assert a == b


def test_merge_yaml_persona_stochastic_stable_by_agent_id() -> None:
    p1 = merge_yaml_persona(
        "hh_0",
        {"role": "worker"},
        stochastic=True,
        base_seed=99,
        default_role="worker",
    )
    p2 = merge_yaml_persona(
        "hh_0",
        {"role": "worker"},
        stochastic=True,
        base_seed=99,
        default_role="worker",
    )
    assert p1.risk_aversion == p2.risk_aversion
    assert p1.agency == p2.agency
    assert p1.goals.primary == p2.goals.primary


def test_merge_stochastic_entrepreneur_vs_rentier_risk_ordering() -> None:
    a = merge_yaml_persona(
        "hh_0",
        {"role": "entrepreneur"},
        stochastic=True,
        base_seed=42,
        default_role="worker",
    )
    b = merge_yaml_persona(
        "hh_1",
        {"role": "rentier"},
        stochastic=True,
        base_seed=42,
        default_role="worker",
    )
    assert a.risk_aversion < b.risk_aversion


def test_load_yaml_personas_include_governance_ids() -> None:
    w = load_economy_yaml(ROOT / "config" / "economy.yaml")
    assert "hh_0" in w.agent_personas
    assert "ceo_mill" in w.agent_personas
    assert "b1" in w.agent_personas


def test_demo_world_personas_change_plans() -> None:
    w = demo_world()
    plan = ManualAgentBackend(wage=50.0, purchase_units=1).plan_tick(w, 0)
    wages = {wp.household_id: wp.amount for wp in plan.wages}
    assert wages["hh_0"] != wages["hh_1"]


def test_persona_to_snapshot_dict_json_safe() -> None:
    p = AgentPersona(role="manager", risk_aversion=0.4, agency=0.5)
    d = persona_to_snapshot_dict(p)
    assert d["role"] == "manager"
    assert d["goals"]["primary"] == "stability"


def test_stochastic_yaml_tmp_config(tmp_path: Path) -> None:
    cfg = tmp_path / "e.yaml"
    cfg.write_text(
        textwrap.dedent(
            """
            seed: 7
            agent_generation:
              stochastic: true
            entities:
              cb: { cash: -100 }
              hh_0: { cash: 50 }
              hh_1: { cash: 50 }
            employment: {}
            goods:
              g: { price: 1.0, category: normal }
            agents:
              hh_0: { role: entrepreneur }
              hh_1: { role: rentier }
            """
        ),
        encoding="utf-8",
    )
    w1 = load_economy_yaml(cfg)
    assert w1.agent_personas["hh_0"].role == "entrepreneur"
    # Same file + seed => identical draws
    w2 = load_economy_yaml(cfg)
    assert w1.agent_personas["hh_0"].risk_aversion == w2.agent_personas["hh_0"].risk_aversion


@pytest.mark.parametrize("ticks", [1, 2])
def test_yaml_ticks_with_personas(ticks: int) -> None:
    w = load_economy_yaml(ROOT / "config" / "economy.yaml")
    TickEngine(ManualAgentBackend()).run(w, ticks)
    w.ledger.validate_closed_economy()


def test_world_state_persona_default_for_unknown_id() -> None:
    w = WorldState(ledger=Ledger({"cb": 0.0}))
    assert w.persona("nope").role == "worker"
