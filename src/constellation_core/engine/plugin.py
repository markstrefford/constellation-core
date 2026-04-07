"""SimulationPlugin protocol — the contract between engine and domain."""

from __future__ import annotations

from typing import Any, Protocol

from constellation_core.engine.events import Event
from constellation_core.topology.state import EnvironmentState


class SimulationPlugin(Protocol):
    """
    Domain plugin that defines simulation behaviour.

    The engine calls these methods in order each tick. The plugin owns
    the phase list, the phase logic, the observation format, the action
    validation, and the action execution. The engine just calls them.
    """

    def get_tick_phases(self) -> list[str]:
        """Return ordered list of phase names for each tick."""
        ...

    def setup(self, state: EnvironmentState, config: dict[str, Any]) -> None:
        """
        Initialize domain-specific state after the engine builds
        the EnvironmentState from config. Called once before the
        first tick.
        """
        ...

    def run_phase(
        self,
        phase: str,
        state: EnvironmentState,
        config: dict[str, Any],
    ) -> list[Event]:
        """Execute one phase. Mutates state in place. Returns events."""
        ...

    def build_observation(
        self,
        agent_id: str,
        state: EnvironmentState,
    ) -> dict[str, Any]:
        """Build the observation dict that an agent receives."""
        ...

    def get_available_actions(
        self,
        agent_id: str,
        state: EnvironmentState,
    ) -> list[str]:
        """Return action names this agent can take right now."""
        ...

    def validate_action(
        self,
        agent_id: str,
        action: dict[str, Any],
        state: EnvironmentState,
    ) -> tuple[bool, str]:
        """Validate an action. Returns (valid, error_message)."""
        ...

    def execute_action(
        self,
        agent_id: str,
        action: dict[str, Any],
        state: EnvironmentState,
        tick: int,
    ) -> list[Event]:
        """Execute a validated action. Mutates state. Returns events."""
        ...
