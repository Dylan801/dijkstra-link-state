"""Construction des routes à partir du résultat SPF."""
from .models import SPFResult, RoutingEntry
from .spf import reconstruct_path

def build_routing_table(result: SPFResult) -> list[RoutingEntry]:
    entries = []
    for destination, cost in sorted(result.distances.items()):
        path = tuple(reconstruct_path(result.predecessors, result.source, destination))
        next_hop = ("Local" if len(path) == 1 else path[1]) if path else None
        entries.append(RoutingEntry(destination, next_hop, cost, path,
                                    (next_hop,) if next_hop else ()))
    return entries
