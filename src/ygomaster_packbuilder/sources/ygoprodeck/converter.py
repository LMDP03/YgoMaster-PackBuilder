from ygomaster_packbuilder.domain import Card

from .models import YgoProDeckPackCard, YgoProDeckPackData

def _convert_card(card: YgoProDeckPackCard) -> Card:
    return Card(
        name=card.name,
        ydk_id=card.ydk_id,
        source_rarity=card.source_rarity
    )

def convert_pack_cards_to_domain(pack: YgoProDeckPackData) -> list[Card]:
    return [_convert_card(card) for card in pack.cards]