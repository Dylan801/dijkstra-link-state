"""Copies privées de la topologie connue par chaque routeur."""
from .graph import NetworkGraph, Cost

class LinkStateDatabase:
    def __init__(self, graph: NetworkGraph) -> None:
        graph.validate()
        self._graph = graph.copy()

    def get_routers(self) -> list[str]:
        return self._graph.get_routers()

    def get_neighbors(self, router: str) -> dict[str, Cost]:
        return self._graph.get_neighbors(router)

    def get_links(self) -> list[tuple[str, str, Cost]]:
        return self._graph.get_links()

    def to_dict(self) -> dict:
        return {"routers": self.get_routers(),
                "neighbors": {r: self.get_neighbors(r) for r in self.get_routers()},
                "links": [{"source": a, "target": b, "cost": c}
                          for a, b, c in self.get_links()]}

def build_lsdbs(graph: NetworkGraph) -> dict[str, LinkStateDatabase]:
    return {router: LinkStateDatabase(graph) for router in graph.get_routers()}
