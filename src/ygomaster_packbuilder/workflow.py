from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from ygomaster_packbuilder.assembly import assemble_project_definition
from ygomaster_packbuilder.domain import ProjectDefinition
from ygomaster_packbuilder.exporters.ygomaster import YgoMasterBuildArtifacts, write_ygomaster_build
from ygomaster_packbuilder.installer import YgoMasterInstallResult, install_ygomaster_build
from ygomaster_packbuilder.manifest import load_project_manifest
from ygomaster_packbuilder.mapping import load_rarity_mapping, load_ydk_mapping
from ygomaster_packbuilder.policies import load_policies_config
from ygomaster_packbuilder.registry import ensure_project_pack_ids, load_id_registry, save_id_registry
from ygomaster_packbuilder.sources.ygoprodeck import YgoProDeckClient
from ygomaster_packbuilder.validation import (
    ValidationReport,
    validate_policies_config,
    validate_project_configuration,
    validate_project_definition,
    validate_project_manifest,
    validate_ygomaster_build,
)

@dataclass(slots=True, frozen=True)
class WorkflowPaths:
    project_root: Path
    ygomaster_dir: Path
    manifest: Path
    policies: Path
    rarity_mapping: Path
    ydk_mapping: Path
    id_registry: Path
    build_dir: Path

@dataclass(slots=True)
class BuildWorkflowResult:
    project: ProjectDefinition
    pack_ids: dict[str, int]
    artifacts: YgoMasterBuildArtifacts
    paths: WorkflowPaths

@dataclass(slots=True)
class InstallWorkflowResult:
    build: BuildWorkflowResult
    installation: YgoMasterInstallResult

class WorkflowError(RuntimeError):
    pass

def resolve_workflow_paths(project_root: str | Path, ygomaster_dir: str | Path) -> WorkflowPaths:
    project_root = Path(project_root).resolve()
    ygomaster_dir = Path(ygomaster_dir).resolve()
    if not project_root.is_dir():
        raise WorkflowError(f"Project root does not exist: {project_root}")
    if not ygomaster_dir.is_dir():
        raise WorkflowError(f"YgoMaster root does not exist: {ygomaster_dir}")
    ydk_mapping = ygomaster_dir / "Data" / "YdkIds.txt"
    if not ydk_mapping.is_file():
        raise WorkflowError(f"YgoMaster YdkIds.txt was not found: {ydk_mapping}")
    return WorkflowPaths(
        project_root=project_root,
        ygomaster_dir=ygomaster_dir,
        manifest=project_root / "config" / "project.yaml",
        policies=project_root / "config" / "policies.yaml",
        rarity_mapping=project_root / "config" / "rarity_mapping.yaml",
        ydk_mapping=ydk_mapping,
        id_registry=project_root / "state" / "ygomaster_ids.json",
        build_dir=project_root / "build",
    )

def _require_valid(report: ValidationReport, stage: str) -> None:
    if report.is_valid:
        return
    details = "\n".join(f"- {issue.code} [{issue.path}]: {issue.message}" for issue in report.errors)
    raise WorkflowError(f"{stage} validation failed:\n{details}")

def build_project(
    project_root: str | Path,
    ygomaster_dir: str | Path,
    *,
    ygoprodeck_client: YgoProDeckClient | None = None,
) -> BuildWorkflowResult:
    paths = resolve_workflow_paths(project_root, ygomaster_dir)

    manifest = load_project_manifest(paths.manifest)
    policies = load_policies_config(paths.policies)

    _require_valid(validate_project_manifest(manifest), "Manifest")
    _require_valid(validate_policies_config(policies), "Policies")
    _require_valid(validate_project_configuration(manifest, policies), "Project configuration")

    rarity_mapping = load_rarity_mapping(paths.rarity_mapping)
    ydk_mapping = load_ydk_mapping(paths.ydk_mapping)

    project = assemble_project_definition(
        manifest=manifest,
        policies=policies,
        rarity_mapping=rarity_mapping,
        ydk_mapping=ydk_mapping,
        ygoprodeck_client=ygoprodeck_client,
    )
    _require_valid(validate_project_definition(project), "Domain")

    registry = load_id_registry(paths.id_registry)
    pack_ids = ensure_project_pack_ids(project, registry)

    with TemporaryDirectory(prefix=".ygomaster-packbuilder-", dir=paths.project_root) as temp_dir:
        staging_dir = Path(temp_dir)
        write_ygomaster_build(project, pack_ids, staging_dir)
        _require_valid(validate_ygomaster_build(project, pack_ids, staging_dir), "Staged build")

    artifacts = write_ygomaster_build(project, pack_ids, paths.build_dir)
    _require_valid(validate_ygomaster_build(project, pack_ids, paths.build_dir), "Final build")
    save_id_registry(registry, paths.id_registry)

    return BuildWorkflowResult(
        project=project,
        pack_ids=pack_ids,
        artifacts=artifacts,
        paths=paths,
    )

def build_and_install_project(
    project_root: str | Path,
    ygomaster_dir: str | Path,
    *,
    ygoprodeck_client: YgoProDeckClient | None = None,
) -> InstallWorkflowResult:
    build = build_project(
        project_root=project_root,
        ygomaster_dir=ygomaster_dir,
        ygoprodeck_client=ygoprodeck_client,
    )
    installation = install_ygomaster_build(
        project=build.project,
        pack_ids=build.pack_ids,
        build_dir=build.paths.build_dir,
        ygomaster_dir=build.paths.ygomaster_dir,
    )
    return InstallWorkflowResult(build=build, installation=installation)
