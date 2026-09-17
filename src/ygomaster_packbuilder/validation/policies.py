from ygomaster_packbuilder.policies import PoliciesConfig
from ygomaster_packbuilder.policies.models import PolicyDefinition, PolicyRarityDistribution

from .models import ValidationIssue, ValidationReport, ValidationSeverity

def _validate_policy_keys(config: PoliciesConfig, report: ValidationReport) -> None:
    if not config.policies:
        report.issues.append(
            ValidationIssue(
                code="no-policies",
                message="At least one opening policy must be defined.",
                path="policies",
                severity=ValidationSeverity.ERROR,
            )
        )
        return
    seen: set[str] = set()
    for index, policy in enumerate(config.policies):
        if not policy.key.strip():
            report.issues.append(
                ValidationIssue(
                    code="empty-policy-key",
                    message="Opening policy key cannot be empty.",
                    path=f"policies[{index}].key",
                    severity=ValidationSeverity.ERROR,
                )
            )
        if policy.key in seen:
            report.issues.append(
                ValidationIssue(
                    code="duplicate-policy-key",
                    message=f"Opening policy key '{policy.key}' is defined more than once.",
                    path=f"policies[{index}].key",
                    severity=ValidationSeverity.ERROR,
                )
            )
        else:
            seen.add(policy.key)

def _validate_distribution(distribution: PolicyRarityDistribution, report: ValidationReport, path: str) -> None:
    values = {
        "normal": distribution.normal,
        "rare": distribution.rare,
        "super_rare": distribution.super_rare,
        "ultra_rare": distribution.ultra_rare,
    }
    for name, value in values.items():
        if value < 0.0 or value > 100.0:
            report.issues.append(
                ValidationIssue(
                    code="probability-out-of-range",
                    message=f"Probability for '{name}' must be between 0 and {100.0}.",
                    path=f"{path}.{name}",
                    severity=ValidationSeverity.ERROR,
                )
            )
    total = sum(values.values())
    if total != 100.0:
        report.issues.append(
            ValidationIssue(
                code="invalid-probability-total",
                message=f"Rarity distribution must sum to {100.0}, but got {total}.",
                path=path,
                severity=ValidationSeverity.ERROR,
            )
        )

def _validate_normal_distribution(policy: PolicyDefinition, report: ValidationReport, path: str) -> None:
    if policy.normal_slot_distribution is None:
        report.issues.append(
            ValidationIssue(
                code="missing-normal-distribution",
                message="Normal slot distribution must be defined.",
                path=f"{path}.normal_slot_distribution",
                severity=ValidationSeverity.ERROR,
            )
        )
        return
    _validate_distribution(policy.normal_slot_distribution, report, f"{path}.normal_slot_distribution")


def _validate_ten_pack_guarantee(policy: PolicyDefinition, report: ValidationReport, path: str) -> None:
    guarantee = policy.ten_pack_guarantee
    if guarantee is None:
        report.issues.append(
            ValidationIssue(
                code="missing-ten-pack-guarantee",
                message="Ten pack guarantee must be defined.",
                path=f"{path}.ten_pack_guarantee",
                severity=ValidationSeverity.ERROR,
            )
        )
        return
    if not guarantee.enabled:
        return
    _validate_distribution(guarantee.final_slot_distribution, report, f"{path}.ten_pack_guarantee.final_slot_distribution")

def _validate_ultra_rare_pity(policy: PolicyDefinition, report: ValidationReport, path: str) -> None:
    pity = policy.ultra_rare_pity
    if pity is None:
        report.issues.append(
            ValidationIssue(
                code="missing-ultra-rare-pity",
                message="Ultra rare pity must be defined.",
                path=f"{path}.ultra_rare_pity",
                severity=ValidationSeverity.ERROR,
            )
        )
        return
    if not pity.enabled:
        return
    distribution = pity.guaranteed_slot_distribution
    if distribution.normal != 0 or distribution.rare != 0 or distribution.super_rare != 0 or distribution.ultra_rare != 100:
        report.issues.append(
            ValidationIssue(
                code="invalid-ur-pity-distribution",
                message=r"Enabled Ultra Rare pity must guarantee 100% ultra rare in its guaranteed slot distribution.",
                path=f"{path}.ultra_rare_pity.guaranteed_slot_distribution",
                severity=ValidationSeverity.ERROR,
            )
        )
    _validate_distribution(distribution, report, f"{path}.ultra_rare_pity.guaranteed_slot_distribution")

def _validate_policy(policy: PolicyDefinition, report: ValidationReport, index: int) -> None:
    path = f"policies[{index}]"
    _validate_normal_distribution(policy, report, path)
    _validate_ten_pack_guarantee(policy, report, path)
    _validate_ultra_rare_pity(policy, report, path)

def validate_policies_config(config: PoliciesConfig) -> ValidationReport:
    report = ValidationReport()
    _validate_policy_keys(config, report)
    for index, policy in enumerate(config.policies):
        _validate_policy(policy, report, index)
    return report