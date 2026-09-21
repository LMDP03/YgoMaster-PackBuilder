from dataclasses import dataclass
from pathlib import Path
import hashlib
import json

INSTALL_STATE_VERSION = 1
INSTALL_STATE_DIRNAME = ".ygomaster-packbuilder"
INSTALL_STATE_FILENAME = "install-state.json"
BACKUP_DIRNAME = "backup"

@dataclass(slots=True, frozen=True)
class ManagedFileState:
    relative_path: str
    preexisting: bool
    installed_sha256: str

@dataclass(slots=True)
class YgoMasterInstallationState:
    version: int
    per_pack_rarities_before: bool | None
    managed_files: dict[str, ManagedFileState]

def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

def get_install_state_dir(ygomaster_dir: Path) -> Path:
    return ygomaster_dir / INSTALL_STATE_DIRNAME

def get_install_state_path(ygomaster_dir: Path) -> Path:
    return get_install_state_dir(ygomaster_dir) / INSTALL_STATE_FILENAME

def _validate_relative_path(relative_path: str) -> None:
    path = Path(relative_path)
    if not relative_path or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Invalid managed relative path: {relative_path!r}.")

def get_backup_path(ygomaster_dir: Path, relative_path: str) -> Path:
    _validate_relative_path(relative_path)
    return get_install_state_dir(ygomaster_dir) / BACKUP_DIRNAME / relative_path

def _validate_state(state: YgoMasterInstallationState) -> None:
    if state.version != INSTALL_STATE_VERSION:
        raise ValueError(f"Unsupported installation state version: {state.version!r}.")
    if state.per_pack_rarities_before is not None and not isinstance(state.per_pack_rarities_before, bool):
        raise ValueError("Invalid per_pack_rarities_before.")
    for key, managed in state.managed_files.items():
        if not isinstance(key, str) or not key:
            raise ValueError("Managed file keys must be non-empty strings.")
        _validate_relative_path(managed.relative_path)
        if not isinstance(managed.preexisting, bool):
            raise ValueError(f"Invalid preexisting flag for {key!r}.")
        if len(managed.installed_sha256) != 64 or any(c not in "0123456789abcdef" for c in managed.installed_sha256.lower()):
            raise ValueError(f"Invalid installed_sha256 for {key!r}.")

def save_install_state(state: YgoMasterInstallationState, ygomaster_dir: Path) -> None:
    _validate_state(state)
    state_path = get_install_state_path(ygomaster_dir)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": state.version,
        "per_pack_rarities_before": state.per_pack_rarities_before,
        "managed_files": {
            key: {
                "relative_path": value.relative_path,
                "preexisting": value.preexisting,
                "installed_sha256": value.installed_sha256,
            }
            for key, value in sorted(state.managed_files.items())
        },
    }
    temp_path = state_path.with_name(state_path.name + ".tmp")
    try:
        temp_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        temp_path.replace(state_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

def load_install_state(ygomaster_dir: Path) -> YgoMasterInstallationState | None:
    state_path = get_install_state_path(ygomaster_dir)
    if not state_path.is_file():
        return None
    data = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Installation state root must be an object.")
    raw_managed = data.get("managed_files")
    if not isinstance(raw_managed, dict):
        raise ValueError("managed_files must be an object.")
    managed: dict[str, ManagedFileState] = {}
    for key, value in raw_managed.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            raise ValueError(f"Invalid managed file state for {key!r}.")
        try:
            managed[key] = ManagedFileState(
                relative_path=value["relative_path"],
                preexisting=value["preexisting"],
                installed_sha256=value["installed_sha256"],
            )
        except KeyError as exc:
            raise ValueError(f"Missing field in managed file state {key!r}: {exc.args[0]}.") from exc
    state = YgoMasterInstallationState(
        version=data.get("version", 0),
        per_pack_rarities_before=data.get("per_pack_rarities_before"),
        managed_files=managed,
    )
    _validate_state(state)
    return state
