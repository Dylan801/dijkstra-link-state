"""Oracle indépendant : énumération exhaustive de chemins simples, petits graphes."""
import random
import unittest
from fractions import Fraction
from dijkstra.core.graph import NetworkGraph
from dijkstra.core.lsdb import LinkStateDatabase
from dijkstra.core.spf import dijkstra, reconstruct_path

class ExhaustiveTests(unittest.TestCase):
    def test_random_small_graphs_against_simple_path_enumeration(self):
        randomizer = random.Random(42)
        for trial in range(25):
            graph = NetworkGraph()
            for r in "ABCDE": graph.add_router(r)
            for i, a in enumerate("ABCDE"):
                for b in "ABCDE"[i+1:]:
                    if randomizer.random() < 0.45:
                        graph.add_link(a, b, randomizer.choice([0.1, 0.2, 1, 2, 4]))
            for source in graph.get_routers():
                best = {r: float("inf") for r in graph.get_routers()}
                pending = [(source, Fraction(0), {source})]
                while pending:
                    node, cost, visited = pending.pop()
                    best[node] = min(best[node], cost)
                    for neighbor, weight in graph.get_neighbors(node).items():
                        if neighbor not in visited:
                            pending.append((neighbor, cost + Fraction(str(weight)), visited | {neighbor}))
                result = dijkstra(LinkStateDatabase(graph), source)
                with self.subTest(trial=trial, source=source):
                    self.assertEqual(result.distances, best)
                    for destination in graph.get_routers():
                        path = reconstruct_path(result.predecessors, source, destination)
                        if path:
                            cost = sum((Fraction(str(graph.get_neighbors(a)[b])) for a, b in zip(path, path[1:])), Fraction(0))
                            self.assertEqual(cost, best[destination])
                            self.assertEqual(len(path), len(set(path)))
