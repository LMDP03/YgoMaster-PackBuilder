from ygomaster_packbuilder.domain import PackDefinition, ProjectDefinition, Rarity
from ygomaster_packbuilder.registry import get_pack_shop_id

YGOMASTER_SELECTION_PACK_TYPE = 2
YGOMASTER_CARD_THUMB_ICON_TYPE = 1

DEFAULT_PACK_PRICE = 100
DEFAULT_PACK_PRICE_X10 = 1000


RARITY_TO_YGOMASTER: dict[Rarity, int] = {
    Rarity.N: 1,
    Rarity.R: 2,
    Rarity.SR: 3,
    Rarity.UR: 4,
}
RARITY_PRIORITY: dict[Rarity, int] = {
    Rarity.N: 1,
    Rarity.R: 2,
    Rarity.SR: 3,
    Rarity.UR: 4,
}

def _select_cover_card_id(pack: PackDefinition) -> int:
    valid_cards = [card for card in pack.cards if card.rarity is not None and card.master_duel_id is not None]
    if not valid_cards:
        raise ValueError(f"Pack {pack.key!r} has no usable cards for its shop icon.")
    card = max(valid_cards, key=lambda card: RARITY_PRIORITY[card.rarity]) # type: ignore
    return card.master_duel_id # type: ignore

def _build_card_list(pack: PackDefinition) -> dict[str, int]:
    result: dict[str, int] = {}
    for card in pack.cards:
        if card.master_duel_id is None:
            raise ValueError(f"Card {card.name!r} in pack {pack.key!r} has no Master Duel ID.")
        if card.rarity is None:
            raise ValueError(f"Card {card.name!r} in pack {pack.key!r} has no rarity.")
        key = str(card.master_duel_id)
        if key in result:
            raise ValueError(f"Pack {pack.key!r} contains duplicate Master Duel card ID {card.master_duel_id}.")
        result[key] = RARITY_TO_YGOMASTER[card.rarity]
    return result

def _build_pack_shop_item(pack: PackDefinition, pack_id: int) -> dict[str, object]:
    icon_card_id = _select_cover_card_id(pack)
    description = pack.description if pack.description else pack.name
    return {
        "packId": pack_id,
        "packType": (
            YGOMASTER_SELECTION_PACK_TYPE
        ),
        "secretType": 0,
        "nameTextId": pack.name,
        "descShortTextId": description,
        "descFullTextId": description,
        "pack_card_num": pack.booster_size,
        "subCategory": 1,
        "productType": 1,
        "iconMrk": icon_card_id,
        "iconType": YGOMASTER_CARD_THUMB_ICON_TYPE,
        "iconData": str(icon_card_id),
        "preview": [
            {
                "type": 1,
                "mrk": icon_card_id,
            }
        ],
        "cardList": _build_card_list(pack),
        "price": DEFAULT_PACK_PRICE,
        "priceX10": DEFAULT_PACK_PRICE_X10,
    }

def build_shop_export(project: ProjectDefinition, pack_ids: dict[str, int]) -> dict[str, object]:
    pack_shop: dict[str, object] = {}

    for pack in project.packs:
        try:
            pack_id = pack_ids[pack.key]
        except KeyError as exc:
            raise ValueError(f"No YgoMaster pack ID assigned to pack {pack.key!r}.") from exc
        
        shop_id = get_pack_shop_id(pack_id)

        pack_shop[str(shop_id)] = (_build_pack_shop_item(pack, pack_id))

    return {
        "PackShop": pack_shop,
    }

def build_main_shop_settings_patch() -> dict[str, object]:
    return {
        "PerPackRarities": True,
    }