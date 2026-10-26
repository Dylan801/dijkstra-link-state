import contextlib
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from dijkstra.advanced.topology_io import graph_from_dict, load_topology, read_json
from dijkstra.advanced.service import NetworkAnalyzer
from dijkstra.advanced.exports import export_analysis, write_json
from dijkstra.advanced.diagnostics import diagnose, connected_components, find_bridges
from dijkstra.advanced.visualization import write_svg
from dijkstra.examples import reference_graph
from dijkstra.v2 import main, interactive
from dijkstra.core.graph import NetworkGraph

class V2Tests(unittest.TestCase):
    def test_load_all_examples(self):
        for path in Path("data").glob("*.json"):
            with self.subTest(path=path):
                load_topology(path).validate()
        self.assertEqual(len(load_topology("data/topologie_exemple.json").get_routers()), 6)

    def test_strict_schema(self):
        bad = [None, {}, {"routers": "AB", "links": []},
               {"routers": ["A", "A"], "links": []},
               {"routers": ["A"], "links": [{"source": "A", "target": "B", "cost": 1}]},
               {"routers": ["A"], "links": [{"source": "A"}]},
               {"routers": [], "links": [], "extra": 1}]
        for data in bad:
            with self.subTest(data=data), self.assertRaises(ValueError):
                graph_from_dict(data)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            for content in ('{"routers":[],"routers":[],"links":[]}', '{', '{"routers":[],"links":[],"x":NaN}'):
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    read_json(path)
        with self.assertRaises(ValueError):
            load_topology("fichier_absent_123.json")

    def test_modifications_recalculate_and_are_atomic(self):
        analyzer = NetworkAnalyzer(reference_graph())
        analyzer.modify("update_link", "R1", "R3", 1)
        self.assertEqual(analyzer.results["R1"].distances["R3"], 1)
        self.assertEqual(analyzer.lsdbs["R5"].get_neighbors("R1")["R3"], 1)
        before = analyzer.graph.get_links()
        with self.assertRaises(ValueError):
            analyzer.modify("update_link", "R1", "R3", -1)
        self.assertEqual(analyzer.graph.get_links(), before)
        analyzer.modify("add_router", "R7")
        analyzer.modify("add_link", "R6", "R7", 2)
        self.assertEqual(analyzer.results["R6"].distances["R7"], 2)
        analyzer.modify("remove_link", "R6", "R7")
        self.assertEqual(analyzer.results["R6"].distances["R7"], float("inf"))
        analyzer.modify("remove_router", "R7")
        self.assertNotIn("R7", analyzer.results)

    def test_diagnostics_and_bridges(self):
        result = diagnose(reference_graph(), "R1")
        self.assertEqual(result["unreachable"], ["R6"])
        self.assertEqual(result["components"], [["R1", "R2", "R3", "R4", "R5"], ["R6"]])
        self.assertEqual(result["bridges"], [])
        graph = NetworkGraph()
        for r in "ABCD": graph.add_router(r)
        for a, b in [("A", "B"), ("B", "C"), ("C", "A"), ("C", "D")]: graph.add_link(a, b, 1)
        self.assertEqual(find_bridges(graph), [("C", "D")])
        self.assertEqual(connected_components(NetworkGraph()), [])

    def test_exports_strict_json_csv_svg(self):
        analyzer = NetworkAnalyzer(reference_graph())
        with tempfile.TemporaryDirectory() as directory:
            paths = export_analysis(analyzer, directory)
            self.assertEqual(len(paths), 5)
            for path in paths[:4]:
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertIsInstance(data, dict)
                self.assertNotIn("Infinity", path.read_text(encoding="utf-8"))
            distances = json.loads((Path(directory) / "distances.json").read_text())
            self.assertIsNone(distances["R1"]["R6"])
            self.assertEqual(distances["R1"]["R5"], 5)
            with paths[-1].open(encoding="utf-8-sig", newline="") as file:
                rows = list(csv.reader(file))
            self.assertEqual(len(rows), 37)
            self.assertIn(["R1", "R5", "R2", "5", "R1 -> R2 -> R4 -> R5"], rows)
            svg = Path(directory) / "topology.svg"
            write_svg(analyzer.graph, svg, analyzer.results["R1"], "R5")
            import xml.etree.ElementTree as ET
            self.assertEqual(ET.parse(svg).getroot().tag, "{http://www.w3.org/2000/svg}svg")
            # Un fichier ne peut pas servir de dossier ; l'erreur est expliquée.
            with self.assertRaises(ValueError):
                write_json(paths[0] / "child.json", {})

    def test_cli_actions_and_menu(self):
        for command in ("all", "routers", "lsdb", "spf", "table", "diagnose", "topology", "path"):
            args = ["--command", command, "--source", "R1", "--destination", "R5"]
            with self.subTest(command=command), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(args), 0)
        with contextlib.redirect_stdout(io.StringIO()), patch("builtins.input", side_effect=["1", "8", "update_link", "R1 R3 1", "6", "R1", "0"]):
            analyzer = NetworkAnalyzer(reference_graph())
            interactive(analyzer)
            self.assertEqual(analyzer.results["R1"].distances["R3"], 1)
        for args in (["--command", "path"], ["--source", "inconnu"], ["--destination", "inconnu"]):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
                main(args)
            self.assertEqual(result.exception.code, 2)

    def test_stats(self):
        stats = NetworkAnalyzer(reference_graph()).statistics("R1", "R5")
        self.assertEqual((stats["routers"], stats["links"], stats["unreachable"]), (6, 7, 1))
        self.assertEqual((stats["minimal_cost"], stats["routers_on_path"], stats["hops"]), (5, 4, 3))
        self.assertGreaterEqual(stats["spf_seconds"], 0)
