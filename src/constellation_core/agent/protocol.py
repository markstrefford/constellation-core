"""Agent decision protocol — the JSON-in, JSON-out contract."""

from __future__ import annotations

from typing import Any, Protocol


class AgentDecision(Protocol):
    """
    The contract between an agent and the simulation.

    The observation is whatever the plugin's build_observation() returns.
    The action dict is whatever the plugin's validate_action() accepts.
    The core never interprets either — they are opaque JSON-like dicts.
    """

    def choose_action(self, observation: dict[str, Any]) -> dict[str, Any]:
        ...
