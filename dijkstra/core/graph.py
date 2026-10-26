"""Topologie non orientée, à coûts strictement positifs."""
import math
from typing import TypeAlias

Cost: TypeAlias = int | float

def validate_router(router: str) -> None:
    if not isinstance(router, str) or not router or router.strip() != router:
        raise ValueError("Identifiant de routeur vide ou mal formé.")
    if any(not (char.isalnum() or char in "_.-") for char in router):
        raise ValueError("Identifiant : lettres, chiffres, _, . et - uniquement.")

def validate_cost(cost: Cost) -> None:
    if isinstance(cost, bool) or not isinstance(cost, (int, float)):
        raise ValueError("Le coût doit être un nombre positif.")
    if cost <= 0 or (isinstance(cost, float) and not math.isfinite(cost)):
        raise ValueError("Le coût doit être strictement positif et fini.")

class NetworkGraph:
    def __init__(self) -> None:
        self._adjacency: dict[str, dict[str, Cost]] = {}

    def add_router(self, router: str) -> None:
        validate_router(router)
        if router in self._adjacency:
            raise ValueError(f"Routeur déjà présent : {router}")
        self._adjacency[router] = {}

    def _require(self, router: str) -> None:
        validate_router(router)
        if router not in self._adjacency:
            raise ValueError(f"Routeur inconnu : {router}")

    def add_link(self, source: str, target: str, cost: Cost) -> None:
        self._require(source)
        self._require(target)
        validate_cost(cost)
        if source == target:
            raise ValueError("Les boucles locales sont interdites.")
        if target in self._adjacency[source]:
            raise ValueError("Liaison déjà présente ; utiliser update_link().")
        self._adjacency[source][target] = cost
        self._adjacency[target][source] = cost

    def remove_router(self, router: str) -> None:
        self._require(router)
        for neighbor in list(self._adjacency[router]):
            del self._adjacency[neighbor][router]
        del self._adjacency[router]

    def remove_link(self, source: str, target: str) -> None:
        self._require(source)
        self._require(target)
        if target not in self._adjacency[source]:
            raise ValueError("Liaison absente.")
        del self._adjacency[source][target]
        del self._adjacency[target][source]

    def update_link(self, source: str, target: str, cost: Cost) -> None:
        self._require(source)
        self._require(target)
        validate_cost(cost)
        if target not in self._adjacency[source]:
            raise ValueError("Liaison absente.")
        self._adjacency[source][target] = cost
        self._adjacency[target][source] = cost

    def get_neighbors(self, router: str) -> dict[str, Cost]:
        self._require(router)
        return dict(sorted(self._adjacency[router].items()))

    def get_routers(self) -> list[str]:
        return sorted(self._adjacency)

    def get_links(self) -> list[tuple[str, str, Cost]]:
        return [(a, b, c) for a in self.get_routers()
                for b, c in self.get_neighbors(a).items() if a < b]

    def validate(self) -> None:
        for router, neighbors in self._adjacency.items():
            validate_router(router)
            for neighbor, cost in neighbors.items():
                validate_cost(cost)
                if neighbor == router or neighbor not in self._adjacency:
                    raise ValueError("Voisin invalide dans la topologie.")
                if self._adjacency[neighbor].get(router) != cost:
                    raise ValueError("Liaison non symétrique.")

    def copy(self) -> "NetworkGraph":
        graph = NetworkGraph()
        for router in self.get_routers():
            graph.add_router(router)
        for source, target, cost in self.get_links():
            graph.add_link(source, target, cost)
        return graph
