import tempfile
from pathlib import Path

from autofed.accounting.ledger import Ledger
from autofed.accounting.sqlite_log import SqliteTransactionLog
from autofed.accounting.transaction import TransactionType


def test_sqlite_log_persists_transfers() -> None:
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "t.db"
        log = SqliteTransactionLog(db)
        ledger = Ledger({"a": 10.0, "b": 0.0}, sqlite_log=log)
        ledger.post_transfer(0, "a", "b", 3.0, memo="t", tx_type=TransactionType.TRANSFER)
        assert log.count() == 1
        rows = log.fetch_tick(0)
        assert rows[0].amount == 3.0
        assert rows[0].type == TransactionType.TRANSFER
        log.close()
