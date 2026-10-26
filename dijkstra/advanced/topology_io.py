"""Lecture stricte des topologies JSON."""
import json
from pathlib import Path
from ..core.graph import NetworkGraph

def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Clé JSON dupliquée : {key}")
        result[key] = value
    return result

def read_json(path: str | Path) -> object:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                          object_pairs_hook=_unique_object,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"Constante JSON invalide : {value}")))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Lecture JSON impossible : {path} : {error}") from error

def graph_from_dict(data: object) -> NetworkGraph:
    if not isinstance(data, dict) or set(data) != {"routers", "links"}:
        raise ValueError("La topologie exige uniquement les clés routers et links.")
    if not isinstance(data["routers"], list) or not isinstance(data["links"], list):
        raise ValueError("routers et links doivent être des listes.")
    graph = NetworkGraph()
    for router in data["routers"]:
        graph.add_router(router)
    for link in data["links"]:
        if not isinstance(link, dict) or set(link) != {"source", "target", "cost"}:
            raise ValueError("Chaque liaison exige source, target et cost.")
        graph.add_link(link["source"], link["target"], link["cost"])
    graph.validate()
    return graph

def load_topology(path: str | Path) -> NetworkGraph:
    return graph_from_dict(read_json(path))

def topology_dict(graph: NetworkGraph) -> dict:
    return {"routers": graph.get_routers(), "links": [
        {"source": source, "target": target, "cost": cost}
        for source, target, cost in graph.get_links()]}
