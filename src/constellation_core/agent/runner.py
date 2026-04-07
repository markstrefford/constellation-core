"""Agent runner — orchestrates agent decisions each tick."""

from __future__ import annotations

from typing import Any

from constellation_core.agent.protocol import AgentDecision
from constellation_core.engine.plugin import SimulationPlugin
from constellation_core.topology.state import EnvironmentState


class AgentRunner:
    """
    Collects decisions from all agents.

    Domain plugins call this from their "decisions" phase. The runner
    builds each agent's observation via the plugin, appends
    available_actions, and calls the agent's choose_action().
    """

    def __init__(
        self,
        agents: dict[str, AgentDecision],
        plugin: SimulationPlugin,
    ) -> None:
        self.agents = agents
        self.plugin = plugin

    def collect_decisions(
        self,
        state: EnvironmentState,
    ) -> dict[str, dict[str, Any]]:
        """
        Get decisions from all registered agents.

        Returns {agent_id: action_dict}.
        """
        decisions: dict[str, dict[str, Any]] = {}

        for agent_id, agent in self.agents.items():
            if agent_id not in state.agents:
                continue

            observation = self.plugin.build_observation(agent_id, state)
            observation["available_actions"] = self.plugin.get_available_actions(
                agent_id, state
            )

            action = agent.choose_action(observation)
            decisions[agent_id] = action

        return decisions
