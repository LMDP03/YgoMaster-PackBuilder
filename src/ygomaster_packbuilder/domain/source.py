from dataclasses import dataclass
from enum import StrEnum

class SourceProvider(StrEnum):
    YGOPRODECK = "ygoprodeck"

@dataclass(slots=True, frozen=True)
class SourcePackRef:
    provider: SourceProvider
    external_id: str