from ygomaster_packbuilder.domain import PackType

from .models import PackRule, RarityComposition

PACK_RULES: dict[PackType, PackRule] = {
    PackType.PERSONAL_MAIN: PackRule(
        expected_card_count=100,
        booster_size=7,
        rarity_composition=RarityComposition(
            normal=50,
            rare=25,
            super_rare=15,
            ultra_rare=10,
        ),
    ),

    PackType.PERSONAL_MINI: PackRule(
        expected_card_count=20,
        booster_size=3,
        rarity_composition=RarityComposition(
            normal=10,
            rare=5,
            super_rare=3,
            ultra_rare=2,
        ),
    ),

    PackType.SHARED_STAPLES: PackRule(
        expected_card_count=200,
        booster_size=11,
        rarity_composition=RarityComposition(
            normal=100,
            rare=60,
            super_rare=20,
            ultra_rare=20,
        ),
    ),
}

def get_pack_rule(pack_type: PackType) -> PackRule:
    return PACK_RULES[pack_type]