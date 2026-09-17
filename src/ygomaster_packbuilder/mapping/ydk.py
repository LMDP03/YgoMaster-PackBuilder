from pathlib import Path

from ygomaster_packbuilder.domain import Card

def load_ydk_mapping(file_path: str | Path) -> dict[int, int]:
    mapping: dict[int, int] = {}
    with open(file_path, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) != 2:
                raise ValueError(f"Invalid YdkIds.txt line {line_number}: expected 2 values, found {len(parts)}.")
            try:
                ydk_id = int(parts[0])
                master_duel_id = int(parts[1])
            except ValueError as exc:
                raise ValueError(f"Invalid numeric value in YdkIds.txt at line {line_number}.") from exc
            if ydk_id in mapping:
                raise ValueError(f"Duplicate YDK ID {ydk_id} at line {line_number}.")
            mapping[ydk_id] = master_duel_id
    return mapping

def resolve_card_master_duel_id(card: Card, mapping: dict[int, int]) -> bool:
    master_duel_id = mapping.get(card.ydk_id)
    if master_duel_id is None:
        return False
    card.master_duel_id = master_duel_id
    return True

def resolve_cards_master_duel_ids(cards: list[Card], mapping: dict[int, int]) -> list[Card]:
    unresolved_cards: list[Card] = []
    for card in cards:
        if not resolve_card_master_duel_id(card, mapping):
            unresolved_cards.append(card)
    return unresolved_cards