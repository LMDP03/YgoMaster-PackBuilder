from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ygomaster_packbuilder.domain import Card, Rarity, PackType

@dataclass(slots=True)
class RarityMapping:
    rarities: dict[str, Rarity]
    overrides: dict[PackType, dict[str, Rarity]]

def _parse_rarity_map(raw_mapping: dict[str, Any], context: str) -> dict[str, Rarity]:
    mapping: dict[str, Rarity] = {}
    for key, value in raw_mapping.items():
        try:
            mapping[key] = Rarity(value)
        except ValueError as e:
            raise ValueError(f"Invalid rarity value for key '{key}' in {context}: {value}") from e
    return mapping

def load_rarity_mapping(file_path: Path) -> RarityMapping:
    if not file_path.exists():
        raise FileNotFoundError(f"Rarity mapping file not found: {file_path}")
    with file_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("Rarity mapping root must be a mapping.")
    raw_rarities = data.get("rarities")
    if not isinstance(raw_rarities, dict):
        raise ValueError("Rarities must be a mapping.")
    rarities = _parse_rarity_map(raw_rarities, "rarities")
    raw_overrides = data.get("overrides", {})
    if not isinstance(raw_overrides, dict):
        raise ValueError("Overrides must be a mapping.")
    overrides: dict[PackType, dict[str, Rarity]] = {}
    for raw_pack_type, raw_mapping in raw_overrides.items():
        try:
            pack_type = PackType(raw_pack_type)
        except ValueError as e:
            raise ValueError(f"Unknown pack type in rarity override: {raw_pack_type!r}") from e
        if not isinstance(raw_mapping, dict):
            raise ValueError(f"Rarity override for '{raw_pack_type!r}' must be a mapping.")
        overrides[pack_type] = _parse_rarity_map(raw_mapping, f"overrides.{raw_pack_type}")
    return RarityMapping(rarities=rarities, overrides=overrides)

def resolve_rarity(source_rarity: str, pack_type: PackType, rarity_mapping: RarityMapping) -> Rarity:
    pack_overrides = rarity_mapping.overrides.get(pack_type, {})
    if source_rarity in pack_overrides:
        return pack_overrides[source_rarity]
    if source_rarity in rarity_mapping.rarities:
        return rarity_mapping.rarities[source_rarity]
    raise ValueError(f"Unsupported source rarity {source_rarity!r} for pack type {pack_type!r}.")

def normalize_card_rarity(card: Card, rarity_mapping: RarityMapping, pack_type: PackType) -> None:
    source_rarity = card.source_rarity
    if source_rarity not in rarity_mapping.rarities:
        raise ValueError(f"Unsupported source rarity: {source_rarity!r}.")
    card.rarity = resolve_rarity(source_rarity, pack_type, rarity_mapping)

def normalize_cards(cards: list[Card], rarity_mapping: RarityMapping, pack_type: PackType) -> None:
    for card in cards:
        normalize_card_rarity(card, rarity_mapping, pack_type)