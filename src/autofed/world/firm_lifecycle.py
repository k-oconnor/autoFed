"""Firm exit (distress streak) and entry (stochastic + template)."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from autofed.accounting.transaction import TransactionType
from autofed.world.firm import FirmGovernance, FirmRecipe

if TYPE_CHECKING:
    from autofed.world.state import WorldState


@dataclass
class FirmLifecycleParams:
    """Exit/entry rules (YAML `firm_lifecycle`)."""

    exit_negative_net_worth_ticks: int = 0
    """Consecutive ticks with negative net worth before exit; ``0`` disables."""

    entry_enabled: bool = False
    entry_probability_per_tick: float = 0.0
    entry_max_firms: int = 100


@dataclass
class FirmEntryTemplate:
    """Spawn state for a new firm (cash from CB, inventory, recipe, optional governance)."""

    initial_cash: float
    inventory: dict[str, int]
    recipe: FirmRecipe
    governance: FirmGovernance | None = None


def firm_net_worth(world: WorldState, firm_id: str) -> float:
    """Cash plus inventory valued at posted prices (no firm debt in MVP)."""
    cash = world.ledger.cash.get(firm_id, 0.0)
    inv = world.inventory.get(firm_id, {})
    mv = sum(
        qty * float(world.posted_unit_prices.get(good_id, 0.0)) for good_id, qty in inv.items()
    )
    return cash + mv


def _active_recipe_firms(world: WorldState) -> list[str]:
    return list(world.firm_recipes.keys())


def exit_firm(world: WorldState, firm_id: str, tick: int) -> None:
    """Severance split among employees; leftover cash to cb; scrap inventory off-model."""
    if firm_id not in world.firm_recipes:
        return

    employees = [h for h, f in world.employment.items() if f == firm_id]
    total = float(world.ledger.cash.get(firm_id, 0.0))
    remaining = total

    if total > 1e-9:
        if employees:
            n = len(employees)
            for i, h in enumerate(employees):
                if i == n - 1:
                    pay = remaining
                else:
                    pay = round(total / n, 6)
                    remaining -= pay
                if pay > 1e-9:
                    world.ledger.post_transfer(
                        tick,
                        firm_id,
                        h,
                        pay,
                        memo=f"severance {firm_id} -> {h}",
                        tx_type=TransactionType.TRANSFER,
                    )
        else:
            world.ledger.post_transfer(
                tick,
                firm_id,
                "cb",
                total,
                memo=f"dissolution {firm_id} -> cb",
                tx_type=TransactionType.TRANSFER,
            )

    for h in employees:
        del world.employment[h]

    world.inventory.pop(firm_id, None)
    world.firm_recipes.pop(firm_id, None)
    world.governance.pop(firm_id, None)
    world.exited_firm_ids.add(firm_id)
    world.firm_negative_streak.pop(firm_id, None)
    world.firm_exit_log.append(f"tick {tick}: exit {firm_id}")


def enter_firm_from_template(world: WorldState, tick: int, template: FirmEntryTemplate) -> str:
    """Create entrant, fund from CB, return new firm id."""
    world.entrant_seq += 1
    new_id = f"entrant_{world.entrant_seq}"
    if template.initial_cash > 1e-9:
        world.ledger.post_transfer(
            tick,
            "cb",
            new_id,
            template.initial_cash,
            memo=f"startup {new_id}",
            tx_type=TransactionType.TRANSFER,
        )
    world.inventory[new_id] = dict(template.inventory)
    world.firm_recipes[new_id] = template.recipe
    if template.governance is not None:
        gov = template.governance
        world.governance[new_id] = FirmGovernance(
            firm_id=new_id,
            ceo_agent_id=gov.ceo_agent_id,
            board_agent_ids=tuple(gov.board_agent_ids),
            evaluate_every_n_ticks=gov.evaluate_every_n_ticks,
        )
    world.firm_entry_log.append(f"tick {tick}: entry {new_id}")
    return new_id


def lifecycle_end_of_tick(world: WorldState, tick: int) -> None:
    """Update distress streaks, exit failing firms, maybe spawn entrants."""
    p = world.lifecycle_params
    active = _active_recipe_firms(world)

    if p.exit_negative_net_worth_ticks > 0:
        to_exit: list[str] = []
        for fid in active:
            nw = firm_net_worth(world, fid)
            if nw < 0:
                world.firm_negative_streak[fid] = world.firm_negative_streak.get(fid, 0) + 1
            else:
                world.firm_negative_streak[fid] = 0
            if world.firm_negative_streak.get(fid, 0) >= p.exit_negative_net_worth_ticks:
                to_exit.append(fid)
        for fid in to_exit:
            exit_firm(world, fid, tick)

    if (
        p.entry_enabled
        and world.entry_template is not None
        and p.entry_probability_per_tick > 0
        and random.random() < p.entry_probability_per_tick
    ):
        n_active = len(_active_recipe_firms(world))
        if n_active < p.entry_max_firms:
            enter_firm_from_template(world, tick, world.entry_template)
