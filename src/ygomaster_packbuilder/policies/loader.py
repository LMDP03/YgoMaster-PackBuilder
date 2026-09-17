from pathlib import Path
from typing import Any

import yaml

from .models import PoliciesConfig, PolicyDefinition, PolicyRarityDistribution, PolicyTenPackGuarantee, PolicyUltraRarePity

def _load_yaml(file_path: Path) -> dict[str, Any]:
    if not file_path.exists():
        raise FileNotFoundError(f"Policies file not found: {file_path}")
    with file_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("Policies config root must be a mapping.")
    return data

def _parse_distribution(data: dict[str, Any]) -> PolicyRarityDistribution:
    normal_rate_data = data["normal"]
    if not isinstance(normal_rate_data, (int, float)):
        raise ValueError(f"Invalid value for 'normal' in rarity distribution: {normal_rate_data}")
    normal_rate = float(normal_rate_data)
    
    rare_rate_data = data["rare"]
    if not isinstance(rare_rate_data, (int, float)):
        raise ValueError(f"Invalid value for 'rare' in rarity distribution: {rare_rate_data}")
    rare_rate = float(rare_rate_data)

    super_rare_rate_data = data["super_rare"]
    if not isinstance(super_rare_rate_data, (int, float)):
        raise ValueError(f"Invalid value for 'super_rare' in rarity distribution: {super_rare_rate_data}")
    super_rare_rate = float(super_rare_rate_data)

    ultra_rare_rate_data = data["ultra_rare"]
    if not isinstance(ultra_rare_rate_data, (int, float)):
        raise ValueError(f"Invalid value for 'ultra_rare' in rarity distribution: {ultra_rare_rate_data}")
    ultra_rare_rate = float(ultra_rare_rate_data)

    return PolicyRarityDistribution(
        normal=normal_rate,
        rare=rare_rate,
        super_rare=super_rare_rate,
        ultra_rare=ultra_rare_rate,
    )

def _parse_ten_pack_guarantee(data: dict[str, Any]) -> PolicyTenPackGuarantee:
    enabled_flag = data["enabled"]
    if not isinstance(enabled_flag, bool):
        raise ValueError(f"Invalid value for 'enabled' in ten pack guarantee: {enabled_flag}")
    
    final_slot_distribution_data = data["final_slot_distribution"]
    if not isinstance(final_slot_distribution_data, dict):
        raise ValueError(f"Invalid value for 'final_slot_distribution' in ten pack guarantee: {final_slot_distribution_data}")
    final_slot_distribution = _parse_distribution(final_slot_distribution_data)
    
    return PolicyTenPackGuarantee(
        enabled=bool(enabled_flag),
        final_slot_distribution=final_slot_distribution
    )

def _parse_ultra_rare_pity(data: dict[str, Any]) -> PolicyUltraRarePity:
    enabled_flag = data["enabled"]
    if not isinstance(enabled_flag, bool):
        raise ValueError(f"Invalid value for 'enabled' in ultra rare pity: {enabled_flag}")
    
    guaranteed_slot_distribution_data = data["guaranteed_slot_distribution"]
    if not isinstance(guaranteed_slot_distribution_data, dict):
        raise ValueError(f"Invalid value for 'guaranteed_slot_distribution' in ultra rare pity: {guaranteed_slot_distribution_data}")
    guaranteed_slot_distribution = _parse_distribution(guaranteed_slot_distribution_data)
    
    return PolicyUltraRarePity(
        enabled=bool(enabled_flag),
        guaranteed_slot_distribution=guaranteed_slot_distribution
    )

def _parse_policy(data: dict[str, Any]) -> PolicyDefinition:
    key = data["key"]
    if not key:
        raise ValueError(f"Missing value for 'key' in policy definition")
    if not isinstance(key, str):
        raise ValueError(f"Invalid value for 'key' in policy definition: {key}")

    normal_slot_distribution_data = data["normal_slot_distribution"]
    if not normal_slot_distribution_data:
        raise ValueError(f"Missing value for 'normal_slot_distribution' in policy definition")
    if not isinstance(normal_slot_distribution_data, dict):
        raise ValueError(f"Invalid value for 'normal_slot_distribution' in policy definition: {normal_slot_distribution_data}")
    normal_slot_distribution = _parse_distribution(normal_slot_distribution_data)

    ten_pack_guarantee_data = data["ten_pack_guarantee"]
    if not ten_pack_guarantee_data:
        raise ValueError(f"Missing value for 'ten_pack_guarantee' in policy definition")
    if not isinstance(ten_pack_guarantee_data, dict):
        raise ValueError(f"Invalid value for 'ten_pack_guarantee' in policy definition: {ten_pack_guarantee_data}")
    ten_pack_guarantee = _parse_ten_pack_guarantee(ten_pack_guarantee_data)

    ultra_rare_pity_data = data["ultra_rare_pity"]
    if not ultra_rare_pity_data:
        raise ValueError(f"Missing value for 'ultra_rare_pity' in policy definition")
    if not isinstance(ultra_rare_pity_data, dict):
        raise ValueError(f"Invalid value for 'ultra_rare_pity' in policy definition: {ultra_rare_pity_data}")
    ultra_rare_pity = _parse_ultra_rare_pity(ultra_rare_pity_data)

    return PolicyDefinition(
        key=key,
        normal_slot_distribution=normal_slot_distribution,
        ten_pack_guarantee=ten_pack_guarantee,
        ultra_rare_pity=ultra_rare_pity
    )

def load_policies_config(file_path: str | Path) -> PoliciesConfig:
    file_path = Path(file_path)
    data = _load_yaml(file_path)

    policies_data = data.get("policies", [])
    if not isinstance(policies_data, list):
        raise ValueError(f"Invalid value for 'policies' in policies config: {policies_data}")

    policies = [_parse_policy(policy_data) for policy_data in policies_data]

    return PoliciesConfig(policies=policies)