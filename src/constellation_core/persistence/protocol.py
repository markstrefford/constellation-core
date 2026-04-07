"""StorageBackend protocol — interface for persisting simulation data."""

from __future__ import annotations

from typing import Any, Protocol


class StorageBackend(Protocol):
    """Protocol for simulation data persistence."""

    def start_simulation(
        self,
        sim_id: str,
        config: dict[str, Any],
        topology: dict[str, Any] | None = None,
    ) -> None: ...

    def save_tick(
        self,
        sim_id: str,
        tick: int,
        events: list[dict[str, Any]],
    ) -> None: ...

    def complete_simulation(
        self,
        sim_id: str,
        final_tick: int,
        summary: dict[str, Any] | None = None,
    ) -> None: ...

    def get_simulation(self, sim_id: str) -> dict[str, Any] | None: ...

    def get_events(self, sim_id: str, tick: int) -> list[dict[str, Any]]: ...

    def list_simulations(self) -> list[dict[str, Any]]: ...

    def close(self) -> None: ...
