from dataclasses import dataclass
from pathlib import Path
import json

from ygomaster_packbuilder.domain import ProjectDefinition

from .odds import build_pack_odds_export
from .shop import build_main_shop_settings_patch, build_shop_export

BUILD_FILENAME = "ygomaster-packbuilder.json"
SHOP_SETTINGS_PATCH_FILENAME = "ShopSettings.patch.json"

@dataclass(slots=True, frozen=True)
class YgoMasterBuildArtifacts:
    root: Path
    shop: Path
    shop_pack_odds: Path
    shop_settings_patch: Path

def _serialize_json(data: object) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"

def _write_text_atomic(file_path: Path, content: str) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    try:
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(file_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

def write_ygomaster_build(
    project: ProjectDefinition,
    pack_ids: dict[str, int],
    build_dir: str | Path,
) -> YgoMasterBuildArtifacts:
    build_dir = Path(build_dir)
    if build_dir.exists() and not build_dir.is_dir():
        raise ValueError(f"Build path is not a directory: {build_dir}")

    shop_data = build_shop_export(project, pack_ids)
    odds_data = build_pack_odds_export(project, pack_ids)
    settings_patch = build_main_shop_settings_patch()

    shop_path = build_dir / "Shop" / BUILD_FILENAME
    odds_path = build_dir / "ShopPackOdds" / BUILD_FILENAME
    settings_patch_path = build_dir / SHOP_SETTINGS_PATCH_FILENAME

    serialized_shop = _serialize_json(shop_data)
    serialized_odds = _serialize_json(odds_data)
    serialized_patch = _serialize_json(settings_patch)

    _write_text_atomic(shop_path, serialized_shop)
    _write_text_atomic(odds_path, serialized_odds)
    _write_text_atomic(settings_patch_path, serialized_patch)

    return YgoMasterBuildArtifacts(
        root=build_dir,
        shop=shop_path,
        shop_pack_odds=odds_path,
        shop_settings_patch=settings_patch_path
    )