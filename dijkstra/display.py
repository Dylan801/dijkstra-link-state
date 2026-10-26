"""Affichage français commun aux trois points d'entrée."""
from decimal import Decimal, localcontext
from fractions import Fraction
from .core.lsdb import LinkStateDatabase
from .core.models import Distance, SPFResult, RoutingEntry
from .core.routing import build_routing_table
from .core.spf import reconstruct_path

def format_cost(cost: Distance) -> str:
    if cost == float("inf"):
        return "INF"
    if isinstance(cost, Fraction):
        if cost.denominator == 1:
            return str(cost.numerator)
        with localcontext() as context:
            context.prec = len(str(abs(cost.numerator))) + len(str(cost.denominator)) + 2
            return format(Decimal(cost.numerator) / Decimal(cost.denominator), "f").rstrip("0").rstrip(".")
    return str(cost)

def show_lsdb(database: LinkStateDatabase) -> None:
    print("LSDB — routeurs : " + ", ".join(database.get_routers()))
    for router in database.get_routers():
        neighbors = ", ".join(f"{r} (coût {c})" for r, c in database.get_neighbors(router).items())
        print(f"  {router} : {neighbors or 'aucun voisin'}")
    print("Liaisons :")
    for source, target, cost in database.get_links():
        print(f"  {source} --{cost}-- {target}")

def show_table(table: list[RoutingEntry]) -> None:
    print("Destination | Next Hop(s) | Coût | Chemin")
    for entry in table:
        hops = ", ".join(entry.next_hops) or entry.next_hop or "-"
        path = " -> ".join(entry.path) or "Inaccessible"
        print(f"{entry.destination} | {hops} | {format_cost(entry.cost)} | {path}")

def show_result(database: LinkStateDatabase, result: SPFResult) -> None:
    print(f"\n=== Routeur source : {result.source} ===")
    show_lsdb(database)
    print(f"Arbre SPF — racine {result.source} :")
    print(f"  {result.source} (coût 0)")
    for parent, destination in result.tree_edges:
        print(f"  {parent} -> {destination} (coût depuis racine {format_cost(result.distances[destination])})")
    print("Distances / prédécesseurs / chemins :")
    for destination, cost in sorted(result.distances.items()):
        path = reconstruct_path(result.predecessors, result.source, destination)
        print(f"  {destination} : {format_cost(cost)} ; prédécesseur {result.predecessors[destination] or '-'} ; "
              + (" -> ".join(path) if path else "Inaccessible"))
    print("Table de routage :")
    show_table(build_routing_table(result))
