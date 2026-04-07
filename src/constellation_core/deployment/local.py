"""Local deployment backend — runs simulation in-process."""

from __future__ import annotations

import threading
import uuid
from typing import Any, AsyncIterator

from constellation_core.config.loader import resolve_plugin
from constellation_core.engine.simulation import Simulation


class LocalDeployment:
    """Runs simulations in a background thread. Default for open source."""

    def __init__(self) -> None:
        self._simulations: dict[str, dict[str, Any]] = {}

    async def run_simulation(self, config: dict[str, Any]) -> str:
        handle = str(uuid.uuid4())[:8]
        self._simulations[handle] = {"status": "running", "events": []}

        plugin = resolve_plugin(config.get("domain", ""))
        sim = Simulation(plugin, config)
        sim.setup()

        def _run() -> None:
            try:
                events = sim.run()
                self._simulations[handle]["events"] = events
                self._simulations[handle]["status"] = "completed"
            except Exception as e:
                self._simulations[handle]["status"] = f"failed: {e}"

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return handle

    async def get_status(self, handle: str) -> str:
        if handle not in self._simulations:
            return "unknown"
        return self._simulations[handle]["status"]

    async def stream_events(self, handle: str) -> AsyncIterator[dict[str, Any]]:
        raise NotImplementedError("Streaming not yet implemented for LocalDeployment")
