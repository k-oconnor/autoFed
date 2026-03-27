from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable


class SocialGraph:
    """Undirected acquaintance edges between agent ids (information layer; read-only for money)."""

    __slots__ = ("_adj",)

    def __init__(self, edges: Iterable[tuple[str, str]] | None = None) -> None:
        self._adj: dict[str, set[str]] = defaultdict(set)
        if edges:
            for a, b in edges:
                self.add_edge(a, b)

    def add_edge(self, a: str, b: str) -> None:
        self._adj[a].add(b)
        self._adj[b].add(a)

    def neighbors(self, agent_id: str) -> frozenset[str]:
        return frozenset(self._adj.get(agent_id, ()))

    def mean_neighbor_value(self, agent_id: str, values: dict[str, float]) -> float | None:
        """Average of ``values[nb]`` over neighbors with defined values."""
        nbs = [values[nb] for nb in self.neighbors(agent_id) if nb in values]
        if not nbs:
            return None
        return sum(nbs) / len(nbs)
