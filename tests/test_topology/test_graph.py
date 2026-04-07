"""Tests for graph topology and pathfinding."""

from constellation_core.topology.graph import Edge, Graph, create_graph


class TestEdge:
    def test_frozen(self):
        e = Edge("a", "b", 5.0)
        assert e.origin == "a"
        assert e.destination == "b"
        assert e.distance == 5.0
        assert e.edge_type == "default"

    def test_custom_edge_type(self):
        e = Edge("a", "b", 5.0, edge_type="ocean")
        assert e.edge_type == "ocean"


class TestGraph:
    def _simple_graph(self) -> Graph:
        """A -> B -> C, all distance 1."""
        edges = [
            Edge("a", "b", 1.0),
            Edge("b", "a", 1.0),
            Edge("b", "c", 1.0),
            Edge("c", "b", 1.0),
        ]
        return Graph(node_ids=["a", "b", "c"], edges=edges)

    def test_neighbors(self):
        g = self._simple_graph()
        assert set(g.neighbors("a")) == {"b"}
        assert set(g.neighbors("b")) == {"a", "c"}
        assert set(g.neighbors("c")) == {"b"}

    def test_distance_direct(self):
        g = self._simple_graph()
        assert g.distance("a", "b") == 1.0
        assert g.distance("a", "c") is None  # not directly connected

    def test_shortest_path_adjacent(self):
        g = self._simple_graph()
        assert g.shortest_path("a", "b") == ["a", "b"]

    def test_shortest_path_two_hops(self):
        g = self._simple_graph()
        assert g.shortest_path("a", "c") == ["a", "b", "c"]

    def test_shortest_path_same_node(self):
        g = self._simple_graph()
        assert g.shortest_path("a", "a") == ["a"]

    def test_shortest_path_distance(self):
        g = self._simple_graph()
        assert g.shortest_path_distance("a", "c") == 2.0

    def test_shortest_path_disconnected(self):
        edges = [Edge("a", "b", 1.0)]
        g = Graph(node_ids=["a", "b", "c"], edges=edges)
        assert g.shortest_path("a", "c") is None
        assert g.shortest_path_distance("a", "c") is None

    def test_shortest_path_chooses_shortest(self):
        """Diamond: A->B(1)->D(1) vs A->C(5)->D(1). Should pick A->B->D."""
        edges = [
            Edge("a", "b", 1.0),
            Edge("a", "c", 5.0),
            Edge("b", "d", 1.0),
            Edge("c", "d", 1.0),
        ]
        g = Graph(node_ids=["a", "b", "c", "d"], edges=edges)
        assert g.shortest_path("a", "d") == ["a", "b", "d"]
        assert g.shortest_path_distance("a", "d") == 2.0

    def test_edge_type_filtering(self):
        edges = [
            Edge("a", "b", 1.0, edge_type="road"),
            Edge("b", "c", 1.0, edge_type="ocean"),
            Edge("a", "c", 10.0, edge_type="road"),
        ]
        g = Graph(node_ids=["a", "b", "c"], edges=edges)

        # Road only: must go A->C direct (B->C is ocean)
        assert g.neighbors("b", allowed_types={"road"}) == []
        path = g.shortest_path("a", "c", allowed_types={"road"})
        assert path == ["a", "c"]

        # Ocean only: can't reach C from A (A->B is road)
        assert g.shortest_path("a", "c", allowed_types={"ocean"}) is None

        # All types: goes through B
        assert g.shortest_path("a", "c") == ["a", "b", "c"]

    def test_nonexistent_node(self):
        g = self._simple_graph()
        assert g.shortest_path("a", "z") is None
        assert g.neighbors("z") == []

    def test_to_dict(self):
        edges = [Edge("a", "b", 1.0)]
        g = Graph(node_ids=["a", "b"], edges=edges)
        d = g.to_dict()
        assert d["nodes"] == ["a", "b"]
        assert len(d["edges"]) == 1
        assert d["edges"][0]["origin"] == "a"
        assert d["edges"][0]["distance"] == 1.0


class TestCreateGraph:
    def test_bidirectional(self):
        edges = [Edge("a", "b", 3.0)]
        g = create_graph(["a", "b"], edges, bidirectional=True)
        # Should have both directions
        assert g.distance("a", "b") == 3.0
        assert g.distance("b", "a") == 3.0

    def test_unidirectional(self):
        edges = [Edge("a", "b", 3.0)]
        g = create_graph(["a", "b"], edges, bidirectional=False)
        assert g.distance("a", "b") == 3.0
        assert g.distance("b", "a") is None

    def test_no_duplicate_reverse(self):
        """If both directions already provided, don't duplicate."""
        edges = [Edge("a", "b", 3.0), Edge("b", "a", 3.0)]
        g = create_graph(["a", "b"], edges, bidirectional=True)
        assert len(g.edges) == 2  # not 4
