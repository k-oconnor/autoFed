# AutoFed

Agent-based macro simulation with **stock-flow-consistent** double-entry money. See `autofed_spec.docx` for the full design.

## Layout

| Path | Role |
|------|------|
| `src/autofed/accounting/` | Journal, `Transaction` / `TransactionType`, `BalanceSheet`, `Ledger`, optional `SqliteTransactionLog` |
| `src/autofed/world/` | `WorldState`, production recipes, Taylor CB params |
| `src/autofed/engine/` | Phased tick runner (observe → expectations → production → markets → policy → accounting → governance) |
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

## Status

**v0.2** — Stock-flow-consistent cash, spec-style `Transaction` log, SQLite persistence hook, YAML economies with multi-firm production, Taylor rule policy rate, social graph + heterogeneous inflation expectations, Monte Carlo runner, banking/equity stubs, CSV export, **Streamlit dashboard** (macro, cash, inventories, prices, transactions) fed by `--export-dir` + `snapshots.jsonl`.

Public repo: [github.com/k-oconnor/autoFed](https://github.com/k-oconnor/autoFed).
