from ygomaster_packbuilder.manifest import ProjectManifest
from ygomaster_packbuilder.policies import PoliciesConfig

from .models import ValidationIssue, ValidationReport, ValidationSeverity
from .manifest import _iter_manifest_packs

def _get_policy_keys(policies: PoliciesConfig) -> set[str]:
    return {policy.key for policy in policies.policies}

def _validate_default_opening_policy(manifest: ProjectManifest, policy_keys: set[str], report: ValidationReport) -> None:
    default_policy = manifest.settings.default_opening_policy
    if default_policy not in policy_keys:
        report.issues.append(
            ValidationIssue(
                code="unknown-default-opening-policy",
                message=f"Default opening policy '{default_policy}' is not defined.",
                path="settings.default_opening_policy",
                severity=ValidationSeverity.ERROR,
            )
        )

def _validate_pack_opening_policies(manifest: ProjectManifest, policy_keys: set[str], report: ValidationReport) -> None:
    for pack, path in _iter_manifest_packs(manifest):
        opening_policy = pack.opening_policy
        if opening_policy is not None and opening_policy not in policy_keys:
            report.issues.append(
                ValidationIssue(
                    code="unknown-opening-policy",
                    message=f"Opening policy '{opening_policy}' is not defined.",
                    path=f"{path}.opening_policy",
                    severity=ValidationSeverity.ERROR,
                )
            )

def validate_project_configuration(manifest: ProjectManifest, policies: PoliciesConfig) -> ValidationReport:
    report = ValidationReport()
    policy_keys = _get_policy_keys(policies)

    _validate_default_opening_policy(manifest, policy_keys, report)
    _validate_pack_opening_policies(manifest, policy_keys, report)

    return report