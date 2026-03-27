from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TaylorParams:
    """Discrete-time Taylor rule (spec §6.4 rule-based mode)."""

    r_star: float = 0.02
    pi_star: float = 0.02
    phi_pi: float = 0.5
    phi_y: float = 0.25


def policy_rate(inflation: float, output_gap: float, params: TaylorParams) -> float:
    """Nominal policy rate from inflation gap and output gap."""
    return (
        params.r_star
        + params.phi_pi * (inflation - params.pi_star)
        + params.phi_y * output_gap
    )
