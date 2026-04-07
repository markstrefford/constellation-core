"""Pydantic config schema for simulation configuration."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NodeConfig(BaseModel):
    id: str
    properties: dict[str, float] = {}
    metadata: dict[str, Any] = {}


class EdgeConfig(BaseModel):
    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")
    distance: float = Field(gt=0)
    edge_type: str = "default"
    bidirectional: bool = True

    model_config = {"populate_by_name": True}


class AgentConfig(BaseModel):
    id: str
    starting_location: str
    properties: dict[str, float] = {}
    metadata: dict[str, Any] = {}


class ScenarioEventConfig(BaseModel):
    tick: int = Field(ge=0)
    type: str
    parameters: dict[str, Any] = {}


class SimulationConfig(BaseModel):
    """Top-level simulation configuration."""

    seed: int = 42
    ticks: int = 500
    nodes: list[NodeConfig] = []
    edges: list[EdgeConfig] = []
    agents: list[AgentConfig] = []
    scenario_events: list[ScenarioEventConfig] = []
    domain: str = ""
    domain_config: dict[str, Any] = {}
    bidirectional_edges: bool = True

    def to_engine_config(self) -> dict[str, Any]:
        """Convert to the dict format the engine expects."""
        return {
            "seed": self.seed,
            "ticks": self.ticks,
            "nodes": [
                {
                    "id": n.id,
                    "properties": n.properties,
                    "metadata": n.metadata,
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "from": e.from_node,
                    "to": e.to_node,
                    "distance": e.distance,
                    "edge_type": e.edge_type,
                }
                for e in self.edges
            ],
            "agents": [
                {
                    "id": a.id,
                    "starting_location": a.starting_location,
                    "properties": a.properties,
                    "metadata": a.metadata,
                }
                for a in self.agents
            ],
            "scenario_events": [
                {
                    "tick": s.tick,
                    "type": s.type,
                    "parameters": s.parameters,
                }
                for s in self.scenario_events
            ],
            "domain": self.domain,
            "domain_config": self.domain_config,
            "bidirectional_edges": self.bidirectional_edges,
        }
