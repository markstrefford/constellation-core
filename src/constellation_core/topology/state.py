"""Environment state — the shared mutable state of a simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from constellation_core.agent.model import AgentData
from constellation_core.topology.graph import Graph


@dataclass
class Node:
    """
    A node in the simulation environment.

    The core platform stores only id and generic property/metadata dicts.
    All domain-specific state (stock levels, prices, headcount, order books,
    etc.) lives in properties. The core never interprets these values —
    the domain plugin reads and writes them.
    """

    id: str
    properties: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EnvironmentState:
    """
    The complete mutable state of a running simulation.

    Passed to the plugin each tick. The plugin mutates nodes, agents,
    and (rarely) the graph in place.
    """

    tick: int
    graph: Graph
    nodes: dict[str, Node] = field(default_factory=dict)
    agents: dict[str, AgentData] = field(default_factory=dict)
