"""Read the card IDs available in the installed YgoMaster server catalog."""

import json
from pathlib import Path


def load_master_duel_card_catalog(file_path: str | Path) -> set[int]:
    """Return MD card IDs from Data/CardList.json; rarity values are not league rarities."""
    file_path = Path(file_path)
    try:
        with file_path.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid YgoMaster card catalog {file_path}: {exc}") from exc

    if not isinstance(data, dict) or not data:
        raise ValueError(f"Invalid {file_path}: expected a non-empty object of card IDs and rarities.")

    card_ids: set[int] = set()
    for raw_id, rarity in data.items():
        if not isinstance(raw_id, str) or not raw_id.isdecimal() or int(raw_id) <= 0:
            raise ValueError(f"Invalid card ID {raw_id!r} in {file_path}.")
        if type(rarity) is not int or rarity not in (1, 2, 3, 4):
            raise ValueError(f"Invalid rarity for card ID {raw_id!r} in {file_path}: {rarity!r}.")
        card_ids.add(int(raw_id))
    return card_ids
