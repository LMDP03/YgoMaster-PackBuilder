from dataclasses import dataclass
from pathlib import Path
import json
import re

from ygomaster_packbuilder.domain import ProjectDefinition
from ygomaster_packbuilder.validation import validate_ygomaster_build

BUILD_FILENAME = "ygomaster-packbuilder.json"
SHOP_SETTINGS_PATCH_FILENAME = "ShopSettings.patch.json"

_PER_PACK_RARITIES_PATTERN = re.compile(
    r'("PerPackRarities"\s*:\s*)'
    r'(true|false)',
    re.IGNORECASE,
)

@dataclass(slots=True, frozen=True)
class YgoMasterInstallResult:
    ygomaster_dir: Path
    data_dir: Path
    shop_file: Path
    shop_pack_odds_file: Path
    main_shop_file: Path
    changed_files: tuple[Path, ...]

class YgoMasterInstallError(RuntimeError):
    pass

def _write_bytes_atomic_if_changed(file_path: Path, content: bytes) -> bool:
    if file_path.is_file():
        if file_path.read_bytes() == content:
            return False
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_name(file_path.name + ".ygomaster-packbuilder.tmp")
    try:
        temp_path.write_bytes(content)
        temp_path.replace(file_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    return True

def _patch_per_pack_rarities(text: str) -> str:
    matches = list(_PER_PACK_RARITIES_PATTERN.finditer(text))
    if len(matches) > 1:
        raise YgoMasterInstallError("Shop.json contains multiple \"PerPackRarities\" settings.")
    if len(matches) == 1:
        return _PER_PACK_RARITIES_PATTERN.sub(r"\g<1>true", text, count=1)
    if '"PerPackRarities"' in text:
        raise YgoMasterInstallError("Shop.json contains an invalid \"PerPackRarities\" setting.")
    stripped = text.lstrip()
    if not stripped.startswith("{"):
        raise YgoMasterInstallError("Shop.json does not appear to contain a JSON object.")
    newline = "\r\n" if "\r\n" in text else "\n"
    indent_match = re.search(r'\r?\n([ \t]+)"', text)
    indent = indent_match.group(1) if indent_match else "    "
    root_index = text.find("{")
    insertion = newline + indent + '"PerPackRarities": true,'
    return text[:root_index + 1] + insertion + text[root_index + 1:]

def _patch_main_shop_file(original: bytes) -> bytes:
    has_bom = original.startswith(b"\xef\xbb\xbf")
    encoding = "utf-8-sig" if has_bom else "utf-8"
    try:
        text = original.decode(encoding)
    except UnicodeDecodeError as exc:
        raise YgoMasterInstallError("Shop.json is not valid UTF-8.") from exc
    patched = _patch_per_pack_rarities(text)
    return patched.encode(encoding)

def _resolve_target(ygomaster_dir: str | Path) -> tuple[Path, Path, Path]:
    ygomaster_dir = Path(ygomaster_dir)
    if not ygomaster_dir.is_dir():
        raise YgoMasterInstallError(f"YgoMaster directory does not exist: {ygomaster_dir}")
    data_dir = ygomaster_dir / "Data"
    if not data_dir.is_dir():
        raise YgoMasterInstallError(f"YgoMaster Data directory does not exist: {data_dir}")
    main_shop_file = data_dir / "Shop.json"
    if not main_shop_file.is_file():
        raise YgoMasterInstallError(f"YgoMaster Shop.json was not found: {main_shop_file}")
    return (ygomaster_dir, data_dir, main_shop_file)

def _require_valid_build(project: ProjectDefinition, pack_ids: dict[str, int], build_dir: Path) -> None:
    report = validate_ygomaster_build(project, pack_ids, build_dir)
    if report.is_valid:
        return
    details = "\n".join(f"- {issue.code}: {issue.message}" for issue in report.errors)
    raise YgoMasterInstallError(f"Cannot install an invalid build:\n{details}")

def install_ygomaster_build(project: ProjectDefinition, pack_ids: dict[str, int], build_dir: str | Path, ygomaster_dir: str | Path) -> YgoMasterInstallResult:
    build_dir = Path(build_dir)
    _require_valid_build(project, pack_ids, build_dir)

    (ygomaster_dir, data_dir, main_shop_file) = _resolve_target(ygomaster_dir)

    source_shop = build_dir / "Shop" / BUILD_FILENAME
    source_odds = build_dir / "ShopPackOdds" / BUILD_FILENAME
    source_patch = build_dir / SHOP_SETTINGS_PATCH_FILENAME

    target_shop = data_dir / "Shop" / BUILD_FILENAME
    target_odds = data_dir / "ShopPackOdds" / BUILD_FILENAME

    shop_content = source_shop.read_bytes()
    odds_content = source_odds.read_bytes()

    patch_data = json.loads(source_patch.read_text(encoding="utf-8"))
    if patch_data != {"PerPackRarities": True}:
        raise YgoMasterInstallError("Unsupported Shop settings patch.")
    
    original_main_shop = (main_shop_file.read_bytes())
    patched_main_shop = _patch_main_shop_file(original_main_shop)

    changed_files: list[Path] = []

    if _write_bytes_atomic_if_changed(target_shop, shop_content):
        changed_files.append(target_shop)
    if _write_bytes_atomic_if_changed(target_odds, odds_content):
        changed_files.append(target_odds)
    if _write_bytes_atomic_if_changed(main_shop_file, patched_main_shop):
        changed_files.append(main_shop_file)

    return YgoMasterInstallResult(
        ygomaster_dir=ygomaster_dir,
        data_dir=data_dir,
        shop_file=target_shop,
        shop_pack_odds_file=target_odds,
        main_shop_file=main_shop_file,
        changed_files=tuple(changed_files),
    )