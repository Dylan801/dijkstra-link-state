import unittest
from dijkstra.core.lsdb import LinkStateDatabase
from dijkstra.core.spf import dijkstra
from dijkstra.core.routing import build_routing_table
from dijkstra.examples import reference_graph

class RoutingTests(unittest.TestCase):
    def test_next_hops_not_predecessors(self):
        result = dijkstra(LinkStateDatabase(reference_graph()), "R1")
        table = {entry.destination: entry for entry in build_routing_table(result)}
        self.assertEqual(table["R1"].next_hop, "Local")
        for destination in ("R2", "R3", "R4", "R5"):
            self.assertEqual(table[destination].next_hop, "R2")
        self.assertEqual(result.predecessors["R5"], "R4")
        self.assertIsNone(table["R6"].next_hop)
        self.assertEqual(table["R6"].path, ())
