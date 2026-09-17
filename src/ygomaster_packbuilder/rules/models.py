from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class RarityComposition:
    normal: int
    rare: int
    super_rare: int
    ultra_rare: int

    @property
    def total(self) -> int:
        return self.normal + self.rare + self.super_rare + self.ultra_rare

@dataclass(slots=True, frozen=True)
class PackRule:
    expected_card_count: int
    booster_size: int
    rarity_composition: RarityComposition