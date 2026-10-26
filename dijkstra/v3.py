"""Interface des scénarios et du simulateur interactif."""
import argparse
import json
from pathlib import Path
from .advanced.topology_io import load_topology
from .advanced.exports import json_value
from .simulation.simulator import LinkStateSimulator
from .simulation.scenarios import load_scenario, apply_action
from .display import show_table

LABELS = {"link_appeared": "Apparition de liaison", "link_removed": "Suppression de liaison",
          "link_cost_changed": "Changement de coût", "lsa_generated": "Génération LSA",
          "lsa_received": "Réception LSA", "lsa_rejected": "Rejet LSA obsolète ou déjà connue",
          "lsdb_updated": "Mise à jour LSDB", "spf_calculated": "Calcul SPF",
          "routing_changed": "Modification de table", "convergence": "État de convergence",
          "delivery_dropped": "Livraison interrompue", "adjacency_synchronized": "Échange de bases"}

def show_journal(simulator: LinkStateSimulator, start: int = 0) -> None:
    for event in simulator.journal[start:]:
        details = event.details
        if event.kind == "routing_changed":
            details = {"routes": len(event.details["after"])}
        print(f"[{event.index:04d} / étape {event.step}] {event.router or '-'} : "
              f"{LABELS[event.kind]} — {json.dumps(json_value(details), ensure_ascii=False)}")

def show_local_lsdbs(simulator: LinkStateSimulator) -> None:
    for name, router in simulator.routers.items():
        print(f"\nLSDB locale de {name} :")
        for _, advertisement in sorted(router.lsas.items()):
            print(json.dumps(advertisement.to_dict(), ensure_ascii=False))

def show_tables(simulator: LinkStateSimulator) -> None:
    for name, router in simulator.routers.items():
        print(f"\nTable de {name} :")
        show_table(router.table)

def show_changes(simulator: LinkStateSimulator, before: dict) -> None:
    changes = simulator.compare_tables(before)
    print("Comparaison avant/après :")
    if not changes:
        print("Aucune modification de table.")
    for router, states in changes.items():
        print(f"  {router} :")
        previous = {entry["destination"]: entry for entry in states["before"]}
        following = {entry["destination"]: entry for entry in states["after"]}
        for destination in sorted(set(previous) | set(following)):
            if previous.get(destination) != following.get(destination):
                print("    " + json.dumps(json_value({"destination": destination,
                       "before": previous.get(destination), "after": following.get(destination)}), ensure_ascii=False))

def execute_scenario(path: str | Path, trace: bool = True) -> LinkStateSimulator:
    simulator, actions = load_scenario(path)
    print(f"\n=== Scénario : {Path(path).stem} ===")
    cursor = 0
    before = simulator.snapshot_tables()
    for action in actions:
        print("Action : " + json.dumps(action, ensure_ascii=False))
        apply_action(simulator, action)
        if trace:
            show_journal(simulator, cursor)
        cursor = len(simulator.journal)
        if action["operation"] == "run":
            show_changes(simulator, before)
            before = simulator.snapshot_tables()
            print(json.dumps(simulator.convergence_status(), ensure_ascii=False))
    show_tables(simulator)
    return simulator

def interactive(simulator: LinkStateSimulator) -> LinkStateSimulator:
    before = simulator.snapshot_tables()
    while True:
        print("\n1 Voisins / 2 LSDB / 3 Étape / 4 Convergence / 5 Panne / 6 Restaurer / "
              "7 Coût / 8 Isoler / 9 Tables / 10 Journal / 11 Comparer / 12 Exporter / 13 Réinitialiser / 0 Quitter")
        try:
            choice = input("Choix : ").strip()
            if choice == "0":
                return simulator
            if choice == "1":
                for r in simulator.routers:
                    print(r, simulator.physical.get_neighbors(r))
            elif choice == "2":
                show_local_lsdbs(simulator)
            elif choice in {"3", "4"}:
                cursor = len(simulator.journal)
                if choice == "3":
                    if not simulator.step():
                        print("Aucun événement en attente.")
                else:
                    simulator.run_until_convergence()
                show_journal(simulator, cursor)
            elif choice in {"5", "6", "7", "8"}:
                before = simulator.snapshot_tables()
                if choice == "8":
                    simulator.isolate_router(input("Routeur : ").strip())
                else:
                    source = input("Extrémité A : ").strip()
                    target = input("Extrémité B : ").strip()
                    if choice == "5":
                        simulator.fail_link(source, target)
                    else:
                        cost = float(input("Coût : "))
                        if choice == "6":
                            simulator.restore_link(source, target, cost)
                        else:
                            simulator.change_cost(source, target, cost)
                print("Changement appliqué ; avancer par étapes ou lancer la convergence.")
            elif choice == "9":
                show_tables(simulator)
            elif choice == "10":
                show_journal(simulator)
            elif choice == "11":
                show_changes(simulator, before)
            elif choice == "12":
                simulator.export(input("Dossier [outputs/simulation] : ").strip() or "outputs/simulation")
            elif choice == "13":
                simulator = LinkStateSimulator(simulator.physical)
                before = simulator.snapshot_tables()
                print("Simulation réinitialisée sur la topologie physique actuelle.")
            else:
                print("Choix inconnu.")
        except (ValueError, RuntimeError) as error:
            print(f"Erreur : {error}")
        except (EOFError, KeyboardInterrupt):
            print("\nFin de simulation.")
            return simulator

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="V3 — simulateur Link-State pédagogique")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--demo", action="store_true", help="Exécuter les quatre démonstrations")
    group.add_argument("--scenario", metavar="JSON", help="Exécuter un scénario")
    parser.add_argument("--topology", default="data/topologie_exemple.json", help="Topologie physique initiale")
    parser.add_argument("--interactive", action="store_true", help="Menu ; initialement sans propagation")
    parser.add_argument("--steps", type=int, help="Nombre de livraisons à exécuter sans convergence implicite")
    parser.add_argument("--until-convergence", action="store_true", help="Converger après les étapes demandées")
    parser.add_argument("--fail", nargs=2, action="append", default=[], metavar=("A", "B"))
    parser.add_argument("--restore", nargs=3, action="append", default=[], metavar=("A", "B", "COUT"))
    parser.add_argument("--cost", nargs=3, action="append", default=[], metavar=("A", "B", "COUT"))
    parser.add_argument("--isolate", action="append", default=[], metavar="R")
    parser.add_argument("--journal", action="store_true", help="Afficher tout le journal")
    parser.add_argument("--lsdb", action="store_true", help="Afficher les annonces locales")
    parser.add_argument("--export", metavar="DOSSIER", help="Exporter journal, LSDB, tables et convergence")
    parser.add_argument("--web", action="store_true", help="Interface graphique locale dans le navigateur")
    parser.add_argument("--host", default="127.0.0.1", help="Adresse du serveur graphique")
    parser.add_argument("--port", type=int, default=8080, help="Port de l'interface graphique")
    args = parser.parse_args(argv)
    try:
        if args.web:
            if args.demo or args.scenario or args.interactive or args.steps is not None or args.fail or args.restore or args.cost or args.isolate or args.until_convergence or args.export or args.journal or args.lsdb:
                raise ValueError("--web s'utilise avec --topology, --host et --port uniquement.")
            if not 1 <= args.port <= 65535:
                raise ValueError("Le port doit être compris entre 1 et 65535.")
            from .visual.server import serve
            serve(args.topology, args.host, args.port)
            return 0
        if args.steps is not None and args.steps < 0:
            raise ValueError("--steps doit être positif ou nul.")
        if args.demo:
            if args.scenario or args.interactive or args.steps is not None or args.fail or args.restore or args.cost or args.isolate:
                raise ValueError("--demo se combine seulement avec --export, --journal et --lsdb.")
            base = Path(__file__).resolve().parents[1] / "scenarios"
            for name in ("reseau_stable", "panne_liaison", "changement_cout", "partition_reconnexion"):
                simulator = execute_scenario(base / f"{name}.json")
                if args.lsdb:
                    show_local_lsdbs(simulator)
                if args.export:
                    simulator.export(str(Path(args.export) / name))
            return 0
        if args.scenario:
            simulator = execute_scenario(args.scenario)
        else:
            simulator = LinkStateSimulator(load_topology(args.topology))
            if not args.interactive and args.steps is None:
                simulator.run_until_convergence()
        before = simulator.snapshot_tables()
        for a, b in args.fail:
            simulator.fail_link(a, b)
        for a, b, cost in args.restore:
            simulator.restore_link(a, b, float(cost))
        for a, b, cost in args.cost:
            simulator.change_cost(a, b, float(cost))
        for router in args.isolate:
            simulator.isolate_router(router)
        if args.steps is not None:
            for _ in range(args.steps):
                if not simulator.step():
                    break
        if args.until_convergence or (not args.interactive and args.steps is None):
            simulator.run_until_convergence()
        if args.interactive:
            simulator = interactive(simulator)
        show_changes(simulator, before)
        show_tables(simulator)
        print(json.dumps(simulator.convergence_status(), ensure_ascii=False))
        if args.lsdb:
            show_local_lsdbs(simulator)
        if args.journal:
            show_journal(simulator)
        if args.export:
            simulator.export(args.export)
    except (ValueError, RuntimeError, TypeError, OverflowError, OSError) as error:
        parser.exit(2, f"Erreur : {error}\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
