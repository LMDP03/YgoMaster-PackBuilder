from pathlib import Path
from typing import Any

import yaml

from ygomaster_packbuilder.domain import Card, Rarity

def load_rarity_mapping(file_path: Path) -> dict[str, Rarity]:
    if not file_path.exists():
        raise FileNotFoundError(f"Rarity mapping file not found: {file_path}")
    with file_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("Rarity mapping root must be a mapping.")
    raw_mapping = data["rarities"]
    mapping: dict[str, Rarity] = {}
    for key, value in raw_mapping.items():
        try:
            mapping[key] = Rarity(value)
        except ValueError as e:
            raise ValueError(f"Invalid rarity value for key '{key}': {value}") from e
    return mapping

def normalize_card_rarity(card: Card, rarity_mapping: dict[str, Rarity]) -> None:
    source_rarity = card.source_rarity
    if source_rarity not in rarity_mapping:
        raise ValueError(f"Unsupported source rarity: {source_rarity!r}.")
    card.rarity = rarity_mapping[source_rarity]

def normalize_cards(cards: list[Card], rarity_mapping: dict[str, Rarity]) -> None:
    for card in cards:
        normalize_card_rarity(card, rarity_mapping)