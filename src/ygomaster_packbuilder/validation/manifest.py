from ygomaster_packbuilder.domain import PackType, SourceProvider
from ygomaster_packbuilder.manifest import ProjectManifest

from .models import ValidationIssue, ValidationReport, ValidationSeverity

SUPPORTED_PROVIDERS = [provider.value for provider in SourceProvider]
SUPPORTED_SHARED_PACK_TYPES = {pack_type.SHARED_STAPLES.value for pack_type in PackType}

def _iter_manifest_packs(manifest: ProjectManifest):
    for player_index, player in enumerate(manifest.players):
        yield player.main_pack, f"players[{player_index}].main_pack"
        for mini_pack_index, mini_pack in enumerate(player.mini_packs):
            yield mini_pack, f"players[{player_index}].mini_packs[{mini_pack_index}]"
    for index, pack in enumerate(manifest.shared_packs):
        yield pack, f"shared_packs[{index}]"

def _validate_players(manifest: ProjectManifest, report: ValidationReport) -> None:
    if not manifest.players:
        report.issues.append(
            ValidationIssue(
                code="no-players",
                message="The manifest must define at least one player.",
                path="players",
                severity=ValidationSeverity.ERROR,
            )
        )
    seen: set[str] = set()
    for index, player in enumerate(manifest.players):
        if len(player.mini_packs) != 3:
            report.issues.append(
                ValidationIssue(
                    code="invalid-mini-pack-count",
                    message=f"Player '{player.key}' must define exactly 3 mini packs, but {len(player.mini_packs)} were found.",
                    path=f"players[{index}].mini_packs",
                    severity=ValidationSeverity.ERROR,
                )
            )
        if player.key in seen:
            report.issues.append(
                ValidationIssue(
                    code="duplicate-player-key",
                    message=f"Player key '{player.key}' is defined more than once.",
                    path=f"players[{index}].key",
                    severity=ValidationSeverity.ERROR,
                )
            )
        else:
            seen.add(player.key)

def _validate_pack_keys(manifest: ProjectManifest, report: ValidationReport) -> None:
    seen: set[str] = set()
    for pack, path in _iter_manifest_packs(manifest):
        if pack.key in seen:
            report.issues.append(
                ValidationIssue(
                    code="duplicate-pack-key",
                    message=f"Pack key '{pack.key}' is defined more than once.",
                    path=f"{path}.key",
                    severity=ValidationSeverity.ERROR,
                )
            )
        else:
            seen.add(pack.key)

def _validate_sources(manifest: ProjectManifest, report: ValidationReport) -> None:
    for pack, path in _iter_manifest_packs(manifest):
        provider = pack.source.provider
        if provider not in SUPPORTED_PROVIDERS:
            report.issues.append(
                ValidationIssue(
                    code="unsupported-source-provider",
                    message=f"Source provider '{provider}' is not supported.",
                    path=f"{path}.source.provider",
                    severity=ValidationSeverity.ERROR,
                )
            )

def _validate_shared_packs(manifest: ProjectManifest, report: ValidationReport) -> None:
    for index, pack in enumerate(manifest.shared_packs):
        if pack.type not in SUPPORTED_SHARED_PACK_TYPES:
            report.issues.append(
                ValidationIssue(
                    code="unsupported-shared-pack-type",
                    message=f"Shared pack type '{pack.type}' is not supported.",
                    path=f"shared_packs[{index}].type",
                    severity=ValidationSeverity.ERROR,
                )
            )
    staples_count = sum(1 for pack in manifest.shared_packs if pack.type == PackType.SHARED_STAPLES.value)
    if staples_count != 1:
        report.issues.append(
            ValidationIssue(
                code="invalid-shared-staples-count",
                message=f"There must be exactly one shared staples pack, found {staples_count}.",
                path="shared_packs",
                severity=ValidationSeverity.ERROR,
            )
        )

def _validate_opening_policy_fields(manifest: ProjectManifest, report: ValidationReport) -> None:
    default_opening_policy = manifest.settings.default_opening_policy
    if default_opening_policy is not None and not default_opening_policy.strip():
        report.issues.append(
            ValidationIssue(
                code="empty-default-opening-policy",
                message=f"Default opening policy must be 'configuration-a', found '{default_opening_policy}'.",
                path="settings.default_opening_policy",
                severity=ValidationSeverity.ERROR,
            )
        )
    for pack, path in _iter_manifest_packs(manifest):
        opening_policy = pack.opening_policy
        if opening_policy is not None and not opening_policy.strip():
            report.issues.append(
                ValidationIssue(
                    code="empty-opening-policy",
                    message=f"Opening policy override cannot be empty.",
                    path=f"{path}.opening_policy",
                    severity=ValidationSeverity.ERROR,
                )
            )

def validate_project_manifest(manifest: ProjectManifest) -> ValidationReport:
    report = ValidationReport()

    _validate_players(manifest, report)
    _validate_pack_keys(manifest, report)
    _validate_sources(manifest, report)
    _validate_shared_packs(manifest, report)
    _validate_opening_policy_fields(manifest, report)

    return report