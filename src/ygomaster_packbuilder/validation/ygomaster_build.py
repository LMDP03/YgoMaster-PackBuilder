from pathlib import Path
import json

from ygomaster_packbuilder.domain import ProjectDefinition
from ygomaster_packbuilder.exporters.ygomaster import build_main_shop_settings_patch, build_pack_odds_export, build_shop_export

from .models import ValidationIssue, ValidationReport

BUILD_FILENAME = "ygomaster-packbuilder.json"
SHOP_SETTINGS_PATCH_FILENAME = "ShopSettings.patch.json"

_LOAD_FAILED = object()


def _add_error(report: ValidationReport, code: str, message: str, path: str) -> None:
    report.issues.append(
        ValidationIssue(
            code=code,
            message=message,
            path=path,
        )
    )

def _load_json(file_path: Path, report: ValidationReport) -> object:
    if not file_path.is_file():
        _add_error(
            report,
            code="build-file-missing",
            message=f"Required build file is missing: {file_path}.",
            path=str(file_path)
        )
        return _LOAD_FAILED
    try:
        with file_path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as exc:
        _add_error(
            report,
            code="build-invalid-json",
            message=f"Invalid JSON in {file_path}: {exc}.",
            path=str(file_path)
        )
        return _LOAD_FAILED

def _validate_shop_structure(data: object, file_path: Path, report: ValidationReport) -> None:
    if not isinstance(data, dict):
        _add_error(
            report,
            code="build-invalid-shop-root",
            message="Shop export root must be a JSON object.",
            path=str(file_path)
        )
        return
    pack_shop = data.get("PackShop")
    if not isinstance(pack_shop, dict):
        _add_error(
            report,
            code="build-invalid-pack-shop",
            message="Shop export must contain a PackShop object.",
            path=f"{file_path}.PackShop"
        )

def _validate_odds_structure(data: object, file_path: Path, report: ValidationReport) -> None:
    if not isinstance(data, list):
        _add_error(
            report,
            code="build-invalid-odds-root",
            message="ShopPackOdds export root must be a JSON array.",
            path=str(file_path)
        )

def _validate_patch_structure(data: object, file_path: Path, report: ValidationReport) -> None:
    if not isinstance(data, dict):
        _add_error(
            report,
            code="build-invalid-settings-patch-root",
            message="Shop settings patch root must be a JSON object.",
            path=str(file_path)
        )
        return
    if data.get("PerPackRarities") is not True:
        _add_error(
            report,
            code="build-per-pack-rarities-disabled",
            message="Shop settings patch must enable PerPackRarities.",
            path=f"{file_path}.PerPackRarities"
        )

def _validate_shop_odds_references(shop_data: object, odds_data: object, report: ValidationReport) -> None:
    if not isinstance(shop_data, dict):
        return
    pack_shop = shop_data.get("PackShop")
    if not isinstance(pack_shop, dict):
        return
    if not isinstance(odds_data, list):
        return
    shop_ids = {str(shop_id) for shop_id in pack_shop}
    odds_shop_ids: set[str] = set()
    for index, odds in enumerate(odds_data):
        if not isinstance(odds, dict):
            _add_error(
                report,
                code="build-invalid-odds-entry",
                message=f"Odds entry {index} must be a JSON object.",
                path=f"ShopPackOdds[{index}]"
            )
            continue
        pack_shop_ids = odds.get("packShopIds")
        if not isinstance(pack_shop_ids, list):
            _add_error(
                report,
                code="build-invalid-odds-pack-ids",
                message=f"Odds entry {index} must contain packShopIds.",
                path=f"ShopPackOdds[{index}].packShopIds"
            )
            continue
        for shop_id in pack_shop_ids:
            odds_shop_ids.add(str(shop_id))
    if shop_ids != odds_shop_ids:
        _add_error(
            report,
            code="build-shop-odds-reference-mismatch",
            message="PackShop IDs and ShopPackOdds references do not match.",
            path="build"
        )

def _validate_expected_content(actual: object, expected: object, code: str, label: str, path: Path, report: ValidationReport) -> None:
    if actual != expected:
        _add_error(
            report,
            code=code,
            message=f"{label} does not match the expected export.",
            path=str(path)
        )

def _validate_no_temp_files(build_dir: Path, report: ValidationReport) -> None:
    if not build_dir.is_dir():
        return
    for file_path in build_dir.rglob("*.tmp"):
        if file_path.is_file():
            _add_error(
                report,
                code="build-temp-file-present",
                message=f"Temporary build file found: {file_path}.",
                path=str(file_path)
            )

def validate_ygomaster_build(project: ProjectDefinition, pack_ids: dict[str, int], build_dir: str | Path) -> ValidationReport:
    report = ValidationReport()
    build_dir = Path(build_dir)
    shop_path = build_dir / "Shop" / BUILD_FILENAME
    odds_path = build_dir / "ShopPackOdds" / BUILD_FILENAME
    patch_path = build_dir / SHOP_SETTINGS_PATCH_FILENAME
    shop_data = _load_json(shop_path, report)
    odds_data = _load_json(odds_path, report)
    patch_data = _load_json(patch_path, report)
    if shop_data is not _LOAD_FAILED:
        _validate_shop_structure(shop_data, shop_path, report)
    if odds_data is not _LOAD_FAILED:
        _validate_odds_structure(odds_data, odds_path, report)
    if patch_data is not _LOAD_FAILED:
        _validate_patch_structure(patch_data, patch_path, report)
    if shop_data is not _LOAD_FAILED and odds_data is not _LOAD_FAILED:
        _validate_shop_odds_references(shop_data, odds_data, report)
    _validate_no_temp_files(build_dir, report)

    try:
        expected_shop = build_shop_export(project, pack_ids)
        expected_odds = build_pack_odds_export(project, pack_ids)
        expected_patch = build_main_shop_settings_patch()
    except ValueError as exc:
        _add_error(
            report,
            code="build-expected-data-error",
            message=f"Could not compute expected build data: {exc}",
            path="build"
        )
        return report
    if shop_data is not _LOAD_FAILED:
        _validate_expected_content(
            actual=shop_data,
            expected=expected_shop,
            code="build-shop-content-mismatch",
            label="Shop export",
            path=shop_path,
            report=report
        )
    if odds_data is not _LOAD_FAILED:
        _validate_expected_content(
            actual=odds_data,
            expected=expected_odds,
            code="build-odds-content-mismatch",
            label="ShopPackOdds export",
            path=odds_path,
            report=report
        )
    if patch_data is not _LOAD_FAILED:
        _validate_expected_content(
            actual=patch_data,
            expected=expected_patch,
            code="build-settings-patch-mismatch",
            label="Shop settings patch",
            path=patch_path,
            report=report
        )

    return report