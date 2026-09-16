from dataclasses import dataclass, field
from enum import StrEnum

from .source import SourcePackRef
from .card import Card

class PackType(StrEnum):
    PERSONAL_MAIN = "personal_main"
    PERSONAL_MINI = "personal_mini"
    SHARED_STAPLES = "shared_staples"

@dataclass(slots=True)
class PackDefinition:
    # Identity
    key: str
    name: str
    description: str
    # Origin & Classification
    type: PackType
    source: SourcePackRef
    # Size & Policy
    expected_card_count: int
    booster_size: int
    opening_policy_key: str
    # Relations
    owner_key: str | None = None
    parent_pack_key: str | None = None
    # Card list
    cards: list[Card] = field(default_factory=list)