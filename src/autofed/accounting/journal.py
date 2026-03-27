from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JournalLine:
    """One leg of a journal entry: change in cash for ``entity_id``."""

    entity_id: str
    delta_cash: float


@dataclass(frozen=True)
class JournalEntry:
    """Balanced multi-leg posting. Sum of ``delta_cash`` must be ~0."""

    tick: int
    lines: tuple[JournalLine, ...]
    memo: str = ""

    def __post_init__(self) -> None:
        if not self.balanced():
            total = sum(line.delta_cash for line in self.lines)
            raise ValueError(f"unbalanced journal entry (sum={total!r}): {self.memo!r}")

    def balanced(self) -> bool:
        return abs(sum(line.delta_cash for line in self.lines)) < 1e-9
