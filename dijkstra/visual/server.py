"""Adaptateur HTTP local : l'interface réutilise intégralement le moteur V3."""
from __future__ import annotations
import json
from pathlib import Path
from threading import RLock
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from ..advanced.exports import json_value, table_dict
from ..advanced.topology_io import load_topology
from ..core.graph import NetworkGraph
from ..display import format_cost
from ..simulation.simulator import LinkStateSimulator

EVENT_NAMES = {
    "link_appeared": "Liaison établie", "link_removed": "Liaison coupée",
    "link_cost_changed": "Coût modifié", "lsa_generated": "LSA générée",
    "lsa_received": "LSA reçue", "lsa_rejected": "LSA déjà connue ou obsolète",
    "lsdb_updated": "LSDB actualisée", "spf_calculated": "Calcul SPF",
    "routing_changed": "Table de routage modifiée", "convergence": "Convergence vérifiée",
    "delivery_dropped": "Livraison interrompue", "adjacency_synchronized": "Échange des bases",
}

class GraphController:
    """État d'une session graphique ; les interfaces sont des étiquettes fictives."""
    def __init__(self, graph: NetworkGraph, topologies: dict[str, Path] | None = None) -> None:
        self.lock = RLock()
        self.initial = graph.copy()
        self.topologies = dict(topologies or {})
        self.topology_name = "personnalisee"
        self._reset(graph)

    def _reset(self, graph: NetworkGraph) -> None:
        self.simulator = LinkStateSimulator(graph)
        self.links: dict[tuple[str, str], dict] = {}
        self.port_counts = {router: 0 for router in graph.get_routers()}
        for source, target, cost in graph.get_links():
            self._register_link(source, target, cost)
        self.baseline = self.simulator.snapshot_tables()
        self.last_packet: dict | None = None

    def _register_link(self, source: str, target: str, cost: int | float) -> None:
        key = tuple(sorted((source, target)))
        if key not in self.links:
            interfaces = {}
            for router in key:
                interfaces[router] = f"Gi0/{self.port_counts[router]}"
                self.port_counts[router] += 1
            self.links[key] = {"source": key[0], "target": key[1], "interfaces": interfaces, "cost": cost}
        else:
            self.links[key]["cost"] = cost

    def perform(self, payload: object) -> None:
        if not isinstance(payload, dict) or not isinstance(payload.get("action"), str):
            raise ValueError("Action JSON incorrecte.")
        with self.lock:
            action = payload["action"]
            simulator = self.simulator
            if action == "reset":
                name = payload.get("topology")
                if name is not None:
                    if not isinstance(name, str) or name not in self.topologies:
                        raise ValueError("Topologie inconnue.")
                    graph = load_topology(self.topologies[name])
                    self.topology_name = name
                else:
                    graph = self.initial
                    self.topology_name = "personnalisee"
                self._reset(graph)
            elif action == "step":
                delivery = simulator.pending[0] if simulator.pending else None
                if simulator.step() and delivery:
                    self.last_packet = {"source": delivery.sender, "target": delivery.receiver,
                                        "origin": delivery.advertisement.origin,
                                        "sequence": delivery.advertisement.sequence}
            elif action == "converge":
                simulator.run_until_convergence()
                self.last_packet = None
            elif action in {"fail", "restore", "cost"}:
                source, target = payload.get("source"), payload.get("target")
                if not isinstance(source, str) or not isinstance(target, str):
                    raise ValueError("Les deux extrémités doivent être des identifiants de routeur.")
                before = simulator.snapshot_tables()
                if action == "fail":
                    simulator.fail_link(source, target)
                elif action == "restore":
                    cost = payload.get("cost")
                    simulator.restore_link(source, target, cost)
                    self._register_link(source, target, cost)
                else:
                    cost = payload.get("cost")
                    simulator.change_cost(source, target, cost)
                    self._register_link(source, target, cost)
                self.baseline = before
                self.last_packet = None
            elif action == "isolate":
                router = payload.get("router")
                if not isinstance(router, str):
                    raise ValueError("Routeur invalide.")
                before = simulator.snapshot_tables()
                simulator.isolate_router(router)
                self.baseline = before
                self.last_packet = None
            else:
                raise ValueError("Action inconnue.")

    def snapshot(self, source: str | None = None, destination: str | None = None) -> dict:
        with self.lock:
            simulator = self.simulator
            names = list(simulator.routers)
            source = source or (names[0] if names else None)
            destination = destination or ("R5" if "R5" in names else names[-1] if names else source)
            if source is not None and source not in simulator.routers:
                raise ValueError("Routeur source inconnu.")
            if destination is not None and destination not in simulator.routers:
                raise ValueError("Routeur destination inconnu.")
            links = []
            interfaces = []
            for key, known in self.links.items():
                a, b = key
                neighbors = simulator.physical.get_neighbors(a)
                active = b in neighbors
                cost = neighbors[b] if active else known["cost"]
                link = {**known, "id": "--".join(key), "active": active, "cost": cost,
                        "source_interface": known["interfaces"][a],
                        "target_interface": known["interfaces"][b]}
                links.append(link)
                if source in key:
                    neighbor = b if source == a else a
                    interfaces.append({"name": known["interfaces"][source], "neighbor": neighbor,
                                       "remote_interface": known["interfaces"][neighbor],
                                       "active": active, "cost": cost})
            node = simulator.routers.get(source)
            route = node.route_to(destination) if node and destination else None
            table = []
            previous = {entry["destination"]: entry for entry in self.baseline.get(source, [])}
            if node:
                for entry, raw in zip(node.table, table_dict(node.table)):
                    table.append({**raw, "cost_label": format_cost(entry.cost),
                                  "changed": previous.get(entry.destination) != raw})
            events = []
            for event in simulator.journal[-70:]:
                details = event.details
                info = ""
                if "origin" in details:
                    info = f"{details['origin']} · séq. {details.get('sequence', '-')}"
                elif "source" in details:
                    info = f"{details['source']} ↔ {details['target']}"
                elif "advertisement" in details:
                    lsa = details["advertisement"]
                    info = f"{lsa['origin']} · séq. {lsa['sequence']}"
                events.append({"index": event.index, "step": event.step, "kind": event.kind,
                               "label": EVENT_NAMES.get(event.kind, event.kind),
                               "router": event.router, "info": info})
            status = simulator.convergence_status()
            result = node.result if node else None
            return json_value({
                "routers": [{"id": name, "neighbors": len(simulator.physical.get_neighbors(name)),
                             "lsa_count": len(router.lsas)} for name, router in simulator.routers.items()],
                "links": links, "source": source, "destination": destination,
                "interfaces": sorted(interfaces, key=lambda entry: int(entry["name"].split("/")[-1])),
                "table": table, "tree": result.tree_edges if result else [],
                "route": {"path": list(route.path), "cost": route.cost,
                          "cost_label": format_cost(route.cost), "next_hops": route.next_hops,
                          "known": destination in result.distances} if route and result else None,
                "lsdb": [lsa.to_dict() for _, lsa in sorted(node.lsas.items())] if node else [],
                "events": events, "event_count": len(simulator.journal),
                "step": simulator.step_number, "status": status, "last_packet": self.last_packet,
                "topology": self.topology_name, "topologies": list(self.topologies),
            })

def make_server(controller: GraphController, host: str, port: int) -> ThreadingHTTPServer:
    static = Path(__file__).with_name("static")

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: bytes, content_type: str = "application/json; charset=utf-8") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, payload: object) -> None:
            self._send(status, json.dumps(payload, ensure_ascii=False, allow_nan=False).encode())

        def do_GET(self) -> None:
            path = urlsplit(self.path)
            try:
                if path.path == "/api/state":
                    params = parse_qs(path.query)
                    self._json(200, controller.snapshot(params.get("source", [None])[0],
                                                        params.get("destination", [None])[0]))
                elif path.path in {"/", "/app.js", "/style.css"}:
                    name = "index.html" if path.path == "/" else path.path[1:]
                    body = (static / name).read_bytes()
                    content_type = {"index.html": "text/html", "app.js": "text/javascript", "style.css": "text/css"}[name]
                    self._send(200, body, content_type + "; charset=utf-8")
                elif path.path == "/api/export":
                    self._json(200, controller.snapshot())
                else:
                    self._json(404, {"error": "Ressource inconnue."})
            except (ValueError, OSError) as error:
                self._json(400, {"error": str(error)})

        def do_POST(self) -> None:
            if self.path != "/api/action":
                self._json(404, {"error": "Action inconnue."})
                return
            # Les mutations de la session locale proviennent de sa propre page.
            origin = self.headers.get("Origin")
            if origin and urlsplit(origin).netloc != self.headers.get("Host"):
                self._json(403, {"error": "Origine non autorisée."})
                return
            if self.headers.get_content_type() != "application/json":
                self._json(415, {"error": "Un corps application/json est exigé."})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 8192:
                    raise ValueError("Taille de requête invalide.")
                payload = json.loads(self.rfile.read(length))
                controller.perform(payload)
                self._json(200, {"ok": True})
            except (ValueError, TypeError, RuntimeError, UnicodeError) as error:
                self._json(400, {"error": str(error)})

        def log_message(self, format: str, *args: object) -> None:
            return

    return ThreadingHTTPServer((host, port), Handler)

def serve(topology: str, host: str = "127.0.0.1", port: int = 8080) -> None:
    path = Path(topology)
    available = {file.stem: file for file in sorted(path.parent.glob("*.json"))}
    controller = GraphController(load_topology(path), available)
    controller.topology_name = path.stem
    server = make_server(controller, host, port)
    print(f"V3 graphique : http://{host}:{server.server_port} — Ctrl+C pour arrêter.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
