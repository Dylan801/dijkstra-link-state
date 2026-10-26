from dataclasses import dataclass, asdict
from .lsa import LinkStateAdvertisement

@dataclass(frozen=True)
class Delivery:
    sender: str
    receiver: str
    advertisement: LinkStateAdvertisement
    link_epoch: int

@dataclass(frozen=True)
class JournalEntry:
    index: int
    step: int
    kind: str
    router: str | None
    details: dict

    def to_dict(self) -> dict:
        return asdict(self)
