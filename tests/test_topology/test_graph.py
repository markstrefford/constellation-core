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

    def test_allowed_nodes_excludes_intermediate(self):
        """4-node chain A-B-C-D. Excluding B blocks the only route."""
        edges = [
            Edge("a", "b", 1.0),
            Edge("b", "a", 1.0),
            Edge("b", "c", 1.0),
            Edge("c", "b", 1.0),
            Edge("c", "d", 1.0),
            Edge("d", "c", 1.0),
        ]
        g = Graph(node_ids=["a", "b", "c", "d"], edges=edges)
        assert (
            g.shortest_path("a", "d", allowed_nodes={"a", "c", "d"}) is None
        )

    def test_allowed_nodes_picks_permitted_route(self):
        """Two routes A->D: through B (permitted) vs through C (blocked)."""
        edges = [
            Edge("a", "b", 1.0),
            Edge("b", "d", 1.0),
            Edge("a", "c", 1.0),
            Edge("c", "d", 1.0),
        ]
        g = Graph(node_ids=["a", "b", "c", "d"], edges=edges)
        path = g.shortest_path("a", "d", allowed_nodes={"a", "b", "d"})
        assert path == ["a", "b", "d"]

    def test_allowed_nodes_does_not_filter_endpoints(self):
        """Endpoints are not subject to the filter even if absent from set."""
        edges = [Edge("a", "b", 1.0), Edge("b", "c", 1.0)]
        g = Graph(node_ids=["a", "b", "c"], edges=edges)
        # Endpoint 'c' missing from set: still reachable.
        assert g.shortest_path("a", "c", allowed_nodes={"a", "b"}) == [
            "a",
            "b",
            "c",
        ]

    def test_allowed_nodes_combined_with_allowed_types(self):
        """Both filters apply simultaneously."""
        edges = [
            Edge("a", "b", 1.0, edge_type="road"),
            Edge("b", "d", 1.0, edge_type="road"),
            Edge("a", "c", 1.0, edge_type="ocean"),
            Edge("c", "d", 1.0, edge_type="ocean"),
        ]
        g = Graph(node_ids=["a", "b", "c", "d"], edges=edges)
        # Road-only with B blocked: no path.
        assert (
            g.shortest_path(
                "a",
                "d",
                allowed_types={"road"},
                allowed_nodes={"a", "c", "d"},
            )
            is None
        )
        # Ocean-only with B blocked: still works via C.
        assert g.shortest_path(
            "a",
            "d",
            allowed_types={"ocean"},
            allowed_nodes={"a", "c", "d"},
        ) == ["a", "c", "d"]

    def test_allowed_nodes_default_preserves_behaviour(self):
        g = self._simple_graph()
        assert g.shortest_path("a", "c") == ["a", "b", "c"]
        assert g.shortest_path("a", "c", allowed_nodes=None) == ["a", "b", "c"]

    def test_shortest_path_distance_honours_allowed_nodes(self):
        """Distance reflects the filtered path, not the unrestricted shortest."""
        edges = [
            Edge("a", "b", 1.0),
            Edge("b", "d", 1.0),
            Edge("a", "c", 5.0),
            Edge("c", "d", 5.0),
        ]
        g = Graph(node_ids=["a", "b", "c", "d"], edges=edges)
        # Unrestricted: A->B->D = 2.0
        assert g.shortest_path_distance("a", "d") == 2.0
        # Block B: forced through C = 10.0
        assert (
            g.shortest_path_distance("a", "d", allowed_nodes={"a", "c", "d"})
            == 10.0
        )

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
