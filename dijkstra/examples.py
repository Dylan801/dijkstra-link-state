from .core.graph import NetworkGraph

def reference_graph() -> NetworkGraph:
    graph = NetworkGraph()
    for router in ("R1", "R2", "R3", "R4", "R5", "R6"):
        graph.add_router(router)
    for source, target, cost in [("R1", "R2", 2), ("R1", "R3", 5),
                                ("R2", "R3", 1), ("R2", "R4", 2),
                                ("R3", "R4", 3), ("R4", "R5", 1),
                                ("R3", "R5", 10)]:
        graph.add_link(source, target, cost)
    return graph
