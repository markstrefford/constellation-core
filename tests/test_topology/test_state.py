"""Tests for environment state."""

from constellation_core.agent.model import AgentData
from constellation_core.topology.graph import Edge, Graph
from constellation_core.topology.state import EnvironmentState, Node


class TestNode:
    def test_creation(self):
        n = Node(id="factory", properties={"headcount": 50, "budget": 1000})
        assert n.id == "factory"
        assert n.properties["headcount"] == 50

    def test_mutable_properties(self):
        n = Node(id="factory", properties={"stock": 100})
        n.properties["stock"] = 80
        assert n.properties["stock"] == 80

    def test_metadata(self):
        n = Node(id="factory", metadata={"label": "Stuttgart Factory", "type": "factory"})
        assert n.metadata["label"] == "Stuttgart Factory"

    def test_defaults(self):
        n = Node(id="x")
        assert n.properties == {}
        assert n.metadata == {}

    def test_mixed_type_properties(self):
        n = Node(
            id="planet",
            properties={
                "stock": 100.0,
                "role": "refiner",
                "production": {"fuel_raw": 10.0, "food": 3.0},
                "queue": [1, 2, 3],
            },
        )
        assert n.properties["stock"] == 100.0
        assert n.properties["role"] == "refiner"
        assert n.properties["production"]["fuel_raw"] == 10.0
        assert n.properties["queue"] == [1, 2, 3]


class TestEnvironmentState:
    def test_creation(self):
        g = Graph(node_ids=["a", "b"], edges=[Edge("a", "b", 1.0)])
        nodes = {"a": Node("a", {"stock": 10}), "b": Node("b", {"stock": 20})}
        agents = {"agent1": AgentData("agent1", "a", {"cash": 100})}
        state = EnvironmentState(tick=0, graph=g, nodes=nodes, agents=agents)

        assert state.tick == 0
        assert len(state.nodes) == 2
        assert len(state.agents) == 1
        assert state.agents["agent1"].location == "a"

    def test_tick_increment(self):
        g = Graph(node_ids=[], edges=[])
        state = EnvironmentState(tick=0, graph=g)
        state.tick += 1
        assert state.tick == 1

    def test_mutate_node_properties(self):
        g = Graph(node_ids=["a"], edges=[])
        state = EnvironmentState(
            tick=0, graph=g, nodes={"a": Node("a", {"price": 100})}
        )
        state.nodes["a"].properties["price"] = 120
        assert state.nodes["a"].properties["price"] == 120
