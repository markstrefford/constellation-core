"""Graph topology and pathfinding."""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Edge:
    """A connection between two nodes."""

    origin: str
    destination: str
    distance: float
    edge_type: str = "default"


@dataclass
class Graph:
    """
    Graph topology with pathfinding.

    Stores node IDs and edges, builds adjacency and distance lookups,
    and provides Dijkstra-based shortest path queries with optional
    edge type filtering.
    """

    node_ids: list[str]
    edges: list[Edge]

    # Derived: (origin, dest) -> distance for direct edges only
    distances: dict[tuple[str, str], float] = field(default_factory=dict, repr=False)

    # Derived: (origin, dest) -> edge_type for direct edges
    edge_types: dict[tuple[str, str], str] = field(default_factory=dict, repr=False)

    # Adjacency list: node_id -> [(neighbor_id, distance, edge_type), ...]
    _adjacency: dict[str, list[tuple[str, float, str]]] = field(
        default_factory=dict, repr=False
    )

    def __post_init__(self) -> None:
        self._build_graph()

    def _build_graph(self) -> None:
        self.distances = {}
        self.edge_types = {}
        self._adjacency = {nid: [] for nid in self.node_ids}

        for edge in self.edges:
            self.distances[(edge.origin, edge.destination)] = edge.distance
            self.edge_types[(edge.origin, edge.destination)] = edge.edge_type

            if edge.origin not in self._adjacency:
                self._adjacency[edge.origin] = []
            if edge.destination not in self._adjacency:
                self._adjacency[edge.destination] = []

            self._adjacency[edge.origin].append(
                (edge.destination, edge.distance, edge.edge_type)
            )

    def neighbors(
        self,
        node_id: str,
        allowed_types: set[str] | None = None,
    ) -> list[str]:
        """Get directly connected nodes, optionally filtered by edge type."""
        if allowed_types is None:
            return [n for n, _, _ in self._adjacency.get(node_id, [])]
        return [
            n
            for n, _, et in self._adjacency.get(node_id, [])
            if et in allowed_types
        ]

    def distance(self, origin: str, destination: str) -> float | None:
        """Get direct distance between two nodes, or None if not connected."""
        return self.distances.get((origin, destination))

    def shortest_path(
        self,
        origin: str,
        destination: str,
        allowed_types: set[str] | None = None,
        allowed_nodes: set[str] | None = None,
    ) -> list[str] | None:
        """
        Find shortest path using Dijkstra's algorithm.

        Returns list of node IDs from origin to destination (inclusive),
        or None if no path exists.

        If allowed_nodes is provided, intermediate nodes outside the set are
        skipped during expansion. Origin and destination are not filtered —
        callers chose them deliberately.
        """
        if origin == destination:
            return [origin]

        if origin not in self._adjacency or destination not in self._adjacency:
            return None

        all_nodes = set(self._adjacency.keys())
        dist: dict[str, float] = {nid: float("inf") for nid in all_nodes}
        prev: dict[str, str | None] = {nid: None for nid in all_nodes}
        dist[origin] = 0

        pq: list[tuple[float, str]] = [(0, origin)]
        visited: set[str] = set()

        while pq:
            d, current = heapq.heappop(pq)

            if current in visited:
                continue
            visited.add(current)

            if current == destination:
                break

            for neighbor, edge_dist, edge_type in self._adjacency.get(current, []):
                if allowed_types is not None and edge_type not in allowed_types:
                    continue
                if (
                    allowed_nodes is not None
                    and neighbor != destination
                    and neighbor not in allowed_nodes
                ):
                    continue
                if neighbor in visited:
                    continue
                new_dist = d + edge_dist
                if new_dist < dist[neighbor]:
                    dist[neighbor] = new_dist
                    prev[neighbor] = current
                    heapq.heappush(pq, (new_dist, neighbor))

        if prev[destination] is None and origin != destination:
            return None

        path: list[str] = []
        current_node: str | None = destination
        while current_node is not None:
            path.append(current_node)
            current_node = prev[current_node]

        return list(reversed(path))

    def shortest_path_distance(
        self,
        origin: str,
        destination: str,
        allowed_types: set[str] | None = None,
        allowed_nodes: set[str] | None = None,
    ) -> float | None:
        """Get total distance of shortest path, or None if no path exists."""
        path = self.shortest_path(origin, destination, allowed_types, allowed_nodes)
        if path is None:
            return None

        total = 0.0
        for i in range(len(path) - 1):
            edge_dist = self.distances.get((path[i], path[i + 1]))
            if edge_dist is None:
                return None
            total += edge_dist

        return total

    def to_dict(self) -> dict[str, Any]:
        """Convert graph to dictionary for JSON serialization."""
        return {
            "nodes": self.node_ids,
            "edges": [
                {
                    "origin": e.origin,
                    "destination": e.destination,
                    "distance": e.distance,
                    "edge_type": e.edge_type,
                }
                for e in self.edges
            ],
        }


def create_graph(
    node_ids: list[str],
    edges: list[Edge],
    bidirectional: bool = True,
) -> Graph:
    """
    Factory function to create a Graph.

    If bidirectional=True, adds reverse edges for each edge provided
    (unless a reverse edge already exists).
    """
    all_edges = list(edges)

    if bidirectional:
        existing = {(e.origin, e.destination) for e in edges}
        for edge in edges:
            if (edge.destination, edge.origin) not in existing:
                all_edges.append(
                    Edge(
                        origin=edge.destination,
                        destination=edge.origin,
                        distance=edge.distance,
                        edge_type=edge.edge_type,
                    )
                )
                existing.add((edge.destination, edge.origin))

    return Graph(node_ids=node_ids, edges=all_edges)
