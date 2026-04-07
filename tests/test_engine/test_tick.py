"""Tests for the tick loop."""

from __future__ import annotations

from typing import Any

from constellation_core.engine.events import Event, ScenarioEvent, TickEvent
from constellation_core.engine.scenario import ScenarioEventConfig, ScenarioScheduler
from constellation_core.engine.tick import run_tick
from constellation_core.topology.graph import Graph
from constellation_core.topology.state import EnvironmentState


class StubPlugin:
    """A minimal plugin for testing the tick loop."""

    def __init__(self, phases: list[str] | None = None) -> None:
        self.phases = phases or ["phase_a", "phase_b"]
        self.phase_calls: list[str] = []

    def get_tick_phases(self) -> list[str]:
        return self.phases

    def setup(self, state: EnvironmentState, config: dict[str, Any]) -> None:
        pass

    def run_phase(
        self, phase: str, state: EnvironmentState, config: dict[str, Any]
    ) -> list[Event]:
        self.phase_calls.append(phase)
        return [Event(tick=state.tick, kind=f"TEST_{phase.upper()}")]

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


def _empty_state(tick: int = 0) -> EnvironmentState:
    return EnvironmentState(tick=tick, graph=Graph(node_ids=[], edges=[]))


class TestRunTick:
    def test_tick_start_and_end_events(self):
        plugin = StubPlugin()
        state = _empty_state()
        events = run_tick(state, plugin, {})

        tick_events = [e for e in events if isinstance(e, TickEvent)]
        assert tick_events[0].payload == "start"
        assert tick_events[-1].payload == "end"

    def test_phases_called_in_order(self):
        plugin = StubPlugin(phases=["alpha", "beta", "gamma"])
        state = _empty_state()
        run_tick(state, plugin, {})
        assert plugin.phase_calls == ["alpha", "beta", "gamma"]

    def test_tick_increments(self):
        plugin = StubPlugin()
        state = _empty_state(tick=5)
        run_tick(state, plugin, {})
        assert state.tick == 6

    def test_phase_events_included(self):
        plugin = StubPlugin(phases=["phase_a"])
        state = _empty_state()
        events = run_tick(state, plugin, {})
        kinds = [e.kind for e in events]
        assert "TEST_PHASE_A" in kinds

    def test_scenario_events_fire(self):
        plugin = StubPlugin()
        scheduler = ScenarioScheduler([
            ScenarioEventConfig(tick=0, event_type="disruption", parameters={"x": 1}),
        ])
        state = _empty_state(tick=0)
        events = run_tick(state, plugin, {}, scenario_scheduler=scheduler)

        scenario = [e for e in events if isinstance(e, ScenarioEvent)]
        assert len(scenario) == 1
        assert scenario[0].event_type == "disruption"
        assert scenario[0].parameters == {"x": 1}

    def test_scenario_events_only_on_matching_tick(self):
        plugin = StubPlugin()
        scheduler = ScenarioScheduler([
            ScenarioEventConfig(tick=5, event_type="shock", parameters={}),
        ])
        state = _empty_state(tick=0)
        events = run_tick(state, plugin, {}, scenario_scheduler=scheduler)
        scenario = [e for e in events if isinstance(e, ScenarioEvent)]
        assert len(scenario) == 0

    def test_multiple_scenario_events_same_tick(self):
        plugin = StubPlugin()
        scheduler = ScenarioScheduler([
            ScenarioEventConfig(tick=0, event_type="a", parameters={}),
            ScenarioEventConfig(tick=0, event_type="b", parameters={}),
        ])
        state = _empty_state(tick=0)
        events = run_tick(state, plugin, {}, scenario_scheduler=scheduler)
        scenario = [e for e in events if isinstance(e, ScenarioEvent)]
        assert len(scenario) == 2


class TestScenarioScheduler:
    def test_empty(self):
        s = ScenarioScheduler([])
        assert s.get_events_for_tick(0) == []

    def test_returns_correct_tick(self):
        s = ScenarioScheduler([
            ScenarioEventConfig(tick=10, event_type="shock", parameters={"val": 42}),
            ScenarioEventConfig(tick=20, event_type="other", parameters={}),
        ])
        events = s.get_events_for_tick(10)
        assert len(events) == 1
        assert events[0].event_type == "shock"
        assert events[0].parameters == {"val": 42}
