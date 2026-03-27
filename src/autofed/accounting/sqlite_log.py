from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path

from autofed.accounting.transaction import Transaction, TransactionType


class SqliteTransactionLog:
    """Append-only SQLite mirror of ``Transaction`` rows (ACID persistence)."""

    _DDL = """
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tick INTEGER NOT NULL,
        from_entity TEXT NOT NULL,
        to_entity TEXT NOT NULL,
        amount REAL NOT NULL,
        currency TEXT NOT NULL,
        type TEXT NOT NULL,
        good_id TEXT,
        memo TEXT NOT NULL DEFAULT ''
    );
    CREATE INDEX IF NOT EXISTS idx_tx_tick ON transactions(tick);
    """

    __slots__ = ("_conn", "_path")

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._path = str(path)
        self._conn = sqlite3.connect(self._path)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(self._DDL)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def append(self, tx: Transaction) -> None:
        self._conn.execute(
            """
            INSERT INTO transactions
            (tick, from_entity, to_entity, amount, currency, type, good_id, memo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tx.tick,
                tx.from_entity,
                tx.to_entity,
                tx.amount,
                tx.currency,
                tx.type.value,
                tx.good_id,
                tx.memo,
            ),
        )
        self._conn.commit()

    def append_all(self, txs: Iterable[Transaction]) -> None:
        for tx in txs:
            self.append(tx)

    def count(self) -> int:
        cur = self._conn.execute("SELECT COUNT(*) FROM transactions")
        return int(cur.fetchone()[0])

    def fetch_tick(self, tick: int) -> list[Transaction]:
        cur = self._conn.execute(
            "SELECT tick, from_entity, to_entity, amount, currency, type, good_id, memo "
            "FROM transactions WHERE tick = ? ORDER BY id",
            (tick,),
        )
        out: list[Transaction] = []
        for row in cur.fetchall():
            t, fe, te, amt, curcy, typ, gid, memo = row
            out.append(
                Transaction(
                    tick=int(t),
                    from_entity=fe,
                    to_entity=te,
                    amount=float(amt),
                    currency=curcy,
                    type=TransactionType(typ),
                    good_id=gid,
                    memo=memo or "",
                )
            )
        return out
