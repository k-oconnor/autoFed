from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autofed.world.state import WorldState


@dataclass
class RunSummary:
    seed: int
    final_cash_sum_private: float
    policy_rate: float
    cpi_level: float
    inflation_expected_mean: float | None


def run_single_seed(
    build_world: Callable[[int], WorldState],
    run_engine: Callable[[WorldState, int], None],
    *,
    seed: int,
    ticks: int,
) -> RunSummary:
    """Monte Carlo single draw: ``build_world(seed)`` then simulate ``ticks`` steps."""
    random.seed(seed)
    world = build_world(seed)
    run_engine(world, ticks)
    priv = {k: v for k, v in world.ledger.cash.items() if k != "cb"}
    exp_vals = [ex.inflation_expected for ex in world.expectations.values()]
    mean_exp = sum(exp_vals) / len(exp_vals) if exp_vals else None
    return RunSummary(
        seed=seed,
        final_cash_sum_private=sum(priv.values()),
        policy_rate=world.policy_rate,
        cpi_level=world.cpi_level,
        inflation_expected_mean=mean_exp,
    )


def monte_carlo_run(
    build_world: Callable[[int], WorldState],
    run_engine: Callable[[WorldState, int], None],
    *,
    n_runs: int,
    ticks: int,
    base_seed: int = 0,
) -> list[RunSummary]:
    return [
        run_single_seed(build_world, run_engine, seed=base_seed + i, ticks=ticks)
        for i in range(n_runs)
    ]
