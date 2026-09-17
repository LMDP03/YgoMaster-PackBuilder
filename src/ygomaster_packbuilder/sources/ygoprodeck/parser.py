from typing import Any

from .models import YgoProDeckPackCard, YgoProDeckPackData

def _require_field(row: dict[str, Any], field: str, index: int) -> Any:
    if field not in row:
        raise ValueError(f"Missing field '{field}' in YGOPRODeck response row {index}.")
    return row[field]

def _validate_pack_metadata(row: dict[str, Any], reference: dict[str, Any], index: int) -> None:
    fields = (
        "pack_name",
        "pack_description",
        "username",
        "img_url",
    )
    for field in fields:
        if row[field] != _require_field(reference, field, index):
            raise ValueError(f"Inconsistent YGOPRODeck pack metadata at row {index}: field '{field}' differs from the first row.")

def _parse_card(row: dict[str, Any], index: int) -> YgoProDeckPackCard:
    name = _require_field(row, "name", index)
    raw_id = _require_field(row, "id", index)
    try:
        ydk_id = int(raw_id)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid YDK ID at row {index}: {row.get('id')!r}") from exc
    card_type = _require_field(row, "type", index)
    source_rarity = _require_field(row, "card_rarity", index)
    
    return YgoProDeckPackCard(
        name=name,
        ydk_id=ydk_id,
        card_type=card_type,
        source_rarity=source_rarity
    )

def parse_custom_pack(external_id: str, data: list[dict[str, Any]]) -> YgoProDeckPackData:
    if not data:
        raise ValueError(f"YGOPRODeck custom pack '{external_id}' returned no cards.")
    
    reference = data[0]
    pack_name = _require_field(reference, "pack_name", 0)
    pack_description = _require_field(reference, "pack_description", 0)
    creator = _require_field(reference, "username", 0)
    raw_image_id = _require_field(reference, "img_url", 0)
    image_id = str(raw_image_id)

    cards: list[YgoProDeckPackCard] = []
    for index, row in enumerate(data):
        _validate_pack_metadata(row, reference, index)
        cards.append(_parse_card(row, index))

    return YgoProDeckPackData(
        external_id=external_id,
        name=pack_name,
        description=pack_description,
        creator=creator,
        image_id=image_id,
        cards=cards
    )
