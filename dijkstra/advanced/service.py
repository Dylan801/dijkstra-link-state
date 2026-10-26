"""Session V2 : chaque modification valide reconstruit toutes les LSDB."""
from ..core.graph import NetworkGraph, Cost
from ..core.lsdb import build_lsdbs
from ..core.spf import run_all
from ..core.routing import build_routing_table

class NetworkAnalyzer:
    def __init__(self, graph: NetworkGraph) -> None:
        self.graph = graph.copy()
        self.recalculate()

    def recalculate(self) -> None:
        self.lsdbs = build_lsdbs(self.graph)
        self.results = run_all(self.lsdbs)
        self.tables = {r: build_routing_table(result) for r, result in self.results.items()}

    def modify(self, operation: str, *arguments: str | Cost) -> None:
        if operation not in {"add_router", "remove_router", "add_link", "remove_link", "update_link"}:
            raise ValueError("Opération de topologie inconnue.")
        candidate = self.graph.copy()
        getattr(candidate, operation)(*arguments)
        candidate.validate()
        self.graph = candidate
        self.recalculate()

    def statistics(self, source: str, destination: str | None = None) -> dict:
        if source not in self.results:
            raise ValueError(f"Source inconnue : {source}")
        result = self.results[source]
        stats = {"routers": len(self.graph.get_routers()), "links": len(self.graph.get_links()),
                 "unreachable": sum(c == float("inf") for c in result.distances.values()),
                 "spf_seconds": result.elapsed_seconds,
                 "all_spf_seconds": sum(r.elapsed_seconds for r in self.results.values())}
        if destination is not None:
            entry = next((e for e in self.tables[source] if e.destination == destination), None)
            if entry is None:
                raise ValueError(f"Destination inconnue : {destination}")
            stats.update(minimal_cost=entry.cost, routers_on_path=len(entry.path),
                         intermediate_routers=max(0, len(entry.path) - 2),
                         hops=max(0, len(entry.path) - 1))
        return stats
