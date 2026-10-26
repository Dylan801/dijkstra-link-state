"""Dijkstra explicite avec tas binaire ; aucun calcul de chemin délégué."""
import heapq
from fractions import Fraction
from time import perf_counter
from .lsdb import LinkStateDatabase
from .models import SPFResult, Distance

def dijkstra(lsdb: LinkStateDatabase, source: str) -> SPFResult:
    start = perf_counter()
    routers = lsdb.get_routers()
    if source not in routers:
        raise ValueError(f"Source absente de la LSDB : {source}")
    distances: dict[str, Distance] = {r: float("inf") for r in routers}
    predecessors: dict[str, str | None] = {r: None for r in routers}
    distances[source] = Fraction(0)
    queue = [(Fraction(0), source)]
    while queue:
        distance, router = heapq.heappop(queue)
        if distance != distances[router]:  # Entrée périmée après une relaxation.
            continue
        for neighbor, cost in sorted(lsdb.get_neighbors(router).items()):
            # Arithmétique exacte sur les valeurs décimales fournies : évite
            # 0.1 + 0.2 != 0.3 et les débordements de sommes finies.
            candidate = distance + Fraction(str(cost))
            if candidate < distances[neighbor]:
                distances[neighbor] = candidate
                predecessors[neighbor] = router
                heapq.heappush(queue, (candidate, neighbor))
            # Égalité : conserver le premier prédécesseur découvert.
            # Le tas départage par identifiant et les voisins sont triés.
    return SPFResult(source, distances, predecessors, perf_counter() - start)

def reconstruct_path(predecessors: dict[str, str | None], source: str,
                     destination: str) -> list[str]:
    if source not in predecessors or destination not in predecessors:
        return []
    path: list[str] = []
    visited: set[str] = set()
    current: str | None = destination
    while current is not None:
        if current in visited:
            raise ValueError("Cycle détecté dans les prédécesseurs.")
        visited.add(current)
        path.append(current)
        if current == source:
            return path[::-1]
        if current not in predecessors:
            raise ValueError("Prédécesseur absent de la structure.")
        current = predecessors[current]
    return []

def run_all(lsdbs: dict[str, LinkStateDatabase]) -> dict[str, SPFResult]:
    return {source: dijkstra(database, source)
            for source, database in sorted(lsdbs.items())}
