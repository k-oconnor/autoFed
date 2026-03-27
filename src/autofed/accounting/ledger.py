from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from autofed.accounting.journal import JournalEntry, JournalLine
from autofed.accounting.transaction import Transaction, TransactionType

if TYPE_CHECKING:
    from autofed.accounting.sqlite_log import SqliteTransactionLog


class Ledger:
    """Append-only journal with running cash balances per entity."""

    __slots__ = ("_cash", "_entries", "_transactions", "_sqlite")

    def __init__(
        self,
        initial_cash: Mapping[str, float] | None = None,
        *,
        sqlite_log: SqliteTransactionLog | None = None,
    ) -> None:
        self._cash: dict[str, float] = dict(initial_cash or {})
        self._entries: list[JournalEntry] = []
        self._transactions: list[Transaction] = []
        self._sqlite: SqliteTransactionLog | None = sqlite_log

    @property
    def cash(self) -> Mapping[str, float]:
        return self._cash

    @property
    def entries(self) -> tuple[JournalEntry, ...]:
        return tuple(self._entries)

    @property
    def transactions(self) -> tuple[Transaction, ...]:
        """Spec-style logical transactions (one row per payment leg narrative)."""
        return tuple(self._transactions)

    def post(self, entry: JournalEntry) -> None:
        """Apply a balanced entry; raises if any balance goes negative."""
        for line in entry.lines:
            prev = self._cash.get(line.entity_id, 0.0)
            new = prev + line.delta_cash
            if new < -1e-9:
                raise ValueError(
                    f"insufficient cash for {line.entity_id!r}: {prev} + {line.delta_cash} = {new} "
                    f"({entry.memo!r})"
                )
            self._cash[line.entity_id] = new
        self._entries.append(entry)

    def post_transfer(
        self,
        tick: int,
        payer: str,
        payee: str,
        amount: float,
        memo: str = "",
        *,
        tx_type: TransactionType = TransactionType.TRANSFER,
        good_id: str | None = None,
        currency: str = "USD",
    ) -> None:
        if amount <= 0:
            raise ValueError("transfer amount must be positive")
        self.post(
            JournalEntry(
                tick,
                (
                    JournalLine(payer, -amount),
                    JournalLine(payee, amount),
                ),
                memo=memo,
            )
        )
        tx = Transaction(
            tick=tick,
            from_entity=payer,
            to_entity=payee,
            amount=amount,
            currency=currency,
            type=tx_type,
            good_id=good_id,
            memo=memo,
        )
        self._transactions.append(tx)
        if self._sqlite is not None:
            self._sqlite.append(tx)

    def validate_closed_economy(self) -> None:
        """Central bank + private sector: total cash should stay at zero."""
        total = sum(self._cash.values())
        if abs(total) > 1e-6:
            raise ValueError(f"money not conserved: sum(cash)={total}")
