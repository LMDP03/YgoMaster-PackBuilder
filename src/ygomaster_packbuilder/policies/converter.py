from ygomaster_packbuilder.domain import OpeningPolicy, RarityDistribution, TenPackGuarantee, UltraRarePity

from .models import PoliciesConfig, PolicyDefinition, PolicyRarityDistribution

def _convert_distribution(distribution: PolicyRarityDistribution) -> RarityDistribution:
    return RarityDistribution(
        normal=distribution.normal,
        rare=distribution.rare,
        super_rare=distribution.super_rare,
        ultra_rare=distribution.ultra_rare,
    )

def _convert_policy(policy: PolicyDefinition) -> OpeningPolicy:
    return OpeningPolicy(
        key=policy.key,
        normal_slot_distribution=_convert_distribution(policy.normal_slot_distribution),
        ten_pack_guarantee=TenPackGuarantee(
            enabled=policy.ten_pack_guarantee.enabled,
            final_slot_distribution=_convert_distribution(policy.ten_pack_guarantee.final_slot_distribution)
        ),
        ultra_rare_pity=UltraRarePity(
            enabled=policy.ultra_rare_pity.enabled,
            guaranteed_slot_distribution=_convert_distribution(policy.ultra_rare_pity.guaranteed_slot_distribution)
        )
    )

def convert_policies_to_domain(config: PoliciesConfig) -> list[OpeningPolicy]:
    return [_convert_policy(policy) for policy in config.policies]