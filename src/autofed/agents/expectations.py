from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExpectationState:
    """Cached beliefs (spec §3.1 expectations)."""

    inflation_expected: float = 0.02
