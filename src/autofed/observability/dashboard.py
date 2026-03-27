"""Streamlit dashboard (optional dependency: ``pip install streamlit``)."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import streamlit as st


def main() -> None:
    st.set_page_config(page_title="AutoFed", layout="wide")
    st.title("AutoFed observability")
    path = st.text_input("Transactions CSV", value="out/transactions.csv")
    p = Path(path)
    if not p.exists():
        st.warning(
            "File not found. Run: autofed run --config config/economy.yaml "
            "--export out/transactions.csv"
        )
        return
    with p.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    st.subheader("Recent flows")
    st.dataframe(rows[-50:], use_container_width=True)
    by_type: dict[str, float] = defaultdict(float)
    for r in rows:
        try:
            by_type[r.get("type", "")] += float(r.get("amount", 0))
        except ValueError:
            continue
    if by_type:
        st.subheader("Volume by type")
        st.bar_chart(dict(sorted(by_type.items())))


if __name__ == "__main__":
    main()
