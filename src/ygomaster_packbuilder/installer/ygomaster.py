from dataclasses import dataclass
from pathlib import Path
import json
import re
import shutil

from ygomaster_packbuilder.domain import ProjectDefinition
from ygomaster_packbuilder.validation import validate_ygomaster_build

from .state import (
    INSTALL_STATE_VERSION,
    ManagedFileState,
    YgoMasterInstallationState,
    get_backup_path,
    get_install_state_dir,
    load_install_state,
    save_install_state,
    sha256_bytes,
)

BUILD_FILENAME = "ygomaster-packbuilder.json"
SHOP_SETTINGS_PATCH_FILENAME = "ShopSettings.patch.json"
SHOP_RELATIVE_PATH = f"Data/Shop/{BUILD_FILENAME}"
ODDS_RELATIVE_PATH = f"Data/ShopPackOdds/{BUILD_FILENAME}"
MANAGED_RELATIVE_PATHS = (SHOP_RELATIVE_PATH, ODDS_RELATIVE_PATH)

_PER_PACK_RARITIES_PATTERN = re.compile(
    r'("PerPackRarities"\s*:\s*)(true|false)',
    re.IGNORECASE,
)
_INSERTED_PER_PACK_RARITIES_PATTERN = re.compile(
    r'(?m)^[ \t]*"PerPackRarities"\s*:\s*true\s*,[ \t]*\r?\n'
)

@dataclass(slots=True, frozen=True)
class YgoMasterInstallResult:
    ygomaster_dir: Path
    data_dir: Path
    shop_file: Path
    shop_pack_odds_file: Path
    main_shop_file: Path
    changed_files: tuple[Path, ...]

@dataclass(slots=True, frozen=True)
class YgoMasterUninstallResult:
    ygomaster_dir: Path
    changed_files: tuple[Path, ...]
    removed_files: tuple[Path, ...]
    restored_files: tuple[Path, ...]

class YgoMasterInstallError(RuntimeError):
    pass

def _write_bytes_atomic_if_changed(file_path: Path, content: bytes) -> bool:
    if file_path.is_file() and file_path.read_bytes() == content:
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

def _decode_main_shop(original: bytes) -> tuple[str, str]:
    encoding = "utf-8-sig" if original.startswith(b"\xef\xbb\xbf") else "utf-8"
    try:
        return original.decode(encoding), encoding
    except UnicodeDecodeError as exc:
        raise YgoMasterInstallError("Shop.json is not valid UTF-8.") from exc

def _get_per_pack_rarities(text: str) -> bool | None:
    matches = list(_PER_PACK_RARITIES_PATTERN.finditer(text))
    if len(matches) > 1:
        raise YgoMasterInstallError("Shop.json contains multiple \"PerPackRarities\" settings.")
    if len(matches) == 1:
        return matches[0].group(2).lower() == "true"
    if '"PerPackRarities"' in text:
        raise YgoMasterInstallError("Shop.json contains an invalid \"PerPackRarities\" setting.")
    return None

def _patch_per_pack_rarities(text: str) -> str:
    current = _get_per_pack_rarities(text)
    if current is True:
        return text
    if current is False:
        return _PER_PACK_RARITIES_PATTERN.sub(r"\g<1>true", text, count=1)
    stripped = text.lstrip()
    if not stripped.startswith("{"):
        raise YgoMasterInstallError("Shop.json does not appear to contain a JSON object.")
    newline = "\r\n" if "\r\n" in text else "\n"
    indent_match = re.search(r'\r?\n([ \t]+)"', text)
    indent = indent_match.group(1) if indent_match else "    "
    root_index = text.find("{")
    insertion = newline + indent + '"PerPackRarities": true,'
    return text[:root_index + 1] + insertion + text[root_index + 1:]

def _restore_per_pack_rarities(text: str, previous: bool | None) -> str:
    current = _get_per_pack_rarities(text)
    if previous is True:
        return text
    if previous is False:
        if current is False:
            return text
        if current is True:
            return _PER_PACK_RARITIES_PATTERN.sub(r"\g<1>false", text, count=1)
        raise YgoMasterInstallError("PerPackRarities was removed after installation; refusing automatic restore.")
    if current is None:
        return text
    if current is False:
        raise YgoMasterInstallError("PerPackRarities was manually changed after installation; refusing automatic restore.")
    restored, count = _INSERTED_PER_PACK_RARITIES_PATTERN.subn("", text, count=1)
    if count != 1:
        raise YgoMasterInstallError("Could not safely remove the PerPackRarities setting added by PackBuilder.")
    return restored

def _patch_main_shop_file(original: bytes) -> bytes:
    text, encoding = _decode_main_shop(original)
    return _patch_per_pack_rarities(text).encode(encoding)

def _restore_main_shop_file(original: bytes, previous: bool | None) -> bytes:
    text, encoding = _decode_main_shop(original)
    return _restore_per_pack_rarities(text, previous).encode(encoding)

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
    return ygomaster_dir, data_dir, main_shop_file

def _require_valid_build(project: ProjectDefinition, pack_ids: dict[str, int], build_dir: Path) -> None:
    report = validate_ygomaster_build(project, pack_ids, build_dir)
    if report.is_valid:
        return
    details = "\n".join(f"- {issue.code}: {issue.message}" for issue in report.errors)
    raise YgoMasterInstallError(f"Cannot install an invalid build:\n{details}")

def _load_install_state(ygomaster_dir: Path) -> YgoMasterInstallationState | None:
    try:
        state = load_install_state(ygomaster_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise YgoMasterInstallError(f"Invalid installation state: {exc}") from exc
    if state is None:
        return None
    if set(state.managed_files) != set(MANAGED_RELATIVE_PATHS):
        raise YgoMasterInstallError("Installation state contains an unexpected managed file set.")
    for key, managed in state.managed_files.items():
        if managed.relative_path != key:
            raise YgoMasterInstallError(f"Managed file state path mismatch for {key!r}.")
    return state

def _verify_managed_file(ygomaster_dir: Path, state: ManagedFileState) -> None:
    target = ygomaster_dir / state.relative_path
    if not target.is_file():
        return
    if sha256_bytes(target.read_bytes()) != state.installed_sha256:
        raise YgoMasterInstallError(f"Managed file was modified after installation: {target}")

def _backup_preexisting_file(ygomaster_dir: Path, relative_path: str) -> bool:
    target = ygomaster_dir / relative_path
    if not target.is_file():
        return False
    backup = get_backup_path(ygomaster_dir, relative_path)
    _write_bytes_atomic_if_changed(backup, target.read_bytes())
    return True

def install_ygomaster_build(project: ProjectDefinition, pack_ids: dict[str, int], build_dir: str | Path, ygomaster_dir: str | Path) -> YgoMasterInstallResult:
    build_dir = Path(build_dir)
    _require_valid_build(project, pack_ids, build_dir)
    ygomaster_dir, data_dir, main_shop_file = _resolve_target(ygomaster_dir)

    source_shop = build_dir / "Shop" / BUILD_FILENAME
    source_odds = build_dir / "ShopPackOdds" / BUILD_FILENAME
    source_patch = build_dir / SHOP_SETTINGS_PATCH_FILENAME
    target_shop = ygomaster_dir / SHOP_RELATIVE_PATH
    target_odds = ygomaster_dir / ODDS_RELATIVE_PATH

    shop_content = source_shop.read_bytes()
    odds_content = source_odds.read_bytes()
    patch_data = json.loads(source_patch.read_text(encoding="utf-8"))
    if patch_data != {"PerPackRarities": True}:
        raise YgoMasterInstallError("Unsupported Shop settings patch.")

    original_main_shop = main_shop_file.read_bytes()
    patched_main_shop = _patch_main_shop_file(original_main_shop)
    main_shop_text, _ = _decode_main_shop(original_main_shop)

    previous_state = _load_install_state(ygomaster_dir)
    if previous_state is not None:
        for managed in previous_state.managed_files.values():
            _verify_managed_file(ygomaster_dir, managed)
        per_pack_rarities_before = previous_state.per_pack_rarities_before
        preexisting = {key: value.preexisting for key, value in previous_state.managed_files.items()}
    else:
        per_pack_rarities_before = _get_per_pack_rarities(main_shop_text)
        preexisting = {
            relative_path: _backup_preexisting_file(ygomaster_dir, relative_path)
            for relative_path in MANAGED_RELATIVE_PATHS
        }

    contents = {
        SHOP_RELATIVE_PATH: shop_content,
        ODDS_RELATIVE_PATH: odds_content,
    }
    new_state = YgoMasterInstallationState(
        version=INSTALL_STATE_VERSION,
        per_pack_rarities_before=per_pack_rarities_before,
        managed_files={
            relative_path: ManagedFileState(
                relative_path=relative_path,
                preexisting=preexisting[relative_path],
                installed_sha256=sha256_bytes(content),
            )
            for relative_path, content in contents.items()
        },
    )

    changed_files: list[Path] = []
    if _write_bytes_atomic_if_changed(target_shop, shop_content):
        changed_files.append(target_shop)
    if _write_bytes_atomic_if_changed(target_odds, odds_content):
        changed_files.append(target_odds)
    if _write_bytes_atomic_if_changed(main_shop_file, patched_main_shop):
        changed_files.append(main_shop_file)
    if previous_state != new_state:
        save_install_state(new_state, ygomaster_dir)

    return YgoMasterInstallResult(
        ygomaster_dir=ygomaster_dir,
        data_dir=data_dir,
        shop_file=target_shop,
        shop_pack_odds_file=target_odds,
        main_shop_file=main_shop_file,
        changed_files=tuple(changed_files),
    )

def uninstall_ygomaster_build(ygomaster_dir: str | Path) -> YgoMasterUninstallResult:
    ygomaster_dir, _, main_shop_file = _resolve_target(ygomaster_dir)
    state = _load_install_state(ygomaster_dir)
    if state is None:
        raise YgoMasterInstallError("No PackBuilder installation state was found.")

    for managed in state.managed_files.values():
        _verify_managed_file(ygomaster_dir, managed)
        if managed.preexisting and not get_backup_path(ygomaster_dir, managed.relative_path).is_file():
            raise YgoMasterInstallError(f"Missing installation backup: {get_backup_path(ygomaster_dir, managed.relative_path)}")

    restored_main_shop = _restore_main_shop_file(
        main_shop_file.read_bytes(),
        state.per_pack_rarities_before,
    )

    changed_files: list[Path] = []
    removed_files: list[Path] = []
    restored_files: list[Path] = []

    for managed in state.managed_files.values():
        target = ygomaster_dir / managed.relative_path
        if managed.preexisting:
            backup = get_backup_path(ygomaster_dir, managed.relative_path)
            if _write_bytes_atomic_if_changed(target, backup.read_bytes()):
                changed_files.append(target)
                restored_files.append(target)
        elif target.is_file():
            target.unlink()
            changed_files.append(target)
            removed_files.append(target)

    if _write_bytes_atomic_if_changed(main_shop_file, restored_main_shop):
        changed_files.append(main_shop_file)
        restored_files.append(main_shop_file)

    shutil.rmtree(get_install_state_dir(ygomaster_dir))
    return YgoMasterUninstallResult(
        ygomaster_dir=ygomaster_dir,
        changed_files=tuple(changed_files),
        removed_files=tuple(removed_files),
        restored_files=tuple(restored_files),
    )
