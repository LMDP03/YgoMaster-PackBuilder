"""Validate resolved Master Duel card IDs against YgoMaster's local catalog."""

from collections.abc import Collection

from ygomaster_packbuilder.domain import ProjectDefinition
from .models import ValidationIssue, ValidationReport


def validate_project_card_catalog(project: ProjectDefinition, card_ids: Collection[int]) -> ValidationReport:
    """Report cards mapped by YdkIds.txt but absent from Data/CardList.json."""
    report = ValidationReport()
    for pack in project.packs:
        for index, card in enumerate(pack.cards):
            if card.master_duel_id is None:
                continue  # The domain validator already reports unresolved mapping.
            if card.master_duel_id not in card_ids:
                report.issues.append(ValidationIssue(
                    code="card-not-in-ygomaster-catalog",
                    message=(
                        f"Card {card.name!r} (YDK {card.ydk_id}, Master Duel ID {card.master_duel_id}) "
                        f"in pack {pack.key!r} is absent from YgoMaster Data/CardList.json. "
                        "The mapping in YdkIds.txt alone does not guarantee availability."
                    ),
                    path=f"packs.{pack.key}.cards[{index}].master_duel_id",
                ))
    return report
