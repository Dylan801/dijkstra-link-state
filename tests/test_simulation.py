import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fractions import Fraction
from dijkstra.core.graph import NetworkGraph
from dijkstra.advanced.topology_io import load_topology
from dijkstra.advanced.service import NetworkAnalyzer
from dijkstra.simulation.simulator import LinkStateSimulator
from dijkstra.simulation.lsa import LinkStateAdvertisement
from dijkstra.simulation.scenarios import load_scenario, apply_action
from dijkstra.simulation.router import ecmp_next_hops
from dijkstra.v3 import main, interactive

def chain():
    graph = NetworkGraph()
    for name in "ABCD": graph.add_router(name)
    for a, b in [("A", "B"), ("B", "C"), ("C", "D")]: graph.add_link(a, b, 1)
    return graph

class SimulationTests(unittest.TestCase):
    def test_initial_knowledge_and_one_step(self):
        simulator = LinkStateSimulator(chain())
        self.assertEqual(set(simulator.routers["A"].lsas), {"A"})
        self.assertEqual(simulator.routers["A"].local_database().get_routers(), ["A", "B"])
        self.assertEqual(simulator.routers["A"].route_to("D").cost, float("inf"))
        self.assertFalse(simulator.convergence_status()["converged"])
        simulator.step()
        self.assertIn("A", simulator.routers["B"].lsas)
        self.assertEqual(set(simulator.routers["D"].lsas), {"D"})

    def test_stable_flooding_and_static_equivalence(self):
        graph = load_topology("data/topologie_exemple.json")
        simulator = LinkStateSimulator(graph)
        self.assertLess(simulator.run_until_convergence(), 200)
        self.assertTrue(simulator.convergence_status()["converged"])
        self.assertEqual(set(simulator.routers["R6"].lsas), {"R6"})
        static = NetworkAnalyzer(graph)
        for name in ("R1", "R2", "R3", "R4", "R5"):
            for entry in static.tables[name]:
                self.assertEqual(simulator.routers[name].route_to(entry.destination).cost, entry.cost)
        kinds = {event.kind for event in simulator.journal}
        self.assertTrue({"lsa_generated", "lsa_received", "lsa_rejected", "lsdb_updated", "spf_calculated", "routing_changed", "convergence"} <= kinds)

    def test_obsolete_duplicate_and_invalid_lsa(self):
        simulator = LinkStateSimulator(chain())
        old = simulator.routers["A"].lsas["A"]
        simulator.run_until_convergence()
        simulator.change_cost("A", "B", 2)
        simulator.run_until_convergence()
        current = simulator.routers["B"].lsas["A"]
        self.assertGreater(current.sequence, old.sequence)
        simulator._enqueue("A", "B", old)
        simulator._enqueue("A", "B", current)
        simulator.run_until_convergence()
        self.assertEqual(simulator.routers["B"].lsas["A"], current)
        for args in [("A", (), 0), ("A", (("A", 1),), 1), ("A", (("B", -1),), 1), ("A", (("B", 1), ("B", 2)), 1)]:
            with self.assertRaises(ValueError):
                LinkStateAdvertisement(*args)

    def test_failure_alternative_and_cost_change(self):
        simulator = LinkStateSimulator(load_topology("data/topologie_ecmp.json"))
        simulator.run_until_convergence()
        before = simulator.snapshot_tables()
        self.assertEqual(simulator.routers["R1"].route_to("R4").next_hops, ("R2", "R3"))
        simulator.fail_link("R1", "R2")
        simulator.run_until_convergence()
        entry = simulator.routers["R1"].route_to("R4")
        self.assertEqual((entry.cost, entry.next_hops), (2, ("R3",)))
        self.assertTrue(simulator.compare_tables(before))
        simulator.restore_link("R1", "R2", 1)
        simulator.run_until_convergence()
        simulator.change_cost("R1", "R3", 0.25)
        simulator.run_until_convergence()
        self.assertEqual(simulator.routers["R1"].route_to("R4").next_hops, ("R3",))
        self.assertEqual(simulator.routers["R1"].route_to("R4").cost, Fraction(5, 4))

    def test_partition_removes_old_routes_and_reconnects(self):
        simulator = LinkStateSimulator(chain())
        simulator.run_until_convergence()
        simulator.fail_link("B", "C")
        simulator.run_until_convergence()
        self.assertEqual(simulator.routers["A"].route_to("D").cost, float("inf"))
        self.assertEqual(simulator.routers["D"].route_to("A").next_hops, ())
        self.assertNotEqual(simulator.routers["A"].lsas["C"], simulator.routers["D"].lsas["C"])
        simulator.change_cost("C", "D", 2)
        simulator.run_until_convergence()
        simulator.restore_link("B", "C", 1)
        simulator.run_until_convergence()
        self.assertEqual(simulator.routers["A"].route_to("D").cost, 4)
        self.assertEqual(simulator.routers["A"].lsas, simulator.routers["D"].lsas)

    def test_join_previously_disconnected_components(self):
        graph = chain()
        graph.remove_link("B", "C")
        simulator = LinkStateSimulator(graph)
        simulator.run_until_convergence()
        self.assertNotIn("D", simulator.routers["A"].lsas)
        simulator.restore_link("B", "C", 1)
        simulator.run_until_convergence()
        self.assertEqual(set(simulator.routers["A"].lsas), set("ABCD"))
        self.assertEqual(simulator.routers["A"].route_to("D").cost, 3)

    def test_isolation_and_recovery(self):
        simulator = LinkStateSimulator(chain())
        simulator.run_until_convergence()
        simulator.isolate_router("B")
        simulator.run_until_convergence()
        for destination in "ACD":
            self.assertEqual(simulator.routers["B"].route_to(destination).cost, float("inf"))
        simulator.restore_link("A", "B", 1)
        simulator.restore_link("B", "C", 1)
        simulator.run_until_convergence()
        self.assertEqual(simulator.routers["A"].route_to("D").cost, 3)

    def test_in_flight_lsa_on_failed_then_restored_link(self):
        simulator = LinkStateSimulator(chain())
        simulator.fail_link("A", "B")
        simulator.restore_link("A", "B", 2)
        simulator.run_until_convergence()
        self.assertTrue(any(event.kind == "delivery_dropped" for event in simulator.journal))
        self.assertEqual(simulator.routers["D"].route_to("A").cost, 4)

    def test_ecmp_decimal_and_merged_paths(self):
        graph = NetworkGraph()
        for r in "ABCDE": graph.add_router(r)
        for a, b, cost in [("A", "B", 0.1), ("A", "C", 0.2), ("B", "D", 0.2),
                           ("C", "D", 0.1), ("D", "E", 1)]: graph.add_link(a, b, cost)
        simulator = LinkStateSimulator(graph)
        simulator.run_until_convergence()
        self.assertEqual(simulator.routers["A"].route_to("E").next_hops, ("B", "C"))
        self.assertEqual(simulator.routers["A"].route_to("D").cost, Fraction(3, 10))
        # La V1 conserve un seul premier saut.
        self.assertEqual(len(NetworkAnalyzer(graph).tables["A"][-1].next_hops), 1)

    def test_invalid_mutation_and_limits(self):
        simulator = LinkStateSimulator(chain())
        before = simulator.physical.get_links()
        sequence = simulator.routers["A"].sequence
        with self.assertRaises(ValueError): simulator.change_cost("A", "B", 0)
        with self.assertRaises(ValueError): simulator.restore_link("A", "B", 1)
        self.assertEqual(simulator.physical.get_links(), before)
        self.assertEqual(simulator.routers["A"].sequence, sequence)
        with self.assertRaises(RuntimeError): simulator.run_until_convergence(max_steps=0)
        simulator.run_until_convergence()
        self.assertFalse(simulator.step())

    def test_scenarios_and_exports(self):
        for path in Path("scenarios").glob("*.json"):
            simulator, actions = load_scenario(path)
            for action in actions:
                apply_action(simulator, action)
            self.assertTrue(simulator.convergence_status()["converged"], path)
        with tempfile.TemporaryDirectory() as directory:
            simulator.export(directory)
            for name in ("events", "local_lsdb", "routing", "convergence"):
                payload = json.loads((Path(directory) / f"{name}.json").read_text(encoding="utf-8"))
                self.assertTrue(payload)
            events = json.loads((Path(directory) / "events.json").read_text(encoding="utf-8"))
            self.assertEqual([e["index"] for e in events], list(range(len(events))))
            self.assertEqual([e["step"] for e in events], sorted(e["step"] for e in events))
            bad = Path(directory) / "bad.json"
            bad.write_text('{"name":"x","topology":"none","actions":[{"operation":"step","count":true}]}')
            with self.assertRaises(ValueError): load_scenario(bad)

    def test_cli_and_interactive(self):
        for args in (["--demo"], ["--scenario", "scenarios/panne_liaison.json"],
                     ["--steps", "2", "--lsdb", "--journal"], ["--fail", "R1", "R2"],
                     ["--steps", "1", "--until-convergence"]):
            with self.subTest(args=args), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(args), 0)
        simulator = LinkStateSimulator(chain())
        with contextlib.redirect_stdout(io.StringIO()), patch("builtins.input", side_effect=["1", "2", "3", "4", "5", "B", "C", "4", "11", "9", "10", "0"]):
            simulator = interactive(simulator)
        self.assertEqual(simulator.routers["A"].route_to("D").cost, float("inf"))

    def test_single_empty_and_many_routers(self):
        for count in (0, 1, 25):
            graph = NetworkGraph()
            for i in range(count): graph.add_router(f"N{i}")
            for i in range(count - 1): graph.add_link(f"N{i}", f"N{i+1}", 1)
            simulator = LinkStateSimulator(graph)
            simulator.run_until_convergence()
            self.assertTrue(simulator.convergence_status()["converged"])
            if count > 1:
                self.assertEqual(simulator.routers["N0"].route_to(f"N{count-1}").cost, count-1)
