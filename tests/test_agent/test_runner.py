"""Tests for agent runner and backends."""

from __future__ import annotations

from typing import Any

from constellation_core.agent.backends import DummyBackend, LLMAgent
from constellation_core.agent.model import AgentData
from constellation_core.agent.runner import AgentRunner
from constellation_core.engine.events import Event
from constellation_core.topology.graph import Graph
from constellation_core.topology.state import EnvironmentState


class SimplePlugin:
    def get_tick_phases(self) -> list[str]:
        return []

    def setup(self, state: EnvironmentState, config: dict) -> None:
        pass

    def run_phase(self, phase: str, state: EnvironmentState, config: dict) -> list[Event]:
        return []

    def build_observation(self, agent_id: str, state: EnvironmentState) -> dict:
        agent = state.agents[agent_id]
        return {"agent_id": agent_id, "location": agent.location}

    def get_available_actions(self, agent_id: str, state: EnvironmentState) -> list[str]:
        return ["buy", "sell", "hold"]

    def validate_action(
        self, agent_id: str, action: dict, state: EnvironmentState
    ) -> tuple[bool, str]:
        return True, ""

    def execute_action(
        self, agent_id: str, action: dict, state: EnvironmentState, tick: int
    ) -> list[Event]:
        return []


class StubAgent:
    def __init__(self, action: dict[str, Any]) -> None:
        self.last_observation: dict[str, Any] | None = None
        self._action = action

    def choose_action(self, observation: dict[str, Any]) -> dict[str, Any]:
        self.last_observation = observation
        return self._action


class TestAgentRunner:
    def test_collect_decisions(self):
        plugin = SimplePlugin()
        agent = StubAgent({"action": "hold"})
        runner = AgentRunner({"a1": agent}, plugin)

        state = EnvironmentState(
            tick=0,
            graph=Graph(node_ids=["x"], edges=[]),
            agents={"a1": AgentData("a1", "x")},
        )

        decisions = runner.collect_decisions(state)
        assert "a1" in decisions
        assert decisions["a1"] == {"action": "hold"}

    def test_observation_includes_available_actions(self):
        plugin = SimplePlugin()
        agent = StubAgent({"action": "buy"})
        runner = AgentRunner({"a1": agent}, plugin)

        state = EnvironmentState(
            tick=0,
            graph=Graph(node_ids=["x"], edges=[]),
            agents={"a1": AgentData("a1", "x")},
        )

        runner.collect_decisions(state)
        assert agent.last_observation is not None
        assert agent.last_observation["available_actions"] == ["buy", "sell", "hold"]

    def test_skips_agents_not_in_state(self):
        plugin = SimplePlugin()
        agent = StubAgent({"action": "hold"})
        runner = AgentRunner({"missing": agent}, plugin)

        state = EnvironmentState(
            tick=0,
            graph=Graph(node_ids=[], edges=[]),
        )

        decisions = runner.collect_decisions(state)
        assert len(decisions) == 0


class TestDummyBackend:
    def test_returns_hold(self):
        backend = DummyBackend()
        result = backend.complete("system", "user")
        assert "hold" in result


class TestLLMAgent:
    def test_parses_json_response(self):
        class MockBackend:
            def complete(self, system_prompt: str, user_message: str) -> str:
                return '{"action": "buy", "stock": "a"}'

        agent = LLMAgent(MockBackend(), "You are a trader.")
        action = agent.choose_action({"prices": {"a": 100}})
        assert action == {"action": "buy", "stock": "a"}

    def test_handles_invalid_json(self):
        class BadBackend:
            def complete(self, system_prompt: str, user_message: str) -> str:
                return "not json"

        agent = LLMAgent(BadBackend(), "prompt")
        action = agent.choose_action({})
        assert action["action"] == "hold"
        assert "error" in action
