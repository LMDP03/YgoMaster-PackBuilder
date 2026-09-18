from dataclasses import dataclass, field
from pathlib import Path
import json

from ygomaster_packbuilder.domain import ProjectDefinition

REGISTRY_VERSION = 1

PACK_ID_MIN = 9_000_000
PACK_ID_MAX = 9_999_999
PACK_SHOP_BASE_ID = 10_000_000

@dataclass(slots=True)
class YgoMasterIdRegistry:
    version: int = REGISTRY_VERSION
    next_pack_id: int = PACK_ID_MIN
    pack_ids: dict[str, int] = field(default_factory=dict)

def _validate_registry(registry: YgoMasterIdRegistry) -> None: 
    if registry.version != REGISTRY_VERSION:
        raise ValueError(f"Unsupported ID registry version {registry.version}.")
    
    if not (PACK_ID_MIN <= registry.next_pack_id <= PACK_ID_MAX + 1):
        raise ValueError(f"Invalid next_pack_id: {registry.next_pack_id}.")

    ids = list(registry.pack_ids.values())

    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate pack IDs found in the registry.")

    for key, pack_id in registry.pack_ids.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"Registry pack keys must be non-empty strings.")
        if not (PACK_ID_MIN <= pack_id <= PACK_ID_MAX):
            raise ValueError(f"Pack {key!r} has invalid YgoMaster ID {pack_id}.")

def load_id_registry(file_path: str | Path) -> YgoMasterIdRegistry:
    file_path = Path(file_path)
    if not file_path.exists():
        return YgoMasterIdRegistry()

    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError("ID registry root must be an object.")

    raw_pack_ids = data.get("pack_ids", {})
    if not isinstance(raw_pack_ids, dict):
        raise ValueError("'pack_ids' must be an object.")

    registry = YgoMasterIdRegistry(
        version=data.get("version", REGISTRY_VERSION),
        next_pack_id=data.get("next_pack_id", PACK_ID_MIN),
        pack_ids={str(key): value for key, value in raw_pack_ids.items()}
    )
    _validate_registry(registry)

    return registry

def save_id_registry(registry: YgoMasterIdRegistry, file_path: str | Path) -> None:
    _validate_registry(registry)

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True,)

    data = {
        "version": registry.version,
        "next_pack_id": registry.next_pack_id,
        "pack_ids": dict(sorted(registry.pack_ids.items()))
    }

    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    temp_path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    temp_path.replace(file_path)

def ensure_project_pack_ids(project: ProjectDefinition, registry: YgoMasterIdRegistry) -> dict[str, int]:
    _validate_registry(registry)

    pack_keys = [pack.key for pack in project.packs]
    if len(pack_keys) != len(set(pack_keys)):
        raise ValueError("Project contains duplicate pack keys.")
    missing_keys = sorted(key for key in pack_keys if key not in registry.pack_ids)
    used_ids = set(registry.pack_ids.values())
    next_id = max(registry.next_pack_id, PACK_ID_MIN)

    for key in missing_keys:
        while next_id in used_ids and next_id <= PACK_ID_MAX:
            next_id += 1
        if next_id > PACK_ID_MAX:
            raise ValueError("YgoMaster custom pack ID range exhausted.")
        registry.pack_ids[key] = next_id
        used_ids.add(next_id)
        next_id += 1

    registry.next_pack_id = next_id

    return {key: registry.pack_ids[key] for key in pack_keys}

def get_pack_shop_id(pack_id: int) -> int:
    if not PACK_ID_MIN <= pack_id <= PACK_ID_MAX:
        raise ValueError(f"Invalid custom pack ID: {pack_id}.")
    
    return PACK_SHOP_BASE_ID + pack_id