"""YAML config loading and plugin resolution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from constellation_core.config.schema import SimulationConfig


def load_config(path: str | Path) -> SimulationConfig:
    """Load and validate a simulation config from a YAML file."""
    with open(path) as f:
        raw = yaml.safe_load(f)
    return SimulationConfig(**raw)


# Plugin registry — examples register themselves here
_plugin_registry: dict[str, Any] = {}


def register_plugin(name: str, plugin_class: Any) -> None:
    """Register a domain plugin class by name."""
    _plugin_registry[name] = plugin_class


def resolve_plugin(name: str) -> Any:
    """Look up a registered plugin by name. Returns an instance."""
    if name not in _plugin_registry:
        available = ", ".join(_plugin_registry.keys()) or "(none)"
        raise ValueError(
            f"Unknown domain plugin: {name!r}. Available: {available}"
        )
    return _plugin_registry[name]()
