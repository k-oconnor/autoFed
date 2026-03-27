from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FirmRecipe:
    """One-step production: consume ``inputs`` batch, add ``output_qty`` of ``output_good``."""

    output_good: str
    output_qty: int
    inputs: dict[str, int] = field(default_factory=dict)


@dataclass
class FirmGovernance:
    """Board / CEO cadence (spec §4.4 subset)."""

    firm_id: str
    ceo_agent_id: str
    board_agent_ids: tuple[str, ...] = ()
    evaluate_every_n_ticks: int = 20
    last_ceo_retained: bool = True
