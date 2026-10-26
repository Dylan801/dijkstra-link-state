import unittest
from fractions import Fraction
from dijkstra.examples import reference_graph
from dijkstra.core.graph import NetworkGraph
from dijkstra.core.lsdb import LinkStateDatabase
from dijkstra.core.spf import dijkstra, reconstruct_path

def make_graph(routers, links):
    graph = NetworkGraph()
    for router in routers:
        graph.add_router(router)
    for source, target, cost in links:
        graph.add_link(source, target, cost)
    return graph

class DijkstraTests(unittest.TestCase):
    def test_reference_exact(self):
        result = dijkstra(LinkStateDatabase(reference_graph()), "R1")
        self.assertEqual(result.distances, dict(R1=0, R2=2, R3=3, R4=4, R5=5, R6=float("inf")))
        self.assertEqual(result.predecessors, dict(R1=None, R2="R1", R3="R2", R4="R2", R5="R4", R6=None))
        expected = {"R1": ["R1"], "R2": ["R1", "R2"], "R3": ["R1", "R2", "R3"],
                    "R4": ["R1", "R2", "R4"], "R5": ["R1", "R2", "R4", "R5"], "R6": []}
        for destination, path in expected.items():
            self.assertEqual(reconstruct_path(result.predecessors, "R1", destination), path)
        self.assertEqual(result.tree_edges, [("R1", "R2"), ("R2", "R3"), ("R2", "R4"), ("R4", "R5")])

    def test_single_and_two(self):
        for graph in (make_graph(["A"], []), make_graph(["A", "B"], [("A", "B", 2)])):
            result = dijkstra(LinkStateDatabase(graph), "A")
            self.assertEqual(result.distances["A"], 0)
            if "B" in result.distances:
                self.assertEqual(result.distances["B"], 2)

    def test_disconnected_components(self):
        graph = make_graph("ABCD", [("A", "B", 1), ("C", "D", 1)])
        result = dijkstra(LinkStateDatabase(graph), "A")
        self.assertEqual(result.distances["C"], float("inf"))
        self.assertEqual(reconstruct_path(result.predecessors, "A", "D"), [])

    def test_ties_and_insertion_order(self):
        links = [("A", "C", 1), ("C", "D", 1), ("A", "B", 1), ("B", "D", 1)]
        results = [dijkstra(LinkStateDatabase(make_graph("DCBA", order)), "A")
                   for order in (links, list(reversed(links)))]
        for result in results:
            self.assertEqual(result.predecessors["D"], "B")
        self.assertEqual(results[0].predecessors, results[1].predecessors)

    def test_decimal_costs_and_stale_heap(self):
        graph = make_graph("ABC", [("A", "B", 0.1), ("B", "C", 0.2), ("A", "C", 0.9)])
        result = dijkstra(LinkStateDatabase(graph), "A")
        self.assertEqual(result.distances["C"], Fraction(3, 10))
        self.assertEqual(result.predecessors["C"], "B")

    def test_large_cost_does_not_become_unreachable(self):
        graph = make_graph("ABC", [("A", "B", 1e308), ("B", "C", 1e308)])
        self.assertNotEqual(dijkstra(LinkStateDatabase(graph), "A").distances["C"], float("inf"))

    def test_reconstruction_guard_and_unknown_source(self):
        with self.assertRaises(ValueError):
            reconstruct_path({"A": None, "B": "C", "C": "B"}, "A", "B")
        self.assertEqual(reconstruct_path({"A": None}, "A", "Z"), [])
        with self.assertRaises(ValueError):
            dijkstra(LinkStateDatabase(reference_graph()), "Z")
