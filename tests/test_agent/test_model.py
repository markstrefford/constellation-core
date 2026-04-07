"""Tests for agent data model."""

from constellation_core.agent.model import AgentData


class TestAgentData:
    def test_creation(self):
        a = AgentData(id="trader_1", location="exchange")
        assert a.id == "trader_1"
        assert a.location == "exchange"
        assert a.properties == {}
        assert a.metadata == {}

    def test_domain_properties(self):
        a = AgentData(
            id="truck_1",
            location="rotterdam",
            properties={"fuel": 100, "cargo_quantity": 50, "status": 0},
            metadata={"role": "logistics", "home_route": ["rotterdam", "stuttgart"]},
        )
        assert a.properties["fuel"] == 100
        assert a.metadata["role"] == "logistics"

    def test_mutable(self):
        a = AgentData(id="t", location="a", properties={"cash": 1000})
        a.location = "b"
        a.properties["cash"] = 800
        assert a.location == "b"
        assert a.properties["cash"] == 800
