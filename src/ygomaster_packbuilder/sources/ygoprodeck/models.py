from dataclasses import dataclass, field

@dataclass(slots=True)
class YgoProDeckPackCard:
    name: str
    ydk_id: int
    card_type: str
    source_rarity: str

@dataclass(slots=True)
class YgoProDeckPackData:
    external_id: str
    name: str
    description: str
    creator: str
    image_id: str
    cards: list[YgoProDeckPackCard] = field(default_factory=list)

