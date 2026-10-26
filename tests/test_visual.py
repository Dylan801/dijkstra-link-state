"""Tests d'intégration de la V3 graphique et de son adaptation HTTP."""
import contextlib
import http.client
import io
import json
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from dijkstra.advanced.topology_io import load_topology
from dijkstra.examples import reference_graph
from dijkstra.visual.server import GraphController, make_server
from dijkstra.v3 import main

class VisualControllerTests(unittest.TestCase):
    def setUp(self):
        self.controller=GraphController(reference_graph(), {
            "ecmp": Path("data/topologie_ecmp.json"),
            "partition": Path("data/topologie_partition.json")})

    def test_initial_local_knowledge_and_physical_diagram(self):
        state=self.controller.snapshot("R1","R5")
        self.assertEqual(len(state["routers"]),6)
        self.assertEqual(len(state["links"]),7)
        self.assertEqual([lsa["origin"] for lsa in state["lsdb"]],["R1"])
        self.assertFalse(state["status"]["converged"])
        self.assertIsNone(state["route"]["cost"])
        self.assertFalse(state["route"]["known"])

    def test_converged_route_interfaces_and_tree(self):
        self.controller.perform({"action":"converge"})
        state=self.controller.snapshot("R1","R5")
        self.assertEqual(state["route"]["path"],["R1","R2","R4","R5"])
        self.assertEqual(state["route"]["cost_label"],"5")
        self.assertEqual(state["route"]["next_hops"],["R2"])
        self.assertIn(["R4","R5"],state["tree"])
        self.assertEqual([(i["name"],i["neighbor"]) for i in state["interfaces"]],
                         [("Gi0/0","R2"),("Gi0/1","R3")])
        self.assertEqual(len(state["lsdb"]),5)
        self.assertTrue(state["status"]["converged"])

    def test_cut_restoration_retains_interface_names(self):
        self.controller.perform({"action":"converge"})
        before=self.controller.snapshot("R2","R5")
        original=next(link for link in before["links"] if link["id"]=="R2--R4")
        self.controller.perform({"action":"fail","source":"R2","target":"R4"})
        self.controller.perform({"action":"converge"})
        state=self.controller.snapshot("R1","R5")
        down=next(link for link in state["links"] if link["id"]=="R2--R4")
        self.assertFalse(down["active"])
        self.assertEqual(down["interfaces"],original["interfaces"])
        self.assertEqual(state["route"]["cost_label"],"7")
        self.controller.perform({"action":"restore","source":"R4","target":"R2","cost":2})
        self.controller.perform({"action":"converge"})
        restored=next(link for link in self.controller.snapshot()["links"] if link["id"]=="R2--R4")
        self.assertTrue(restored["active"])
        self.assertEqual(restored["interfaces"],original["interfaces"])

    def test_new_link_uses_unique_local_ports(self):
        self.controller.perform({"action":"restore","source":"R6","target":"R1","cost":3})
        state=self.controller.snapshot("R1","R6")
        ports=[interface["name"] for interface in state["interfaces"]]
        self.assertEqual(len(ports),len(set(ports)))
        self.assertEqual(ports,["Gi0/0","Gi0/1","Gi0/2"])
        remote=self.controller.snapshot("R6","R1")["interfaces"]
        self.assertEqual(remote[0]["name"],"Gi0/0")

    def test_partition_and_ecmp_are_preserved(self):
        self.controller.perform({"action":"reset","topology":"partition"})
        self.controller.perform({"action":"converge"})
        self.controller.perform({"action":"fail","source":"B","target":"C"})
        self.controller.perform({"action":"converge"})
        state=self.controller.snapshot("A","D")
        self.assertIsNone(state["route"]["cost"])
        self.assertEqual(state["route"]["path"],[])
        self.assertTrue(state["status"]["converged"])
        self.controller.perform({"action":"reset","topology":"ecmp"})
        self.controller.perform({"action":"converge"})
        self.assertEqual(self.controller.snapshot("R1","R4")["route"]["next_hops"],["R2","R3"])

    def test_invalid_change_is_atomic_and_snapshot_validated(self):
        before=self.controller.snapshot()
        for payload in ({"action":"cost","source":"R1","target":"R2","cost":0},
                        {"action":"cost","source":"R1","target":"R2","cost":True},
                        {"action":"reset","topology":"../../etc/passwd"},
                        {"action":"unknown"},[],None):
            with self.subTest(payload=payload),self.assertRaises(ValueError):
                self.controller.perform(payload)
            self.assertEqual(self.controller.snapshot(),before)
        with self.assertRaises(ValueError):self.controller.snapshot("inconnu","R1")
        with self.assertRaises(ValueError):self.controller.snapshot("R1","inconnu")

    def test_step_tracks_lsa_and_state_is_json_serializable(self):
        self.controller.perform({"action":"step"})
        state=self.controller.snapshot()
        self.assertEqual(state["step"],1)
        self.assertEqual(state["last_packet"]["origin"],"R1")
        json.dumps(state,allow_nan=False)
        self.assertTrue(state["events"])

class VisualHTTPTests(unittest.TestCase):
    def setUp(self):
        self.controller=GraphController(reference_graph())
        self.server=make_server(self.controller,"127.0.0.1",0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self,method,path,body=None,headers=None):
        connection=http.client.HTTPConnection("127.0.0.1",self.server.server_port,timeout=5)
        connection.request(method,path,body=body,headers=headers or {})
        response=connection.getresponse()
        result=(response.status,dict(response.headers),response.read())
        connection.close()
        return result

    def test_static_assets_and_no_directory_traversal(self):
        for path,kind in [("/","text/html"),("/app.js","text/javascript"),("/style.css","text/css")]:
            status,headers,body=self.request("GET",path)
            self.assertEqual(status,200)
            self.assertIn(kind,headers["Content-Type"])
            self.assertGreater(len(body),100)
        self.assertEqual(self.request("GET","/../../pyproject.toml")[0],404)

    def test_http_drives_same_simulator(self):
        status,_,body=self.request("POST","/api/action",json.dumps({"action":"converge"}),{"Content-Type":"application/json"})
        self.assertEqual(status,200)
        status,_,body=self.request("GET","/api/state?source=R1&destination=R5")
        state=json.loads(body)
        self.assertEqual(status,200)
        self.assertEqual(state["route"]["cost"],5)
        self.assertEqual(self.request("GET","/api/state?source=unknown")[0],400)

    def test_http_rejects_invalid_or_cross_origin_mutations(self):
        body=json.dumps({"action":"converge"})
        self.assertEqual(self.request("POST","/api/action",body,{"Content-Type":"text/plain"})[0],415)
        self.assertEqual(self.request("POST","/api/action",body,{"Content-Type":"application/json","Origin":"https://other.example"})[0],403)
        self.assertEqual(self.request("POST","/api/action","{",{"Content-Type":"application/json"})[0],400)
        self.assertEqual(self.request("POST","/api/action","[]",{"Content-Type":"application/json"})[0],400)
        self.assertFalse(self.controller.snapshot()["status"]["converged"])

    def test_web_cli_and_incompatible_flags(self):
        with patch("dijkstra.visual.server.serve") as serve:
            self.assertEqual(main(["--web","--port","8082"]),0)
            serve.assert_called_once_with("data/topologie_exemple.json","127.0.0.1",8082)
        for args in (["--web","--demo"],["--web","--port","0"],["--web","--interactive"]):
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as error:
                main(args)
            self.assertEqual(error.exception.code,2)
