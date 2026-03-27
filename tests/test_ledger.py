import pytest

from autofed.accounting.ledger import Ledger


def test_transfer_conserves_total() -> None:
    ledger = Ledger({"cb": -100.0, "a": 60.0, "b": 40.0})
    ledger.post_transfer(0, "a", "b", 25.0, memo="pay")
    assert ledger.cash["a"] == 35.0
    assert ledger.cash["b"] == 65.0
    ledger.validate_closed_economy()


def test_transfer_rejects_overdraft() -> None:
    ledger = Ledger({"x": 10.0, "y": 0.0})
    with pytest.raises(ValueError, match="insufficient cash"):
        ledger.post_transfer(0, "x", "y", 20.0, memo="too much")
