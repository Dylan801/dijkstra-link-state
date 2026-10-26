import unittest
from dijkstra.core.graph import NetworkGraph

class GraphTests(unittest.TestCase):
    def setUp(self):
        self.graph = NetworkGraph()
        for router in ("A", "B", "C"):
            self.graph.add_router(router)

    def test_symmetric_and_copy(self):
        self.graph.add_link("A", "B", 0.5)
        self.assertEqual(self.graph.get_neighbors("B"), {"A": 0.5})
        neighbors = self.graph.get_neighbors("A")
        neighbors.clear()
        self.assertEqual(len(self.graph.get_links()), 1)
        copy = self.graph.copy()
        copy.remove_router("B")
        self.assertIn("B", self.graph.get_routers())

    def test_invalid_costs(self):
        for cost in (0, -1, float("inf"), -float("inf"), float("nan"), True, "2", None):
            with self.subTest(cost=cost), self.assertRaises(ValueError):
                self.graph.add_link("A", "B", cost)
        self.assertEqual(self.graph.get_links(), [])

    def test_invalid_ids_and_links(self):
        for router in ("", " A", "A B", "A\n", None, 42):
            with self.subTest(router=router), self.assertRaises(ValueError):
                self.graph.add_router(router)
        for source, target in (("A", "A"), ("A", "Z")):
            with self.assertRaises(ValueError):
                self.graph.add_link(source, target, 1)
        self.graph.add_link("A", "B", 1)
        with self.assertRaises(ValueError):
            self.graph.add_link("B", "A", 2)

    def test_operations(self):
        self.graph.add_link("A", "B", 1)
        self.graph.update_link("A", "B", 3)
        self.assertEqual(self.graph.get_neighbors("B")["A"], 3)
        self.graph.remove_link("A", "B")
        self.assertEqual(self.graph.get_links(), [])
        self.graph.add_link("A", "C", 1)
        self.graph.remove_router("C")
        self.graph.validate()
        self.assertEqual(self.graph.get_neighbors("A"), {})

    def test_validate_detects_corruption(self):
        self.graph._adjacency["A"]["B"] = 1
        with self.assertRaises(ValueError):
            self.graph.validate()
