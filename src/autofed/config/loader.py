from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from autofed.accounting.ledger import Ledger
from autofed.agents.batching import LLMCallBudget
from autofed.agents.expectations import ExpectationState
from autofed.banking.layer import BankingLayer
from autofed.equity.cap_table import EquityCapTable
from autofed.social.graph import SocialGraph
from autofed.world.central_bank import TaylorParams
from autofed.world.firm import FirmGovernance, FirmRecipe
from autofed.world.state import WorldState


def load_economy_yaml(path: str | Path) -> WorldState:
    """Build ``WorldState`` from YAML (goods, firms, employment, CB)."""
    p = Path(path)
    raw: dict[str, Any] = yaml.safe_load(p.read_text(encoding="utf-8"))

    ent = raw.get("entities") or {}
    cash0 = {k: float(v["cash"]) for k, v in ent.items()}

    goods_cfg = raw.get("goods") or {}
    posted = {gid: float(v["price"]) for gid, v in goods_cfg.items()}
    good_categories = {
        gid: str(v.get("category", "normal")) for gid, v in goods_cfg.items()
    }

    inv: dict[str, dict[str, int]] = {}
    recipes: dict[str, FirmRecipe] = {}
    governance: dict[str, FirmGovernance] = {}
    firm_ids: list[str] = []

    for firm_id, block in (raw.get("firms") or {}).items():
        firm_ids.append(firm_id)
        inv[firm_id] = {g: int(q) for g, q in (block.get("inventory") or {}).items()}
        rc = block.get("recipe") or {}
        if rc:
            recipes[firm_id] = FirmRecipe(
                output_good=str(rc["output_good"]),
                output_qty=int(rc["output_qty"]),
                inputs={k: int(v) for k, v in (rc.get("inputs") or {}).items()},
            )
        gov = block.get("governance") or {}
        if gov:
            board = tuple(str(x) for x in gov.get("board") or ())
            governance[firm_id] = FirmGovernance(
                firm_id=firm_id,
                ceo_agent_id=str(gov.get("ceo", "ceo")),
                board_agent_ids=board,
                evaluate_every_n_ticks=int(gov.get("evaluate_every_n_ticks", 20)),
            )

    employment = {str(k): str(v) for k, v in (raw.get("employment") or {}).items()}
    hh_ids = tuple(sorted(k for k in ent if k.startswith("hh_")))

    cb = raw.get("central_bank") or {}
    taylor_raw = cb.get("taylor") or {}
    taylor = TaylorParams(
        r_star=float(taylor_raw.get("r_star", 0.02)),
        pi_star=float(taylor_raw.get("pi_star", 0.02)),
        phi_pi=float(taylor_raw.get("phi_pi", 0.5)),
        phi_y=float(taylor_raw.get("phi_y", 0.25)),
    )
    fg = str(cb.get("forward_guidance", ""))

    expectations = {hid: ExpectationState(0.02) for hid in hh_ids}

    llm_raw = raw.get("llm") or {}
    max_llm = llm_raw.get("max_calls_per_tick")
    llm_budget = LLMCallBudget(int(max_llm)) if max_llm is not None else None

    bank_raw = raw.get("banking") or {}
    banking = BankingLayer(enabled=bool(bank_raw.get("enabled", False)))

    eq_raw = raw.get("equity") or {}
    equity: EquityCapTable | None = None
    if bool(eq_raw.get("enabled", False)):
        equity = EquityCapTable()

    soc = raw.get("social") or {}
    edge_pairs = soc.get("edges") or []
    social_graph = SocialGraph(tuple(tuple(pair) for pair in edge_pairs)) if edge_pairs else None

    ledger = Ledger(cash0, sqlite_log=None)

    return WorldState(
        ledger=ledger,
        inventory=inv,
        employment=employment,
        posted_unit_prices=posted,
        good_categories=good_categories,
        firm_recipes=recipes,
        taylor=taylor,
        forward_guidance=fg,
        governance=governance,
        expectations=expectations,
        household_ids=hh_ids,
        firm_ids=tuple(firm_ids),
        llm_budget=llm_budget,
        banking=banking,
        equity=equity,
        social_graph=social_graph,
    )
