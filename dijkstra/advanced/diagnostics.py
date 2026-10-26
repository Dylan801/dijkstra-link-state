"""Connectivité topologique, sans paquets réseau réels."""
from ..core.graph import NetworkGraph

def reachable_routers(graph: NetworkGraph, source: str) -> list[str]:
    graph.get_neighbors(source)  # Valide la source, y compris dans un graphe vide.
    seen = {source}
    pending = [source]
    while pending:
        router = pending.pop()
        for neighbor in graph.get_neighbors(router):
            if neighbor not in seen:
                seen.add(neighbor)
                pending.append(neighbor)
    return sorted(seen)

def connected_components(graph: NetworkGraph) -> list[list[str]]:
    remaining = set(graph.get_routers())
    components = []
    while remaining:
        component = reachable_routers(graph, min(remaining))
        components.append(component)
        remaining.difference_update(component)
    return components

def find_bridges(graph: NetworkGraph) -> list[tuple[str, str]]:
    # Tarjan itératif : reste utilisable au-delà de la limite de récursion.
    discovery: dict[str, int] = {}
    low: dict[str, int] = {}
    parent: dict[str, str | None] = {}
    bridges = []
    clock = 0
    for root in graph.get_routers():
        if root in discovery:
            continue
        parent[root] = None
        discovery[root] = low[root] = clock
        clock += 1
        stack = [(root, iter(graph.get_neighbors(root)))]
        while stack:
            router, neighbors = stack[-1]
            neighbor = next(neighbors, None)
            if neighbor is None:
                stack.pop()
                previous = parent[router]
                if previous is not None:
                    low[previous] = min(low[previous], low[router])
                    if low[router] > discovery[previous]:
                        bridges.append(tuple(sorted((previous, router))))
            elif neighbor not in discovery:
                parent[neighbor] = router
                discovery[neighbor] = low[neighbor] = clock
                clock += 1
                stack.append((neighbor, iter(graph.get_neighbors(neighbor))))
            elif neighbor != parent[router]:
                low[router] = min(low[router], discovery[neighbor])
    return sorted(bridges)

def diagnose(graph: NetworkGraph, source: str) -> dict:
    reachable = reachable_routers(graph, source)
    return {"source": source, "reachable": reachable,
            "unreachable": sorted(set(graph.get_routers()) - set(reachable)),
            "components": connected_components(graph), "bridges": find_bridges(graph)}
