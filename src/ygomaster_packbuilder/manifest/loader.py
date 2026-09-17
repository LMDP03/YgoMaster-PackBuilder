from pathlib import Path
from typing import Any

import yaml

from .models import ManifestPack, ManifestPackSource, ManifestPlayer, ManifestProjectSettings, ManifestSharedPack, ProjectManifest

def _load_yaml(file_path: Path) -> dict[str, Any]:
    if not file_path.exists():
        raise FileNotFoundError(f"YAML file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        raise ValueError(f"Failed to load YAML file: {file_path}")
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must be a mapping: {file_path}")
    return data

def _parse_source(data: dict[str, Any]) -> ManifestPackSource:
    provider = data["provider"]
    if not provider:
        raise ValueError("Field 'provider' must be provided")
    if not isinstance(provider, str):
        raise ValueError("'provider' must be a string")
    
    external_id = data["external_id"]
    if not external_id:
        raise ValueError("Field 'external_id' must be provided")
    if not isinstance(external_id, (str, int)):
        raise ValueError("'external_id' must be a string or an integer")
    
    return ManifestPackSource(
        provider=provider,
        external_id=str(external_id)
    )

def _parse_pack(data: dict[str, Any]) -> ManifestPack:
    key = data["key"]
    if not key:
        raise ValueError("Field 'key' must be provided")
    if not isinstance(key, str):
        raise ValueError("'key' must be a string")
    
    source_data = data["source"]
    if not source_data:
        raise ValueError("Field 'source' must be provided")
    if not isinstance(source_data, dict):
        raise ValueError("'source' must be a mapping")
    source = _parse_source(source_data)

    opening_policy = data.get("opening_policy")

    return ManifestPack(
        key=key,
        source=source,
        opening_policy=opening_policy
    )

def _parse_player(data: dict[str, Any]) -> ManifestPlayer:
    key = data["key"]
    if not key:
        raise ValueError("Field 'key' must be provided")
    if not isinstance(key, str):
        raise ValueError("'key' must be a string")
    
    display_name = data["display_name"]
    if not display_name:
        raise ValueError("Field 'display_name' must be provided")
    if not isinstance(display_name, str):
        raise ValueError("'display_name' must be a string")

    main_pack_data = data["main_pack"]
    if not main_pack_data:
        raise ValueError("Field 'main_pack' must be provided")
    if not isinstance(main_pack_data, dict):
        raise ValueError("'main_pack' must be a mapping")
    main_pack = _parse_pack(main_pack_data)

    mini_packs_data = data.get("mini_packs", [])
    if not isinstance(mini_packs_data, list):
        raise ValueError("'mini_packs' must be a list")
    mini_packs = [_parse_pack(pack_data) for pack_data in mini_packs_data]

    return ManifestPlayer(
        key=key,
        display_name=display_name,
        main_pack=main_pack,
        mini_packs=mini_packs
    )

def _parse_shared_pack(data: dict[str, Any]) -> ManifestSharedPack:
    key = data["key"]
    if not key:
        raise ValueError("Field 'key' must be provided")
    if not isinstance(key, str):
        raise ValueError("'key' must be a string")

    pack_type = data["type"]
    if not pack_type:
        raise ValueError("Field 'type' must be provided")
    if not isinstance(pack_type, str):
        raise ValueError("'type' must be a string")

    source_data = data["source"]
    if not source_data:
        raise ValueError("Field 'source' must be provided")
    if not isinstance(source_data, dict):
        raise ValueError("'source' must be a mapping")
    source = _parse_source(source_data)

    opening_policy = data.get("opening_policy")

    return ManifestSharedPack(
        key=key,
        type=pack_type,
        source=source,
        opening_policy=opening_policy
    )

def _parse_project_settings(data: dict[str, Any]) -> ManifestProjectSettings:
    name = data["name"]
    if not name:
        raise ValueError("Field 'name' must be provided")
    if not isinstance(name, str):
        raise ValueError("'name' must be a string")

    default_opening_policy = data["default_opening_policy"]
    if not default_opening_policy:
        raise ValueError("Field 'default_opening_policy' must be provided")
    if not isinstance(default_opening_policy, str):
        raise ValueError("'default_opening_policy' must be a string")
    
    return ManifestProjectSettings(
        name=name,
        default_opening_policy=default_opening_policy
    )

def load_project_manifest(file_path: str | Path) -> ProjectManifest:
    file_path = Path(file_path)
    data = _load_yaml(file_path)

    settings_data = data["settings"]
    if not settings_data:
        raise ValueError("Field 'settings' must be provided")
    if not isinstance(settings_data, dict):
        raise ValueError("'settings' must be a mapping")
    settings = _parse_project_settings(settings_data)

    players_data = data["players"]
    if not players_data:
        raise ValueError("Field 'players' must be provided")
    if not isinstance(players_data, list):
        raise ValueError("'players' must be a list")
    players = [_parse_player(player_data) for player_data in players_data]
    
    shared_packs_data = data.get("shared_packs", [])
    if not isinstance(shared_packs_data, list):
        raise ValueError("'shared_packs' must be a list")
    shared_packs = [_parse_shared_pack(pack_data) for pack_data in shared_packs_data]

    return ProjectManifest(
        settings=settings,
        players=players,
        shared_packs=shared_packs
    )