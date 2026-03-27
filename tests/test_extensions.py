from autofed.accounting.ledger import Ledger
from autofed.agents.backend import ManualAgentBackend
from autofed.agents.batching import LLMCallBudget
from autofed.agents.llm_stub import StubLLMAgentBackend
from autofed.banking.layer import BankingLayer
from autofed.engine.tick import TickEngine
from autofed.equity.cap_table import EquityCapTable
from autofed.world.state import demo_world


def test_banking_loan_creates_deposit() -> None:
    b = BankingLayer(enabled=True)
    b.grant_loan_creates_deposit("firm", 100.0)
    assert b.deposits["firm"] == 100.0
    assert b.loans_payable["firm"] == 100.0


def test_equity_transfer() -> None:
    ledger = Ledger({"cb": -100.0, "hh_0": 50.0, "hh_1": 50.0})
    cap = EquityCapTable(
        shares={"bakery": {"hh_0": 20, "hh_1": 0}},
        posted_share_prices={"bakery": 2.0},
    )
    cap.transfer_shares("bakery", "hh_0", "hh_1", 5, ledger, tick=0)
    assert cap.shares["bakery"]["hh_0"] == 15
    assert cap.shares["bakery"]["hh_1"] == 5
    assert ledger.cash["hh_0"] == 60.0
    assert ledger.cash["hh_1"] == 40.0
    ledger.validate_closed_economy()


def test_llm_stub_budget() -> None:
    w = demo_world()
    w.llm_budget = LLMCallBudget(max_per_tick=2)
    eng = TickEngine(StubLLMAgentBackend(ManualAgentBackend()))
    eng.step(w, 0)
    assert w.llm_budget.used_this_tick == 1


def test_llm_budget_exceeded() -> None:
    w = demo_world()
    w.llm_budget = LLMCallBudget(max_per_tick=0)
    eng = TickEngine(StubLLMAgentBackend(ManualAgentBackend()))
    try:
        eng.step(w, 0)
    except RuntimeError as e:
        assert "budget" in str(e).lower()
    else:
        raise AssertionError("expected RuntimeError")
