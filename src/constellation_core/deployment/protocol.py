"""Deployment backend protocol."""

from __future__ import annotations

from typing import Any, AsyncIterator, Protocol


class DeploymentBackend(Protocol):
    """Abstraction over where simulations run."""

    async def run_simulation(self, config: dict[str, Any]) -> str:
        """Start a simulation. Returns a handle ID."""
        ...

    async def get_status(self, handle: str) -> str:
        """Get simulation status."""
        ...

    async def stream_events(self, handle: str) -> AsyncIterator[dict[str, Any]]:
        """Stream events from a running simulation."""
        ...
