# AutoFed

Agent-based macro simulation with **stock-flow-consistent** double-entry money. See `autofed_spec.docx` for the full design.

## Layout

| Path | Role |
|------|------|
| `src/autofed/accounting/` | Journal entries, ledger, balance validation |
| `src/autofed/world/` | World state (entities, inventory) |
| `src/autofed/engine/` | Phased tick runner |
| `src/autofed/agents/` | Decision backends (`ManualAgentBackend`, future LLM) |
| `tests/` | Pytest |

## Quick start

Python **3.11+** is recommended (per spec); **3.9+** is supported for the current codebase.

```bash
cd autoFed
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
python -m autofed run --ticks 3
```

## Status

**v0.1** — Phase 0: one-tick (and multi-tick) loop with manual policies, ledger invariants, minimal labor + goods flow.
