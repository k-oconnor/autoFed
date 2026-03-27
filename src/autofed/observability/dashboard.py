"""Streamlit dashboard: macro series, balances, inventories, prices, transactions."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import pandas as pd
import streamlit as st

from autofed.observability.snapshots import flatten_snapshot_row, read_snapshots_jsonl


def main() -> None:
    st.set_page_config(page_title="AutoFed economy", layout="wide")
    st.title("AutoFed economy dashboard")
    st.caption("Point at a run folder produced by `autofed run ... --export-dir <dir>`.")

    default = Path("out/run")
    run_dir_s = st.sidebar.text_input("Run directory", value=str(default))
    run_dir = Path(run_dir_s)
    snap_path = run_dir / "snapshots.jsonl"
    tx_path = run_dir / "transactions.csv"

    st.sidebar.markdown("**Files**")
    st.sidebar.write(f"snapshots: `{snap_path.name}` — {'ok' if snap_path.exists() else 'missing'}")
    st.sidebar.write(f"transactions: `{tx_path.name}` — {'ok' if tx_path.exists() else 'missing'}")

    snaps = read_snapshots_jsonl(snap_path)
    flat = [flatten_snapshot_row(s) for s in snaps]
    df = pd.DataFrame(flat) if flat else pd.DataFrame()

    tab_macro, tab_cash, tab_inv, tab_tx = st.tabs(
        ["Macro & expectations", "Cash balances", "Inventories & prices", "Transactions"]
    )

    with tab_macro:
        if df.empty:
            st.info(
                "No snapshots found. Generate with:\n\n"
                "`python -m autofed run --config config/economy.yaml --ticks 30 "
                f"--export-dir {default}`"
            )
        else:
            idx = df.set_index("tick")
            macro_cols = [
                c
                for c in (
                    "policy_rate",
                    "cpi_level",
                    "last_inflation",
                    "output_gap",
                    "mean_inflation_expectation",
                    "expectation_dispersion",
                )
                if c in df.columns
            ]
            st.subheader("Macro & beliefs")
            st.line_chart(idx[macro_cols])
            if snaps:
                st.subheader("Forward guidance (latest)")
                st.text(snaps[-1].get("forward_guidance", ""))
                tail = snaps[-1].get("governance_log_tail") or []
                if tail:
                    st.subheader("Governance (recent)")
                    for line in tail:
                        st.text(line)

    with tab_cash:
        if df.empty:
            st.info("Need snapshots.jsonl for balance time series.")
        else:
            idx = df.set_index("tick")
            cash_cols = sorted(c for c in df.columns if c.startswith("cash__"))
            if cash_cols:
                st.subheader("Cash by entity")
                st.line_chart(idx[cash_cols])
            if "private_sector_cash" in df.columns:
                st.subheader("Private sector cash (excl. cb)")
                st.line_chart(idx[["private_sector_cash"]])

    with tab_inv:
        if df.empty:
            st.info("Need snapshots.jsonl.")
        else:
            idx = df.set_index("tick")
            inv_cols = sorted(c for c in df.columns if c.startswith("inv__"))
            price_cols = sorted(c for c in df.columns if c.startswith("price__"))
            epi_cols = sorted(c for c in df.columns if c.startswith("E_pi__"))
            if inv_cols:
                st.subheader("Firm inventories")
                st.line_chart(idx[inv_cols])
            if price_cols:
                st.subheader("Posted prices")
                st.line_chart(idx[price_cols])
            if epi_cols:
                st.subheader("Household inflation expectations")
                st.line_chart(idx[epi_cols])

    with tab_tx:
        if not tx_path.exists():
            st.warning(f"No `{tx_path.name}` in run directory (optional for raw flow explorer).")
        else:
            with tx_path.open(encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            st.subheader("Recent transactions")
            st.dataframe(rows[-200:], use_container_width=True, hide_index=True)
            by_type: dict[str, float] = defaultdict(float)
            for r in rows:
                try:
                    by_type[r.get("type", "")] += float(r.get("amount", 0))
                except ValueError:
                    continue
            if by_type:
                st.subheader("Cumulative flow volume by type")
                st.bar_chart(dict(sorted(by_type.items())))


if __name__ == "__main__":
    main()
