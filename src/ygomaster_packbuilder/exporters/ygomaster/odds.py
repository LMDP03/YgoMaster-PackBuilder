from ygomaster_packbuilder.domain import OpeningPolicy, PackDefinition, ProjectDefinition, RarityDistribution
from ygomaster_packbuilder.registry import get_pack_shop_id

YGOMASTER_GACHA_TYPE = 1

YGOMASTER_RARITY_N = 1
YGOMASTER_RARITY_R = 2
YGOMASTER_RARITY_SR = 3
YGOMASTER_RARITY_UR = 4

def _distribution_to_rate(distribution: RarityDistribution) -> dict[str, dict[str, str]]:
    values = {
        YGOMASTER_RARITY_N: distribution.normal,
        YGOMASTER_RARITY_R: distribution.rare,
        YGOMASTER_RARITY_SR: distribution.super_rare,
        YGOMASTER_RARITY_UR: distribution.ultra_rare,
    }
    return {str(rarity): {"rate": f"{rate:.2f}"} for rarity, rate in values.items() if rate > 0}

def _build_pack_odds(
    pack: PackDefinition,
    policy: OpeningPolicy,
    pack_id: int,
) -> dict[str, object]:
    final_slot = pack.booster_size
    card_rate_list: list[dict[str, object]] = [
        {
            "start_num": 1,
            "end_num": pack.booster_size,
            "standard": False,
            "rate": _distribution_to_rate(policy.normal_slot_distribution),
        }
    ]
    if policy.ten_pack_guarantee.enabled:
        card_rate_list.append(
            {
                "start_num": final_slot,
                "end_num": final_slot,
                "standard": False,
                "settle_rare_min": YGOMASTER_RARITY_SR,
                "settle_rare_max": YGOMASTER_RARITY_UR,
                "rate": _distribution_to_rate(policy.ten_pack_guarantee.final_slot_distribution),
            }
        )
    if policy.ultra_rare_pity.enabled:
        card_rate_list.append(
            {
                "start_num": final_slot,
                "end_num": final_slot,
                "standard": False,
                "settle_rare_min": YGOMASTER_RARITY_UR,
                "settle_rare_max": YGOMASTER_RARITY_UR,
                "rate": _distribution_to_rate(policy.ultra_rare_pity.guaranteed_slot_distribution),
            }
        )
    premiere_rate_list = [
        {
            "rare": [4, 3],
            "rate": {
                "3": "1.00",
                "2": "9.00",
                "1": "90.00",
            },
        },
        {
            "rare": [2, 1],
            "rate": {
                "2": "10.00",
                "1": "90.00",
            },
        },
    ]
    return {
        "packShopIds": [get_pack_shop_id(pack_id)],
        "gachaType": YGOMASTER_GACHA_TYPE,
        "cardRateList": card_rate_list,
        "premiereRateList": premiere_rate_list,
    }

def build_pack_odds_export(project: ProjectDefinition, pack_ids: dict[str, int]) -> list[dict[str, object]]:
    policies = {policy.key: policy for policy in project.opening_policies}

    result: list[dict[str, object]] = []
    for pack in project.packs:
        try:
            pack_id = pack_ids[pack.key]
        except KeyError as exc:
            raise ValueError(f"No YgoMaster pack ID assigned to pack {pack.key!r}.") from exc
        
        try:
            policy = policies[pack.opening_policy_key]
        except KeyError as exc:
            raise ValueError(f"Pack {pack.key!r} references unknown opening policy {pack.opening_policy_key!r}.") from exc

        result.append(_build_pack_odds(pack, policy,  pack_id))

    return result