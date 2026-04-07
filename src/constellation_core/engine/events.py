"""Base event types for the simulation engine."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Event:
    """Base event — all events have tick and kind."""

    tick: int
    kind: str


@dataclass(frozen=True)
class TickEvent(Event):
    """Marks tick start or end."""

    kind: str = "TICK"
    payload: str = ""  # "start" or "end"


@dataclass(frozen=True)
class ScenarioEvent(Event):
    """A mid-simulation shock fired by the scenario scheduler."""

    kind: str = "SCENARIO"
    event_type: str = ""
    parameters: dict = field(default_factory=dict)
