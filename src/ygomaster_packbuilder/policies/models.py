from dataclasses import dataclass, field

@dataclass(slots=True)
class PolicyRarityDistribution:
    normal: float
    rare: float
    super_rare: float
    ultra_rare: float

@dataclass(slots=True)
class PolicyTenPackGuarantee:
    enabled: bool
    final_slot_distribution: PolicyRarityDistribution

@dataclass(slots=True)
class PolicyUltraRarePity:
    enabled: bool
    guaranteed_slot_distribution: PolicyRarityDistribution

@dataclass(slots=True)
class PolicyDefinition:
    key: str
    normal_slot_distribution: PolicyRarityDistribution
    ten_pack_guarantee: PolicyTenPackGuarantee
    ultra_rare_pity: PolicyUltraRarePity

@dataclass(slots=True)
class PoliciesConfig:
    policies: list[PolicyDefinition] = field(default_factory=list)