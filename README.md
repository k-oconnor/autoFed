# AutoFed

Agent-based macro simulation with **stock-flow-consistent** double-entry money. See `autofed_spec.docx` for the full design.

## Layout

| Path | Role |
|------|------|
| `src/autofed/accounting/` | Journal, `Transaction` / `TransactionType`, `BalanceSheet`, `Ledger`, optional `SqliteTransactionLog` |
| `src/autofed/world/` | `WorldState`, production recipes, Taylor CB params |
| `src/autofed/engine/` | Phased tick runner; **goods before wages**; partial wages if firm cash binds |
| `src/autofed/markets/` | Priority goods clearing (necessity → … → luxury) + rationing |
| `src/autofed/agents/` | `ManualAgentBackend`, `StubLLMAgentBackend`, `LLMCallBudget`, `ExpectationState` |
| `src/autofed/social/` | `SocialGraph` (neighbor signals for beliefs) |
| `src/autofed/config/` | YAML economy loader |
| `src/autofed/banking/` | Optional `BankingLayer` (loans → deposits) |
| `src/autofed/equity/` | `EquityCapTable` (cash-for-shares) |
| `src/autofed/observability/` | CSV export, per-tick `snapshots.jsonl`, Streamlit economy dashboard |
| `config/economy.yaml` | Multi-good supply-chain example |
| `tests/` | Pytest |

## Quick start

Python **3.11+** is recommended (per spec); **3.9+** is supported for the current codebase.

```bash
cd autoFed
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
python -m autofed run --ticks 3
python -m autofed run --config config/economy.yaml --ticks 5 --export out/transactions.csv
python -m autofed run --config config/economy.yaml --ticks 10 --export-dir out/run
python -m autofed monte-carlo --config config/economy.yaml --runs 3 --ticks 4
pip install -e ".[dashboard]"   # streamlit + pandas
autofed-dashboard               # open sidebar: run dir = out/run (snapshots + transactions)
```

**Dashboard `ModuleNotFoundError: autofed`:** Streamlit must use the same environment where the package is installed (`source .venv/bin/activate` then `autofed-dashboard`), *or* run from the repo: `streamlit run src/autofed/observability/dashboard.py` — the script adds `src/` to `sys.path` automatically when it finds your checkout layout.

## Status

**v0.2.2** — Adds **priority goods clearing** (YAML `goods.*.category`), **rationing** on stock/cash, **sales before wages**, and **partial wages** when firms are liquidity-constrained (longer runs without hard failures). Plus v0.2.1 dashboard, CI, and SQLite transaction log.

Public repo: [github.com/k-oconnor/autoFed](https://github.com/k-oconnor/autoFed).
