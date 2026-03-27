"""End-of-tick economy snapshots for visualization (JSON-serializable)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from autofed.agents.persona import persona_to_snapshot_dict
from autofed.social.feed import feed_post_to_dict

if TYPE_CHECKING:
    from autofed.world.state import WorldState


def build_snapshot(world: WorldState, tick: int) -> dict[str, Any]:
    """Capture macro, balances, inventories, prices, and beliefs after a tick completes."""
    cash = {k: float(v) for k, v in world.ledger.cash.items()}
    private_sum = sum(v for k, v in cash.items() if k != "cb")
    inv: dict[str, dict[str, int]] = {
        fid: {g: int(q) for g, q in goods.items()} for fid, goods in world.inventory.items()
    }
    prices = {g: float(p) for g, p in world.posted_unit_prices.items()}
    exp = {aid: float(ex.inflation_expected) for aid, ex in world.expectations.items()}
    mean_exp = sum(exp.values()) / len(exp) if exp else None
    disp = world.expectation_dispersion()
    active_firms = sorted(world.firm_recipes.keys())
    return {
        "tick": int(tick),
        "policy_rate": float(world.policy_rate),
        "cpi_level": float(world.cpi_level),
        "last_inflation": float(world.last_inflation),
        "output_gap": float(world.output_gap),
        "mean_inflation_expectation": mean_exp,
        "expectation_dispersion": float(disp) if disp is not None else None,
        "private_sector_cash": float(private_sum),
        "forward_guidance": world.forward_guidance[:200],
        "cash": cash,
        "inventory": inv,
        "prices": prices,
        "expectations": exp,
        "governance_log_tail": list(world.governance_log[-5:]),
        "good_categories": dict(world.good_categories),
        "active_firms": active_firms,
        "exited_firm_ids": sorted(world.exited_firm_ids),
        "firm_exit_log_tail": list(world.firm_exit_log[-5:]),
        "firm_entry_log_tail": list(world.firm_entry_log[-5:]),
        "agent_personas": {
            aid: persona_to_snapshot_dict(p) for aid, p in sorted(world.agent_personas.items())
        },
        "agent_declared_roles": dict(sorted(world.agent_declared_roles.items())),
        "social_feed_tail": [feed_post_to_dict(p) for p in world.social_feed[-20:]],
        "good_ids": sorted(world.posted_unit_prices.keys()),
    }


def write_snapshots_jsonl(snapshots: list[dict[str, Any]], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for row in snapshots:
            f.write(json.dumps(row, separators=(",", ":")) + "\n")


def read_snapshots_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def flatten_snapshot_row(snap: dict[str, Any]) -> dict[str, Any]:
    """One flat dict per tick for pandas / charts."""
    row: dict[str, Any] = {
        "tick": snap["tick"],
        "policy_rate": snap["policy_rate"],
        "cpi_level": snap["cpi_level"],
        "last_inflation": snap["last_inflation"],
        "output_gap": snap["output_gap"],
        "mean_inflation_expectation": snap.get("mean_inflation_expectation"),
        "expectation_dispersion": snap.get("expectation_dispersion"),
        "private_sector_cash": snap.get("private_sector_cash"),
    }
    for entity, bal in snap.get("cash", {}).items():
        row[f"cash__{entity}"] = bal
    for firm, goods in snap.get("inventory", {}).items():
        for good, qty in goods.items():
            row[f"inv__{firm}__{good}"] = qty
    for good, price in snap.get("prices", {}).items():
        row[f"price__{good}"] = price
    for aid, epi in snap.get("expectations", {}).items():
        row[f"E_pi__{aid}"] = epi
    return row
