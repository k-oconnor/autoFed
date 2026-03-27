import json
import tempfile
from pathlib import Path

from autofed.agents.backend import ManualAgentBackend
from autofed.engine.tick import TickEngine
from autofed.observability.snapshots import (
    build_snapshot,
    flatten_snapshot_row,
    read_snapshots_jsonl,
    write_snapshots_jsonl,
)
from autofed.world.state import demo_world


def test_build_snapshot_after_tick() -> None:
    w = demo_world()
    TickEngine(ManualAgentBackend()).step(w, 0)
    s = build_snapshot(w, 0)
    assert s["tick"] == 0
    assert "cash" in s and "firm" in s["cash"]
    assert "inventory" in s
    assert "policy_rate" in s


def test_jsonl_roundtrip() -> None:
    w = demo_world()
    s0 = build_snapshot(w, -1)
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "s.jsonl"
        write_snapshots_jsonl([s0], p)
        back = read_snapshots_jsonl(p)
        assert len(back) == 1
        assert back[0]["tick"] == -1


def test_flatten_snapshot_row() -> None:
    w = demo_world()
    s = build_snapshot(w, 0)
    flat = flatten_snapshot_row(s)
    assert flat["tick"] == 0
    assert any(k.startswith("cash__") for k in flat)
    assert json.dumps(flat)  # JSON-serializable
