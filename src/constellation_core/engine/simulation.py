"""Simulation class — setup and run."""

from __future__ import annotations

from typing import Any, Iterator

from constellation_core.agent.model import AgentData
from constellation_core.engine.events import Event
from constellation_core.engine.plugin import SimulationPlugin
from constellation_core.engine.scenario import ScenarioEventConfig, ScenarioScheduler
from constellation_core.engine.tick import run_tick
from constellation_core.topology.graph import Edge, create_graph
from constellation_core.topology.state import EnvironmentState, Node


class Simulation:
    """
    Orchestrates a simulation run.

    Builds EnvironmentState from config, delegates domain-specific
    setup to the plugin, then runs the tick loop.
    """

    def __init__(
        self,
        plugin: SimulationPlugin,
        config: dict[str, Any],
    ) -> None:
        self.plugin = plugin
        self.config = config
        self.state: EnvironmentState | None = None
        self._scenario_scheduler: ScenarioScheduler | None = None

    def setup(self) -> None:
        """Build environment state from config and call plugin setup."""
        node_configs = self.config.get("nodes", [])
        edge_configs = self.config.get("edges", [])
        agent_configs = self.config.get("agents", [])
        scenario_configs = self.config.get("scenario_events", [])

        # Build nodes
        nodes: dict[str, Node] = {}
        node_ids: list[str] = []
        for nc in node_configs:
            nid = nc["id"]
            node_ids.append(nid)
            nodes[nid] = Node(
                id=nid,
                properties=dict(nc.get("properties", {})),
                metadata=dict(nc.get("metadata", {})),
            )

        # Build edges
        edges: list[Edge] = []
        for ec in edge_configs:
            edges.append(
                Edge(
                    origin=ec["from"],
                    destination=ec["to"],
                    distance=ec["distance"],
                    edge_type=ec.get("edge_type", "default"),
                )
            )
        bidirectional = self.config.get("bidirectional_edges", True)
        graph = create_graph(node_ids, edges, bidirectional=bidirectional)

        # Build agents
        agents: dict[str, AgentData] = {}
        for ac in agent_configs:
            aid = ac["id"]
            agents[aid] = AgentData(
                id=aid,
                location=ac["starting_location"],
                properties=dict(ac.get("properties", {})),
                metadata=dict(ac.get("metadata", {})),
            )

        self.state = EnvironmentState(
            tick=0,
            graph=graph,
            nodes=nodes,
            agents=agents,
        )

        # Scenario scheduler
        if scenario_configs:
            self._scenario_scheduler = ScenarioScheduler([
                ScenarioEventConfig(
                    tick=sc["tick"],
                    event_type=sc["type"],
                    parameters=sc.get("parameters", {}),
                )
                for sc in scenario_configs
            ])

        # Let the plugin do domain-specific setup
        domain_config = self.config.get("domain_config", {})
        self.plugin.setup(self.state, domain_config)

    def run(self, ticks: int | None = None) -> list[Event]:
        """Run simulation for N ticks. Returns all events."""
        if self.state is None:
            raise RuntimeError("Call setup() before run()")

        total_ticks = ticks or self.config.get("ticks", 100)
        all_events: list[Event] = []
        domain_config = self.config.get("domain_config", {})

        for _ in range(total_ticks):
            tick_events = run_tick(
                self.state,
                self.plugin,
                domain_config,
                self._scenario_scheduler,
            )
            all_events.extend(tick_events)

        return all_events

    def run_streaming(self, ticks: int | None = None) -> Iterator[list[Event]]:
        """Run simulation, yielding per-tick event batches."""
        if self.state is None:
            raise RuntimeError("Call setup() before run_streaming()")

        total_ticks = ticks or self.config.get("ticks", 100)
        domain_config = self.config.get("domain_config", {})

        for _ in range(total_ticks):
            tick_events = run_tick(
                self.state,
                self.plugin,
                domain_config,
                self._scenario_scheduler,
            )
            yield tick_events
