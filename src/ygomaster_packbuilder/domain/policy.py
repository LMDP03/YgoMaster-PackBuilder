from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class RarityDistribution:
    normal: float
    rare: float
    super_rare: float
    ultra_rare: float

@dataclass(slots=True, frozen=True)
class TenPackGuarantee:
    enabled: bool
    final_slot_distribution: RarityDistribution

@dataclass(slots=True, frozen=True)
class UltraRarePity:
    enabled: bool
    trigger_after_ten_pack_without_ur: bool
    guaranteed_slot_distribution: RarityDistribution

@dataclass(slots=True, frozen=True)
class OpeningPolicy:
    key: str
    normal_slot_distribution: RarityDistribution
    ten_pack_guarantee: TenPackGuarantee
    ultra_rare_pity: UltraRarePity
