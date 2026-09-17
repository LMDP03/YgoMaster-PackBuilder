from dataclasses import dataclass, field
from enum import StrEnum

class ValidationSeverity(StrEnum):
    WARNING = "warning"
    ERROR = "error"

@dataclass(slots=True, frozen=True)
class ValidationIssue:
    code: str
    message: str
    path: str
    severity: ValidationSeverity = ValidationSeverity.ERROR

@dataclass(slots=True)
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity is ValidationSeverity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity is ValidationSeverity.WARNING]

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0