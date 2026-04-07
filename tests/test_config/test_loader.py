"""Tests for config loading and validation."""

from __future__ import annotations

import tempfile
from pathlib import Path

import yaml

from constellation_core.config.loader import (
    load_config,
    register_plugin,
    resolve_plugin,
)
from constellation_core.config.schema import SimulationConfig


SAMPLE_YAML = {
    "seed": 1,
    "ticks": 100,
    "domain": "test",
    "nodes": [
        {"id": "a", "properties": {"stock": 50}, "metadata": {"label": "Node A"}},
        {"id": "b", "properties": {"stock": 30}},
    ],
    "edges": [
        {"from": "a", "to": "b", "distance": 5.0, "edge_type": "road"},
    ],
    "agents": [
        {
            "id": "agent1",
            "starting_location": "a",
            "properties": {"cash": 1000},
            "metadata": {"strategy": "greedy"},
        },
    ],
    "scenario_events": [
        {"tick": 50, "type": "shock", "parameters": {"magnitude": 2}},
    ],
    "domain_config": {"price_elasticity": 0.5},
}


class TestLoadConfig:
    def test_roundtrip(self, tmp_path: Path):
        config_path = tmp_path / "test.yaml"
        with open(config_path, "w") as f:
            yaml.dump(SAMPLE_YAML, f)

        config = load_config(config_path)
        assert config.seed == 1
        assert config.ticks == 100
        assert config.domain == "test"
        assert len(config.nodes) == 2
        assert config.nodes[0].id == "a"
        assert config.nodes[0].properties["stock"] == 50
        assert config.nodes[0].metadata["label"] == "Node A"
        assert len(config.edges) == 1
        assert config.edges[0].from_node == "a"
        assert config.edges[0].edge_type == "road"
        assert len(config.agents) == 1
        assert config.agents[0].starting_location == "a"
        assert len(config.scenario_events) == 1
        assert config.scenario_events[0].tick == 50
        assert config.domain_config["price_elasticity"] == 0.5

    def test_defaults(self):
        config = SimulationConfig()
        assert config.seed == 42
        assert config.ticks == 500
        assert config.nodes == []
        assert config.domain == ""

    def test_to_engine_config(self):
        config = SimulationConfig(**SAMPLE_YAML)
        ec = config.to_engine_config()
        assert ec["ticks"] == 100
        assert len(ec["nodes"]) == 2
        assert ec["nodes"][0]["id"] == "a"
        assert ec["edges"][0]["from"] == "a"
        assert ec["agents"][0]["starting_location"] == "a"


class TestPluginRegistry:
    def test_register_and_resolve(self):
        class FakePlugin:
            pass

        register_plugin("fake", FakePlugin)
        plugin = resolve_plugin("fake")
        assert isinstance(plugin, FakePlugin)

    def test_unknown_plugin_raises(self):
        try:
            resolve_plugin("nonexistent_plugin_xyz")
            assert False, "Should have raised"
        except ValueError as e:
            assert "nonexistent_plugin_xyz" in str(e)
