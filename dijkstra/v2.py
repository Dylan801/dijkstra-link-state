"""CLI et menu de l'outil d'analyse statique."""
import argparse
import json
from .advanced.topology_io import load_topology
from .advanced.service import NetworkAnalyzer
from .advanced.diagnostics import diagnose
from .advanced.exports import export_analysis
from .advanced.visualization import text_topology, write_svg
from .display import show_result, show_table, show_lsdb, format_cost
from .core.spf import reconstruct_path

def show_statistics(analyzer: NetworkAnalyzer, source: str, destination: str | None) -> None:
    stats = analyzer.statistics(source, destination)
    print(f"Statistiques : {stats['routers']} routeurs ; {stats['links']} liaisons ; "
          f"{stats['unreachable']} destinations inaccessibles depuis {source}.")
    print(f"SPF source : {stats['spf_seconds']:.6f} s ; tous SPF : {stats['all_spf_seconds']:.6f} s.")
    if destination:
        print(f"Coût minimal : {format_cost(stats['minimal_cost'])} ; "
              f"routeurs du chemin : {stats['routers_on_path']} ; sauts : {stats['hops']} ; "
              f"intermédiaires : {stats['intermediate_routers']}.")

def interactive(analyzer: NetworkAnalyzer) -> None:
    while True:
        print("\n1 Voisins / 2 LSDB / 3 SPF / 4 Tous SPF / 5 Chemin / 6 Table / "
              "7 Diagnostic / 8 Modifier / 9 Exporter / 0 Quitter")
        try:
            choice = input("Choix : ").strip()
            if choice == "0":
                return
            if choice == "1":
                for r in analyzer.graph.get_routers():
                    print(r, analyzer.graph.get_neighbors(r))
            elif choice == "4":
                for r, result in analyzer.results.items():
                    show_result(analyzer.lsdbs[r], result)
            elif choice == "8":
                print("Opérations : add_router, remove_router, add_link, remove_link, update_link")
                operation = input("Opération : ").strip()
                args = input("Arguments séparés par des espaces (A B 2 pour un lien) : ").split()
                if operation in {"add_link", "update_link"} and len(args) == 3:
                    args[2] = float(args[2])
                analyzer.modify(operation, *args)
                print("LSDB et tables recalculées pour toutes les sources.")
            elif choice == "9":
                print(*export_analysis(analyzer, input("Dossier [outputs] : ").strip() or "outputs"), sep="\n")
            elif choice in {"2", "3", "5", "6", "7"}:
                source = input("Source : ").strip()
                if source not in analyzer.results:
                    raise ValueError("Source inconnue.")
                if choice == "2":
                    show_lsdb(analyzer.lsdbs[source])
                elif choice == "3":
                    show_result(analyzer.lsdbs[source], analyzer.results[source])
                elif choice == "5":
                    destination = input("Destination : ").strip()
                    show_statistics(analyzer, source, destination)
                    print(" -> ".join(reconstruct_path(analyzer.results[source].predecessors, source, destination)) or "Inaccessible")
                elif choice == "6":
                    show_table(analyzer.tables[source])
                else:
                    print(json.dumps(diagnose(analyzer.graph, source), ensure_ascii=False, indent=2))
            else:
                print("Choix inconnu.")
        except (ValueError, TypeError) as error:
            print(f"Erreur : {error}")
        except (EOFError, KeyboardInterrupt):
            print("\nFin du menu.")
            return

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V2 — analyse de topologie et calcul SPF")
    parser.add_argument("--topology", default="data/topologie_exemple.json", help="Fichier JSON")
    parser.add_argument("--command", choices=["all", "routers", "lsdb", "spf", "path", "table", "diagnose", "topology"], default="all")
    parser.add_argument("--source", help="Routeur source")
    parser.add_argument("--destination", help="Destination du chemin")
    parser.add_argument("--interactive", action="store_true", help="Menu textuel")
    parser.add_argument("--export", metavar="DOSSIER", help="Exporter JSON et CSV")
    parser.add_argument("--svg", metavar="FICHIER", help="Dessiner un SVG")
    parser.add_argument("--add-router", action="append", default=[], metavar="R")
    parser.add_argument("--remove-router", action="append", default=[], metavar="R")
    parser.add_argument("--add-link", nargs=3, action="append", default=[], metavar=("A", "B", "COUT"))
    parser.add_argument("--remove-link", nargs=2, action="append", default=[], metavar=("A", "B"))
    parser.add_argument("--update-link", nargs=3, action="append", default=[], metavar=("A", "B", "COUT"))
    return parser

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        analyzer = NetworkAnalyzer(load_topology(args.topology))
        for router in args.add_router:
            analyzer.modify("add_router", router)
        for source, target, cost in args.add_link:
            analyzer.modify("add_link", source, target, float(cost))
        for source, target, cost in args.update_link:
            analyzer.modify("update_link", source, target, float(cost))
        for source, target in args.remove_link:
            analyzer.modify("remove_link", source, target)
        for router in args.remove_router:
            analyzer.modify("remove_router", router)
        if args.interactive:
            interactive(analyzer)
        else:
            routers = analyzer.graph.get_routers()
            source = args.source or (routers[0] if routers else None)
            if args.source is not None and args.source not in analyzer.results:
                raise ValueError("Source inconnue.")
            if args.destination is not None and args.destination not in routers:
                raise ValueError("Destination inconnue.")
            if args.command in {"lsdb", "spf", "path", "table", "diagnose"} and source is None:
                raise ValueError("Réseau vide : aucune source disponible.")
            if args.command == "all":
                for r, result in analyzer.results.items():
                    show_result(analyzer.lsdbs[r], result)
            elif args.command == "routers":
                for r in routers:
                    print(r, analyzer.graph.get_neighbors(r))
            elif args.command == "topology":
                print(text_topology(analyzer.graph))
            elif args.command == "lsdb":
                show_lsdb(analyzer.lsdbs[source])
            elif args.command == "spf":
                show_result(analyzer.lsdbs[source], analyzer.results[source])
            elif args.command == "table":
                show_table(analyzer.tables[source])
            elif args.command == "diagnose":
                print(json.dumps(diagnose(analyzer.graph, source), ensure_ascii=False, indent=2))
            elif args.command == "path":
                if not args.destination:
                    raise ValueError("--destination est obligatoire pour path.")
                print(" -> ".join(reconstruct_path(analyzer.results[source].predecessors, source, args.destination)) or "Inaccessible")
            if source:
                show_statistics(analyzer, source, args.destination)
        if args.export:
            print("Exports :", *export_analysis(analyzer, args.export), sep="\n")
        if args.svg:
            source = args.source or next(iter(analyzer.results), None)
            write_svg(analyzer.graph, args.svg, analyzer.results.get(source), args.destination)
            print(f"SVG : {args.svg}")
    except (ValueError, TypeError, OverflowError) as error:
        parser.exit(2, f"Erreur : {error}\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
