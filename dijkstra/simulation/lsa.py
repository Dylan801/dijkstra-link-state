"""Annonce immuable : l'identifiant est le couple origine / séquence."""
from dataclasses import dataclass
from ..core.graph import Cost, validate_cost, validate_router

@dataclass(frozen=True)
class LinkStateAdvertisement:
    origin: str
    neighbors: tuple[tuple[str, Cost], ...]
    sequence: int

    def __post_init__(self) -> None:
        validate_router(self.origin)
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int) or self.sequence < 1:
            raise ValueError("Séquence LSA : entier strictement positif exigé.")
        if not isinstance(self.neighbors, tuple):
            raise ValueError("Les voisins LSA doivent être un tuple immuable.")
        seen = set()
        for entry in self.neighbors:
            if not isinstance(entry, tuple) or len(entry) != 2:
                raise ValueError("Voisin LSA mal formé.")
            neighbor, cost = entry
            validate_router(neighbor)
            validate_cost(cost)
            if neighbor == self.origin or neighbor in seen:
                raise ValueError("Voisin LSA dupliqué ou boucle locale.")
            seen.add(neighbor)

    @property
    def identifier(self) -> tuple[str, int]:
        return self.origin, self.sequence

    def to_dict(self) -> dict:
        return {"origin": self.origin, "sequence": self.sequence,
                "id": list(self.identifier), "neighbors": dict(self.neighbors)}
