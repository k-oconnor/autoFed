from autofed.agents.backend import ManualAgentBackend
from autofed.engine.tick import TickEngine
from autofed.world.state import demo_world


def test_expectation_dispersion_defined() -> None:
    w = demo_world()
    d0 = w.expectation_dispersion()
    assert d0 is not None
    TickEngine(ManualAgentBackend()).step(w, 0)
    d1 = w.expectation_dispersion()
    assert d1 is not None
