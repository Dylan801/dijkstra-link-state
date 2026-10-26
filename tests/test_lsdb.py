import unittest
from dijkstra.examples import reference_graph
from dijkstra.core.lsdb import build_lsdbs
from dijkstra.core.spf import run_all, dijkstra

class LSDBTests(unittest.TestCase):
    def test_independent_complete_copies(self):
        graph = reference_graph()
        databases = build_lsdbs(graph)
        original = databases["R1"].to_dict()
        self.assertEqual(len(databases), 6)
        for database in databases.values():
            self.assertEqual(database.to_dict(), original)
        graph.update_link("R1", "R2", 99)
        databases["R2"]._graph.update_link("R1", "R2", 88)
        self.assertEqual(databases["R1"].to_dict(), original)
        self.assertEqual(dijkstra(databases["R1"], "R1").distances["R5"], 5)

    def test_all_sources(self):
        results = run_all(build_lsdbs(reference_graph()))
        self.assertEqual(set(results), {f"R{i}" for i in range(1, 7)})
        for source, result in results.items():
            self.assertEqual(result.source, source)
            self.assertEqual(result.distances[source], 0)
