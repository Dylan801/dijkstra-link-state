from dataclasses import dataclass
from fractions import Fraction
from typing import TypeAlias

Distance: TypeAlias = Fraction | float

@dataclass
class SPFResult:
    source: str
    distances: dict[str, Distance]
    predecessors: dict[str, str | None]
    elapsed_seconds: float

    @property
    def tree_edges(self) -> list[tuple[str, str]]:
        return [(parent, node) for node, parent in sorted(self.predecessors.items())
                if parent is not None]

@dataclass(frozen=True)
class RoutingEntry:
    destination: str
    next_hop: str | None
    cost: Distance
    path: tuple[str, ...]
    next_hops: tuple[str, ...] = ()
