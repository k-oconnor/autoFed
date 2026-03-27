from autofed.accounting.balance_sheet import BalanceSheet


def test_balance_sheet_from_ledger_cash() -> None:
    bs = BalanceSheet.from_ledger_cash("hh_0", {"hh_0": 123.0})
    assert bs.cash == 123.0
    assert bs.net_worth == 123.0
