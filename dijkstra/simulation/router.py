"""État privé d'un routeur ; SPF ne reçoit jamais la topologie physique."""
from dataclasses import dataclass, field, replace
from fractions import Fraction
from ..core.graph import NetworkGraph
from ..core.lsdb import LinkStateDatabase
from ..core.models import SPFResult, RoutingEntry
from ..core.routing import build_routing_table
from ..core.spf import dijkstra
from .lsa import LinkStateAdvertisement

def ecmp_next_hops(database: LinkStateDatabase, result: SPFResult) -> dict[str, tuple[str, ...]]:
    # Les arêtes tendues forment un DAG car les coûts sont strictement positifs.
    # Propager tous les premiers sauts sur ce DAG, pas un prédécesseur arbitraire.
    hops: dict[str, set[str]] = {r: set() for r in result.distances}
    reachable = [r for r, cost in result.distances.items() if cost != float("inf")]
    for router in sorted(reachable, key=lambda r: (result.distances[r], r)):
        for neighbor, cost in database.get_neighbors(router).items():
            if result.distances[router] + Fraction(str(cost)) == result.distances[neighbor]:
                hops[neighbor].update({neighbor} if router == result.source else hops[router])
    hops[result.source] = {"Local"}
    return {r: tuple(sorted(values)) for r, values in hops.items()}

@dataclass
class Router:
    identifier: str
    sequence: int = 0
    lsas: dict[str, LinkStateAdvertisement] = field(default_factory=dict)
    result: SPFResult | None = None
    table: list[RoutingEntry] = field(default_factory=list)

    def accept(self, advertisement: LinkStateAdvertisement) -> bool:
        current = self.lsas.get(advertisement.origin)
        if current is not None and current.sequence >= advertisement.sequence:
            return False
        self.lsas[advertisement.origin] = advertisement
        return True

    def local_database(self) -> LinkStateDatabase:
        # Les noms viennent exclusivement des annonces reçues ou locales.
        names = {self.identifier} | set(self.lsas)
        for advertisement in self.lsas.values():
            names.update(neighbor for neighbor, _ in advertisement.neighbors)
        graph = NetworkGraph()
        for name in sorted(names):
            graph.add_router(name)
        for origin, advertisement in sorted(self.lsas.items()):
            for neighbor, cost in advertisement.neighbors:
                remote = self.lsas.get(neighbor)
                # Une liaison utilisable exige deux déclarations concordantes.
                # Une annonce ancienne d'une autre partition ne suffit donc pas
                # à ressusciter une liaison retirée par son extrémité locale.
                if origin < neighbor and remote and dict(remote.neighbors).get(origin) == cost:
                    graph.add_link(origin, neighbor, cost)
        return LinkStateDatabase(graph)

    def calculate_routes(self) -> bool:
        database = self.local_database()
        self.result = dijkstra(database, self.identifier)
        alternatives = ecmp_next_hops(database, self.result)
        table = [replace(entry, next_hops=alternatives[entry.destination])
                 for entry in build_routing_table(self.result)]
        changed = table != self.table
        self.table = table
        return changed

    def route_to(self, destination: str) -> RoutingEntry:
        # Une destination jamais apprise est inconnue et inaccessible localement.
        return next((entry for entry in self.table if entry.destination == destination),
                    RoutingEntry(destination, None, float("inf"), (), ()))
