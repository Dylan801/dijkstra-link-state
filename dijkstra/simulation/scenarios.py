"""Scénarios validés avant exécution, topologie relative au fichier scénario."""
from pathlib import Path
from ..advanced.topology_io import read_json, load_topology
from ..core.graph import validate_cost, validate_router
from .simulator import LinkStateSimulator

def load_scenario(path: str | Path) -> tuple[LinkStateSimulator, list[dict]]:
    path = Path(path)
    data = read_json(path)
    if not isinstance(data, dict) or set(data) != {"name", "topology", "actions"}:
        raise ValueError("Scénario : clés name, topology, actions exigées.")
    if not isinstance(data["name"], str) or not isinstance(data["topology"], str) or not isinstance(data["actions"], list):
        raise ValueError("Types invalides dans le scénario.")
    schemas = {"run": {"operation"}, "step": {"operation", "count"},
               "fail": {"operation", "source", "target"},
               "restore": {"operation", "source", "target", "cost"},
               "cost": {"operation", "source", "target", "cost"},
               "isolate": {"operation", "router"}}
    for action in data["actions"]:
        if not isinstance(action, dict) or not isinstance(action.get("operation"), str):
            raise ValueError("Action de scénario incorrecte.")
        operation = action["operation"]
        if operation not in schemas or set(action) != schemas[operation]:
            raise ValueError(f"Schéma d'action incorrect : {operation}")
        for key in ("source", "target", "router"):
            if key in action:
                validate_router(action[key])
        if "cost" in action:
            validate_cost(action["cost"])
        if "count" in action and (type(action["count"]) is not int or action["count"] < 0):
            raise ValueError("count exige un entier positif ou nul.")
    return LinkStateSimulator(load_topology(path.parent / data["topology"])), data["actions"]

def apply_action(simulator: LinkStateSimulator, action: dict) -> None:
    operation = action["operation"]
    if operation == "run":
        simulator.run_until_convergence()
    elif operation == "step":
        for _ in range(action["count"]):
            if not simulator.step():
                break
    elif operation == "fail":
        simulator.fail_link(action["source"], action["target"])
    elif operation == "restore":
        simulator.restore_link(action["source"], action["target"], action["cost"])
    elif operation == "cost":
        simulator.change_cost(action["source"], action["target"], action["cost"])
    elif operation == "isolate":
        simulator.isolate_router(action["router"])
    else:
        raise ValueError("Action inconnue.")
