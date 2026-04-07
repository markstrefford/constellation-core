"""Generic tick loop — calls plugin phases in order."""

from __future__ import annotations

from typing import Any

from constellation_core.engine.events import Event, TickEvent
from constellation_core.engine.plugin import SimulationPlugin
from constellation_core.engine.scenario import ScenarioScheduler
from constellation_core.topology.state import EnvironmentState


def run_tick(
    state: EnvironmentState,
    plugin: SimulationPlugin,
    config: dict[str, Any],
    scenario_scheduler: ScenarioScheduler | None = None,
) -> list[Event]:
    """
    Execute one tick of simulation. Mutates state in place.

    1. Emit tick-start event
    2. Fire any scenario events scheduled for this tick
    3. Run each domain-defined phase via the plugin
    4. Emit tick-end event
    5. Increment tick counter

    Returns all events produced during this tick.
    """
    events: list[Event] = []
    tick = state.tick

    events.append(TickEvent(tick=tick, payload="start"))

    if scenario_scheduler is not None:
        scenario_events = scenario_scheduler.get_events_for_tick(tick)
        events.extend(scenario_events)
        # Notify plugin if it supports scenario event handling
        if scenario_events and hasattr(plugin, "notify_scenario_event"):
            for se in scenario_events:
                plugin.notify_scenario_event(se)  # type: ignore[attr-defined]

    for phase in plugin.get_tick_phases():
        phase_events = plugin.run_phase(phase, state, config)
        events.extend(phase_events)

    events.append(TickEvent(tick=tick, payload="end"))

    state.tick += 1

    return events
