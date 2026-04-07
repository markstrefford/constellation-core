"""Tests for the Simulation class."""

from __future__ import annotations

from typing import Any

from constellation_core.engine.events import Event, ScenarioEvent, TickEvent
from constellation_core.engine.simulation import Simulation
from constellation_core.topology.state import EnvironmentState


class CountingPlugin:
    """Plugin that counts phase calls and emits one event per phase."""

    def __init__(self) -> None:
        self.setup_called = False
        self.phase_count = 0

    def get_tick_phases(self) -> list[str]:
        return ["step"]

    def setup(self, state: EnvironmentState, config: dict[str, Any]) -> None:
        self.setup_called = True

    def run_phase(
        self, phase: str, state: EnvironmentState, config: dict[str, Any]
    ) -> list[Event]:
        self.phase_count += 1
        return [Event(tick=state.tick, kind="COUNTED")]

    def build_observation(self, agent_id: str, state: EnvironmentState) -> dict:
        return {}

    def get_available_actions(self, agent_id: str, state: EnvironmentState) -> list[str]:
        return []

    def validate_action(
        self, agent_id: str, action: dict, state: EnvironmentState
    ) -> tuple[bool, str]:
        return True, ""

    def execute_action(
        self, agent_id: str, action: dict, state: EnvironmentState, tick: int
    ) -> list[Event]:
        return []


BASIC_CONFIG = {
    "ticks": 10,
    "nodes": [
        {"id": "a", "properties": {"val": 1}},
        {"id": "b", "properties": {"val": 2}},
    ],
    "edges": [
        {"from": "a", "to": "b", "distance": 5.0},
    ],
    "agents": [
        {"id": "agent1", "starting_location": "a", "properties": {"cash": 100}},
    ],
}


class TestSimulation:
    def test_setup_builds_state(self):
        plugin = CountingPlugin()
        sim = Simulation(plugin, BASIC_CONFIG)
        sim.setup()

        assert sim.state is not None
        assert len(sim.state.nodes) == 2
        assert len(sim.state.agents) == 1
        assert sim.state.agents["agent1"].location == "a"
        assert sim.state.agents["agent1"].properties["cash"] == 100
        assert plugin.setup_called

    def test_setup_builds_graph(self):
        plugin = CountingPlugin()
        sim = Simulation(plugin, BASIC_CONFIG)
        sim.setup()

        assert sim.state is not None
        # Bidirectional by default
        assert sim.state.graph.distance("a", "b") == 5.0
        assert sim.state.graph.distance("b", "a") == 5.0

    def test_run(self):
        plugin = CountingPlugin()
        sim = Simulation(plugin, BASIC_CONFIG)
        sim.setup()
        events = sim.run(ticks=5)

        assert plugin.phase_count == 5
        assert sim.state is not None
        assert sim.state.tick == 5
        # Each tick: TickEvent(start) + COUNTED + TickEvent(end) = 3 events
        assert len(events) == 15

    def test_run_uses_config_ticks(self):
        plugin = CountingPlugin()
        sim = Simulation(plugin, BASIC_CONFIG)
        sim.setup()
        events = sim.run()
        assert plugin.phase_count == 10  # from config["ticks"]

    def test_run_streaming(self):
        plugin = CountingPlugin()
        sim = Simulation(plugin, BASIC_CONFIG)
        sim.setup()

        batches = list(sim.run_streaming(ticks=3))
        assert len(batches) == 3
        for batch in batches:
            assert any(isinstance(e, TickEvent) for e in batch)

    def test_run_without_setup_raises(self):
        plugin = CountingPlugin()
        sim = Simulation(plugin, BASIC_CONFIG)
        try:
            sim.run()
            assert False, "Should have raised"
        except RuntimeError as e:
            assert "setup()" in str(e)

    def test_scenario_events(self):
        config = {
            **BASIC_CONFIG,
            "scenario_events": [
                {"tick": 2, "type": "shock", "parameters": {"magnitude": 5}},
            ],
        }
        plugin = CountingPlugin()
        sim = Simulation(plugin, config)
        sim.setup()
        events = sim.run(ticks=5)

        scenarios = [e for e in events if isinstance(e, ScenarioEvent)]
        assert len(scenarios) == 1
        assert scenarios[0].event_type == "shock"
        assert scenarios[0].tick == 2

    def test_node_metadata(self):
        config = {
            **BASIC_CONFIG,
            "nodes": [
                {"id": "x", "properties": {"v": 1}, "metadata": {"label": "Node X"}},
            ],
            "edges": [],
        }
        plugin = CountingPlugin()
        sim = Simulation(plugin, config)
        sim.setup()
        assert sim.state is not None
        assert sim.state.nodes["x"].metadata["label"] == "Node X"
