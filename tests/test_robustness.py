"""Vérifications indépendantes d'ECMP, de partitions et de grands graphes."""
import random
import unittest
from fractions import Fraction
from dijkstra.core.graph import NetworkGraph
from dijkstra.core.lsdb import LinkStateDatabase
from dijkstra.core.spf import dijkstra, reconstruct_path
from dijkstra.advanced.service import NetworkAnalyzer
from dijkstra.advanced.diagnostics import find_bridges, connected_components
from dijkstra.advanced.exports import json_value
from dijkstra.simulation.simulator import LinkStateSimulator

def random_graph(randomizer: random.Random, names: str) -> NetworkGraph:
    graph = NetworkGraph()
    for name in names:
        graph.add_router(name)
    for i, source in enumerate(names):
        for target in names[i+1:]:
            if randomizer.random() < 0.45:
                graph.add_link(source, target, randomizer.choice([0.1, 0.2, 0.3, 1, 2]))
    return graph

class RobustnessTests(unittest.TestCase):
    def test_ecmp_against_all_simple_paths(self):
        randomizer = random.Random(71)
        for trial in range(12):
            graph = random_graph(randomizer, "ABCDE")
            simulator = LinkStateSimulator(graph)
            simulator.run_until_convergence()
            for source in graph.get_routers():
                costs = {r: float("inf") for r in graph.get_routers()}
                hops = {r: set() for r in graph.get_routers()}
                pending = [([source], Fraction(0))]
                while pending:
                    path, cost = pending.pop()
                    node = path[-1]
                    first = path[1] if len(path) > 1 else "Local"
                    if cost < costs[node]:
                        costs[node] = cost
                        hops[node] = {first}
                    elif cost == costs[node]:
                        hops[node].add(first)
                    for neighbor, weight in graph.get_neighbors(node).items():
                        if neighbor not in path:
                            pending.append((path + [neighbor], cost + Fraction(str(weight))))
                for destination in graph.get_routers():
                    with self.subTest(trial=trial, source=source, destination=destination):
                        route = simulator.routers[source].route_to(destination)
                        self.assertEqual(route.cost, costs[destination])
                        self.assertEqual(set(route.next_hops), hops[destination])

    def test_repeated_mutations_against_current_physical_topology(self):
        randomizer = random.Random(2026)
        for trial in range(8):
            simulator = LinkStateSimulator(random_graph(randomizer, "ABCDEF"))
            for iteration in range(10):
                # Les premiers changements arrivent avant la diffusion initiale.
                a, b = randomizer.sample(list("ABCDEF"), 2)
                if b in simulator.physical.get_neighbors(a):
                    if randomizer.random() < 0.5:
                        simulator.fail_link(a, b)
                    else:
                        simulator.change_cost(a, b, randomizer.choice([0.1, 0.5, 1, 3]))
                else:
                    simulator.restore_link(a, b, randomizer.choice([0.2, 1, 2]))
                simulator.run_until_convergence()
                static = NetworkAnalyzer(simulator.physical)
                for source, result in static.results.items():
                    for destination, cost in result.distances.items():
                        with self.subTest(trial=trial, iteration=iteration, source=source, destination=destination):
                            self.assertEqual(simulator.routers[source].route_to(destination).cost, cost)

    def test_deterministic_log_except_measured_duration(self):
        randomizer = random.Random(99)
        graph = random_graph(randomizer, "ABCDE")
        records = []
        for _ in range(2):
            simulator = LinkStateSimulator(graph)
            simulator.run_until_convergence()
            records.append([{**event.to_dict(), "details": {key: value for key, value in event.details.items() if key != "seconds"}}
                            for event in simulator.journal])
        self.assertEqual(records[0], records[1])

    def test_bridge_detection_against_edge_removal(self):
        randomizer = random.Random(7)
        for _ in range(15):
            graph = random_graph(randomizer, "ABCDEF")
            initial = len(connected_components(graph))
            expected = []
            for source, target, _ in graph.get_links():
                candidate = graph.copy()
                candidate.remove_link(source, target)
                if len(connected_components(candidate)) > initial:
                    expected.append((source, target))
            self.assertEqual(find_bridges(graph), expected)

    def test_no_recursion_limit_for_spf_paths_and_bridges(self):
        graph = NetworkGraph()
        for i in range(1200): graph.add_router(f"N{i:04d}")
        for i in range(1199): graph.add_link(f"N{i:04d}", f"N{i+1:04d}", 1)
        result = dijkstra(LinkStateDatabase(graph), "N0000")
        self.assertEqual(result.distances["N1199"], 1199)
        self.assertEqual(len(reconstruct_path(result.predecessors, "N0000", "N1199")), 1200)
        self.assertEqual(len(find_bridges(graph)), 1199)

    def test_invalid_endpoint_and_exact_large_decimal_export(self):
        graph = NetworkGraph()
        graph.add_router("A")
        for target in ([], {}, None, " B", 3):
            with self.subTest(target=target), self.assertRaises(ValueError):
                graph.add_link("A", target, 1)
        value = Fraction(10**400 + 1, 10)
        encoded = json_value(value)
        self.assertIsInstance(encoded, str)
        self.assertEqual(Fraction(encoded), value)
