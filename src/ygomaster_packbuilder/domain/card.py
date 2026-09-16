from dataclasses import dataclass

from .rarity import Rarity

@dataclass(slots=True)
class Card:
    name: str
    ydk_id: int
    source_rarity: str
    master_duel_id: int | None = None
    rarity: Rarity | None = None