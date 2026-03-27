from __future__ import annotations

import argparse

from autofed.agents.backend import ManualAgentBackend
from autofed.engine.tick import TickEngine
from autofed.world.state import demo_world


def main() -> None:
    parser = argparse.ArgumentParser(prog="autofed")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="Run demo simulation for N ticks")
    run_p.add_argument("--ticks", type=int, default=1, help="Number of ticks to simulate")

    args = parser.parse_args()
    if args.cmd == "run":
        world = demo_world()
        engine = TickEngine(ManualAgentBackend())
        engine.run(world, args.ticks)
        print("Final cash:", dict(world.ledger.cash))
        print("Firm food inventory:", world.firm_inventory("firm", "food"))


if __name__ == "__main__":
    main()
