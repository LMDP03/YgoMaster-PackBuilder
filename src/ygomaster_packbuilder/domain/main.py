from dataclasses import dataclass, field

from .pack import PackDefinition
from .player import PlayerDefinition
from .policy import OpeningPolicy

@dataclass(slots=True)
class ProjectDefinition:
    name: str
    players: list[PlayerDefinition] = field(default_factory=list)
    packs: list[PackDefinition] = field(default_factory=list)
    opening_policies: list[OpeningPolicy] = field(default_factory=list)

