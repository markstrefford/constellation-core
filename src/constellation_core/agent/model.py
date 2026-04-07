"""Agent data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentData:
    """
    An agent in the simulation.

    The core platform stores only id, location, and generic property/metadata
    dicts. All domain-specific state (fuel, cargo, cash, portfolio, morale,
    etc.) lives in properties. The core never interprets these values —
    the domain plugin reads and writes them.
    """

    id: str
    location: str
    properties: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
