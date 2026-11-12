#!/usr/bin/env python3
"""Keep only cards used by one YgoMaster deck in a player's collection.

By default, this script is READ ONLY. Pass --apply to modify Player.json.
Stop the YgoMaster server before applying changes.

Examples:
    python3 filter_ygo_collection.py --player /path/to/Player.json --deck '/path/to/Might from shine and stone.json'
    python3 filter_ygo_collection.py --player /path/to/Player.json --deck '/path/to/Might from shine and stone.json' --apply
"""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import tempfile


def read_json_object(path: Path, label: str) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read {label} ({path}): {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return data


def get_deck_ids(deck: dict) -> set[int]:
    keep = set()
    for section in ("m", "e", "s"):  # Main, Extra, Side
        block = deck.get(section)
        if not isinstance(block, dict) or not isinstance(block.get("ids"), list):
            raise ValueError(f"Deck section '{section}.ids' must be an array")
        ids = block["ids"]
        if any(type(card_id) is not int or card_id <= 0 for card_id in ids):
            raise ValueError(f"Deck section '{section}.ids' contains an invalid card ID")
        rarities = block.get("r")
        if not isinstance(rarities, list) or len(rarities) != len(ids):
            raise ValueError(f"Deck section '{section}.r' must align with its IDs")
        keep.update(ids)
    if not keep:
        raise ValueError("The deck has no cards: refusing to empty the player's collection")
    return keep


def filter_player(player: dict, keep: set[int]) -> tuple[dict, list[int], list[int]]:
    cards = player.get("Cards")
    if not isinstance(cards, dict):
        raise ValueError("Player.json has no valid 'Cards' object")
    if any(not isinstance(card_id, str) or not card_id.isdecimal() or int(card_id) <= 0 for card_id in cards):
        raise ValueError("Player.json has non-numeric card keys: refusing to edit")
    owned = {int(card_id) for card_id in cards}
    removed = sorted(owned - keep)
    missing = sorted(keep - owned)
    # No other player data is changed; all copies/rarities for retained IDs are preserved.
    new_player = {**player, "Cards": {card_id: info for card_id, info in cards.items() if int(card_id) in keep}}
    return new_player, removed, missing


def apply_with_backup(player_path: Path, new_player: dict) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_path = player_path.with_name(f"{player_path.name}.bak-{stamp}")
    # Same-directory copy is a full, byte-for-byte backup before any change.
    shutil.copy2(player_path, backup_path)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=player_path.parent,
            prefix=f".{player_path.name}.", suffix=".tmp", delete=False,
        ) as tmp:
            temp_path = Path(tmp.name)
            json.dump(new_player, tmp, indent=2, ensure_ascii=False)
            tmp.write("\n")
            tmp.flush()
            os.fsync(tmp.fileno())
        shutil.copymode(player_path, temp_path)
        os.replace(temp_path, player_path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
    return backup_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--player", required=True, type=Path, help="Path to the actual server Player.json")
    parser.add_argument("--deck", required=True, type=Path, help="YgoMaster deck JSON containing m/e/s sections")
    parser.add_argument("--apply", action="store_true", help="Back up and update Player.json; otherwise only preview")
    args = parser.parse_args()

    try:
        if not args.player.is_file() or not args.deck.is_file():
            raise ValueError("Player and deck paths must both refer to existing files")
        if args.player.resolve() == args.deck.resolve():
            raise ValueError("The player and deck paths must be different")
        player = read_json_object(args.player, "player")
        deck = read_json_object(args.deck, "deck")
        keep = get_deck_ids(deck)
        new_player, removed, missing = filter_player(player, keep)

        print(f"Player file : {args.player.resolve()}")
        print(f"Deck file   : {args.deck.resolve()}")
        print(f"Owned IDs   : {len(player['Cards'])}")
        print(f"Deck IDs    : {len(keep)} unique")
        print(f"Kept IDs    : {len(new_player['Cards'])}")
        print(f"Removed IDs : {len(removed)}")
        print(f"Remove list : {', '.join(map(str, removed)) or '(none)'}")
        if missing:
            print(f"Deck cards not owned (not added): {', '.join(map(str, missing))}")
        if not args.apply:
            print("DRY RUN: nothing was changed. Add --apply to save after stopping YgoMaster.")
            return 0
        if not removed:
            print("No cards need removal. File was not changed.")
            return 0
        print("IMPORTANT: stop the YgoMaster server and all clients before continuing.")
        answer = input("Type RIMUOVI to create a backup and update this Player.json: ").strip()
        if answer != "RIMUOVI":
            print("Cancelled: no changes made.")
            return 0
        backup = apply_with_backup(args.player, new_player)
        print(f"Updated Player.json. Original backup: {backup}")
        return 0
    except (ValueError, OSError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
