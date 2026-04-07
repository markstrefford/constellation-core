"""Scenario event scheduling — mid-simulation shocks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from constellation_core.engine.events import ScenarioEvent


@dataclass
class ScenarioEventConfig:
    """Configuration for a scheduled scenario event."""

    tick: int
    event_type: str
    parameters: dict[str, Any]


class ScenarioScheduler:
    """
    Holds scheduled scenario events and returns them at the right tick.

    Events are loaded from config and sorted by tick. The tick loop
    calls get_events_for_tick() each tick and adds the results to the
    event stream. The domain plugin is responsible for interpreting
    and applying the events (e.g. modifying edge distances, changing
    node properties).
    """

    def __init__(self, events: list[ScenarioEventConfig]) -> None:
        self._events = sorted(events, key=lambda e: e.tick)

    def get_events_for_tick(self, tick: int) -> list[ScenarioEvent]:
        return [
            ScenarioEvent(
                tick=tick,
                event_type=e.event_type,
                parameters=dict(e.parameters),
            )
            for e in self._events
            if e.tick == tick
        ]
