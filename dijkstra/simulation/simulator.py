"""Moteur FIFO, une livraison par étape, aucune communication réelle."""
from collections import deque
from ..core.graph import NetworkGraph, Cost
from ..advanced.diagnostics import connected_components
from ..advanced.exports import table_dict, write_json
from .lsa import LinkStateAdvertisement
from .events import Delivery, JournalEntry
from .router import Router

class LinkStateSimulator:
    def __init__(self, graph: NetworkGraph) -> None:
        graph.validate()
        self.physical = graph.copy()
        self.routers = {r: Router(r) for r in graph.get_routers()}
        self.pending: deque[Delivery] = deque()
        self.journal: list[JournalEntry] = []
        self.step_number = 0
        self._epochs = {tuple(sorted((a, b))): 0 for a, b, _ in graph.get_links()}
        for a, b, cost in graph.get_links():
            self._log("link_appeared", None, source=a, target=b, cost=cost)
        for router in self.routers:
            self._originate(router)

    def _log(self, kind: str, router: str | None, **details: object) -> None:
        self.journal.append(JournalEntry(len(self.journal), self.step_number, kind, router, details))

    def _enqueue(self, sender: str, receiver: str, advertisement: LinkStateAdvertisement) -> None:
        key = tuple(sorted((sender, receiver)))
        self.pending.append(Delivery(sender, receiver, advertisement, self._epochs[key]))

    def _refresh(self, router: str) -> None:
        node = self.routers[router]
        previous = table_dict(node.table)
        changed = node.calculate_routes()
        self._log("spf_calculated", router, seconds=node.result.elapsed_seconds)
        if changed:
            self._log("routing_changed", router, before=previous, after=table_dict(node.table))

    def _originate(self, router: str) -> None:
        node = self.routers[router]
        node.sequence += 1
        advertisement = LinkStateAdvertisement(router, tuple(self.physical.get_neighbors(router).items()), node.sequence)
        node.lsas[router] = advertisement
        self._log("lsa_generated", router, advertisement=advertisement.to_dict())
        self._log("lsdb_updated", router, origin=router, sequence=node.sequence)
        self._refresh(router)
        for neighbor in self.physical.get_neighbors(router):
            self._enqueue(router, neighbor, advertisement)

    def step(self) -> bool:
        if not self.pending:
            return False
        delivery = self.pending.popleft()
        self.step_number += 1
        key = tuple(sorted((delivery.sender, delivery.receiver)))
        if (delivery.receiver not in self.physical.get_neighbors(delivery.sender)
                or self._epochs.get(key) != delivery.link_epoch):
            self._log("delivery_dropped", delivery.receiver, sender=delivery.sender,
                      reason="Liaison interrompue depuis l'envoi")
            return True
        advertisement = delivery.advertisement
        node = self.routers[delivery.receiver]
        self._log("lsa_received", delivery.receiver, sender=delivery.sender,
                  origin=advertisement.origin, sequence=advertisement.sequence)
        if not node.accept(advertisement):
            self._log("lsa_rejected", delivery.receiver, origin=advertisement.origin,
                      sequence=advertisement.sequence, reason="Version connue au moins aussi récente")
            return True
        self._log("lsdb_updated", delivery.receiver, origin=advertisement.origin, sequence=advertisement.sequence)
        self._refresh(delivery.receiver)
        for neighbor in self.physical.get_neighbors(delivery.receiver):
            if neighbor != delivery.sender:
                self._enqueue(delivery.receiver, neighbor, advertisement)
        return True

    def convergence_status(self) -> dict:
        components = connected_components(self.physical)
        valid = []
        for component in components:
            synchronized = True
            for receiver in component:
                node = self.routers[receiver]
                for origin in component:
                    # L'observateur vérifie la convergence ; ces annonces ne sont
                    # jamais copiées par lui dans les LSDB ni données au SPF.
                    latest = self.routers[origin].lsas[origin]
                    if node.lsas.get(origin) != latest:
                        synchronized = False
                reached = {entry.destination for entry in node.table if entry.cost != float("inf")}
                if reached != set(component):
                    synchronized = False
            valid.append({"routers": component, "synchronized": synchronized})
        return {"converged": not self.pending and all(c["synchronized"] for c in valid),
                "pending": len(self.pending), "components": valid}

    def run_until_convergence(self, max_steps: int = 1_000_000) -> int:
        if max_steps < 0:
            raise ValueError("Nombre d'étapes maximal négatif.")
        count = 0
        while self.pending and count < max_steps:
            self.step()
            count += 1
        status = self.convergence_status()
        self._log("convergence", None, **status)
        if not status["converged"]:
            raise RuntimeError("Convergence non atteinte ; file restante ou LSDB incohérentes.")
        return count

    def fail_link(self, source: str, target: str) -> None:
        self.physical.remove_link(source, target)
        key = tuple(sorted((source, target)))
        self._epochs[key] += 1
        self._log("link_removed", None, source=source, target=target)
        for router in sorted((source, target)):
            self._originate(router)

    def restore_link(self, source: str, target: str, cost: Cost) -> None:
        self.physical.add_link(source, target, cost)
        key = tuple(sorted((source, target)))
        self._epochs[key] = self._epochs.get(key, 0) + 1
        self._log("link_appeared", None, source=source, target=target, cost=cost)
        for router in sorted((source, target)):
            self._originate(router)
        # Échange de toute la base aux nouvelles adjacences. Sans cette phase,
        # les annonces anciennes mais encore courantes d'une partition resteraient absentes.
        for sender, receiver in ((source, target), (target, source)):
            for _, advertisement in sorted(self.routers[sender].lsas.items()):
                self._enqueue(sender, receiver, advertisement)
        self._log("adjacency_synchronized", None, source=source, target=target)

    def change_cost(self, source: str, target: str, cost: Cost) -> None:
        self.physical.update_link(source, target, cost)
        self._log("link_cost_changed", None, source=source, target=target, cost=cost)
        for router in sorted((source, target)):
            self._originate(router)

    def isolate_router(self, router: str) -> None:
        neighbors = list(self.physical.get_neighbors(router))
        for neighbor in neighbors:
            self.physical.remove_link(router, neighbor)
            self._epochs[tuple(sorted((router, neighbor)))] += 1
            self._log("link_removed", None, source=router, target=neighbor)
        for affected in sorted({router, *neighbors}):
            self._originate(affected)

    def snapshot_tables(self) -> dict:
        return {router: table_dict(node.table) for router, node in self.routers.items()}

    def compare_tables(self, before: dict) -> dict:
        after = self.snapshot_tables()
        return {router: {"before": before.get(router, []), "after": after[router]}
                for router in sorted(after) if before.get(router) != after[router]}

    def export(self, directory: str = "outputs/simulation") -> None:
        from pathlib import Path
        root = Path(directory)
        write_json(root / "events.json", [event.to_dict() for event in self.journal])
        write_json(root / "local_lsdb.json", {r: [lsa.to_dict() for _, lsa in sorted(node.lsas.items())]
                                             for r, node in self.routers.items()})
        write_json(root / "routing.json", self.snapshot_tables())
        write_json(root / "convergence.json", self.convergence_status())
