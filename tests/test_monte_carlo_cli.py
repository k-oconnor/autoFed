from pathlib import Path

from autofed.agents.backend import ManualAgentBackend
from autofed.config.loader import load_economy_yaml
from autofed.engine.tick import TickEngine
from autofed.monte_carlo import monte_carlo_run

ROOT = Path(__file__).resolve().parents[1]


def test_monte_carlo_variants() -> None:
    path = ROOT / "config" / "economy.yaml"

    def build(seed: int):
        w = load_economy_yaml(path)
        if seed % 2 == 0:
            w.expectations["hh_0"].inflation_expected += 0.001
        return w

    def run_engine(world, ticks: int) -> None:
        TickEngine(ManualAgentBackend()).run(world, ticks)

    out = monte_carlo_run(build, run_engine, n_runs=3, ticks=2, base_seed=10)
    assert len(out) == 3
    assert {s.seed for s in out} == {10, 11, 12}
