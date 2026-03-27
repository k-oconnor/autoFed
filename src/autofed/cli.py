from __future__ import annotations

import argparse
import random
from pathlib import Path
from typing import Any

from autofed.agents.backend import ManualAgentBackend
from autofed.agents.llm_stub import StubLLMAgentBackend
from autofed.config.loader import load_economy_yaml
from autofed.engine.tick import TickEngine
from autofed.monte_carlo import monte_carlo_run
from autofed.observability.export import export_transactions_csv
from autofed.observability.snapshots import build_snapshot, write_snapshots_jsonl
from autofed.world.state import WorldState, demo_world


def main() -> None:
    parser = argparse.ArgumentParser(prog="autofed")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="Run simulation for N ticks")
    run_p.add_argument("--ticks", type=int, default=1, help="Number of ticks to simulate")
    run_p.add_argument(
        "--config",
        type=Path,
        default=None,
        help="YAML economy config (multi-good / supply chain)",
    )
    run_p.add_argument(
        "--export",
        type=Path,
        default=None,
        help="Write transactions CSV for dashboards",
    )
    run_p.add_argument(
        "--export-dir",
        type=Path,
        default=None,
        help="Write transactions.csv + snapshots.jsonl for the Streamlit dashboard",
    )
    run_p.add_argument(
        "--llm-stub",
        action="store_true",
        help="Use stub LLM backend (consumes llm_budget from config)",
    )

    mc = sub.add_parser("monte-carlo", help="Run repeated simulations with different seeds")
    mc.add_argument("--config", type=Path, required=True)
    mc.add_argument("--runs", type=int, default=5)
    mc.add_argument("--ticks", type=int, default=5)
    mc.add_argument("--base-seed", type=int, default=0)

    args = parser.parse_args()
    if args.cmd == "run":
        if args.config:
            world = load_economy_yaml(args.config)
        else:
            world = demo_world()
        if args.llm_stub:
            engine = TickEngine(StubLLMAgentBackend(ManualAgentBackend()))
        else:
            engine = TickEngine(ManualAgentBackend())

        if args.export_dir is not None:
            args.export_dir.mkdir(parents=True, exist_ok=True)
            snapshots: list[dict[str, Any]] = []
            for t in range(args.ticks):
                engine.step(world, t)
                snapshots.append(build_snapshot(world, t))
            tx_path = args.export_dir / "transactions.csv"
            snap_path = args.export_dir / "snapshots.jsonl"
            export_transactions_csv(list(world.ledger.transactions), tx_path)
            write_snapshots_jsonl(snapshots, snap_path)
            print("Wrote", tx_path, "and", snap_path)
        else:
            engine.run(world, args.ticks)
            if args.export:
                export_transactions_csv(list(world.ledger.transactions), args.export)
                print("Wrote", args.export)

        print("Final cash:", dict(world.ledger.cash))
        print("Policy rate:", world.policy_rate)
        print("CPI level:", world.cpi_level)
        if world.expectations:
            print(
                "Mean inflation expectation:",
                sum(e.inflation_expected for e in world.expectations.values())
                / len(world.expectations),
            )

    elif args.cmd == "monte-carlo":

        def build(seed: int) -> WorldState:
            random.seed(seed)
            w = load_economy_yaml(args.config)
            for ex in w.expectations.values():
                ex.inflation_expected += random.uniform(-0.002, 0.002)
            return w

        def run_engine(world: WorldState, ticks: int) -> None:
            TickEngine(ManualAgentBackend()).run(world, ticks)

        summaries = monte_carlo_run(
            build,
            run_engine,
            n_runs=args.runs,
            ticks=args.ticks,
            base_seed=args.base_seed,
        )
        for s in summaries:
            print(
                s.seed,
                f"private_cash={s.final_cash_sum_private:.2f}",
                f"r={s.policy_rate:.4f}",
                f"cpi={s.cpi_level:.4f}",
                f"E_pi={s.inflation_expected_mean}",
            )


if __name__ == "__main__":
    main()
