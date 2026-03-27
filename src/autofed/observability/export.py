from __future__ import annotations

import csv
from pathlib import Path

from autofed.accounting.transaction import Transaction


def export_transactions_csv(transactions: list[Transaction], path: str | Path) -> None:
    """Write spec-style transaction rows for dashboards / Streamlit."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "tick",
                "from_entity",
                "to_entity",
                "amount",
                "currency",
                "type",
                "good_id",
                "memo",
            ]
        )
        for tx in transactions:
            w.writerow(
                [
                    tx.tick,
                    tx.from_entity,
                    tx.to_entity,
                    tx.amount,
                    tx.currency,
                    tx.type.value,
                    tx.good_id or "",
                    tx.memo,
                ]
            )
