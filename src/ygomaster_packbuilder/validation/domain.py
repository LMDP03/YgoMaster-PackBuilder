from collections import Counter

from ygomaster_packbuilder.domain import PackDefinition, PackType, PlayerDefinition, ProjectDefinition, Rarity
from ygomaster_packbuilder.rules import get_pack_rule

from .models import ValidationIssue, ValidationReport

def _add_error(report: ValidationReport, code: str, message: str, path: str) -> None:
    report.issues.append(
        ValidationIssue(
            code=code,
            message=message,
            path=path
        )
    )

def _validate_unique_keys(project: ProjectDefinition, report: ValidationReport) -> None:
    player_keys = [player.key for player in project.players]
    pack_keys = [pack.key for pack in project.packs]
    policy_keys = [policy.key for policy in project.opening_policies]
    for key, count in Counter(player_keys).items():
        if count > 1:
            _add_error(
                report,
                code="duplicate-player-key",
                message=f"Player key {key!r} is duplicated.",
                path="players"
            )

    for key, count in Counter(pack_keys).items():
        if count > 1:
            _add_error(
                report,
                code="duplicate-pack-key",
                message=f"Pack key {key!r} is duplicated.",
                path="packs"
            )

    for key, count in Counter(policy_keys).items():
        if count > 1:
            _add_error(
                report,
                code="duplicate-opening-policy-key",
                message=f"Opening policy key {key!r} is duplicated.",
                path="opening_policies"
            )

def _validate_pack(
    pack: PackDefinition,
    policy_keys: set[str],
    report: ValidationReport
) -> None:
    path = f"packs.{pack.key}"
    rule = get_pack_rule(pack.type)
    if pack.expected_card_count != rule.expected_card_count:
        _add_error(
            report,
            code="invalid-expected-card-count",
            message=f"Pack {pack.key!r} declares expected_card_count={pack.expected_card_count}, but {pack.type.value!r} requires {rule.expected_card_count}.",
            path=f"{path}.expected_card_count"
        )
    if pack.booster_size != rule.booster_size:
        _add_error(
            report,
            code="invalid-booster-size",
            message=f"Pack {pack.key!r} has booster_size={pack.booster_size}, but {pack.type.value!r} requires {rule.booster_size}.",
            path=f"{path}.booster_size"
        )
    if len(pack.cards) != rule.expected_card_count:
        _add_error(
            report,
            code="invalid-card-count",
            message=f"Pack {pack.key!r} contains {len(pack.cards)} cards; expected {rule.expected_card_count}.",
            path=f"{path}.cards"
        )
    if pack.opening_policy_key not in policy_keys:
        _add_error(
            report,
            code="unknown-opening-policy",
            message=f"Pack {pack.key!r} references unknown opening policy {pack.opening_policy_key!r}.",
            path=f"{path}.opening_policy_key"
        )

    ydk_counts = Counter(card.ydk_id for card in pack.cards)
    for ydk_id, count in ydk_counts.items():
        if count > 1:
            _add_error(
                report,
                code="duplicate-card",
                message=f"YDK card ID {ydk_id} appears {count} times in pack {pack.key!r}.",
                path=f"{path}.cards"
            )
    for index, card in enumerate(pack.cards):
        card_path = f"{path}.cards[{index}]"
        if card.rarity is None:
            _add_error(
                report,
                code="unresolved-rarity",
                message=f"Card {card.name!r} has no normalized rarity.",
                path=f"{card_path}.rarity"
            )

        if card.master_duel_id is None:
            _add_error(
                report,
                code="unresolved-master-duel-id",
                message=f"Card {card.name!r} (YDK {card.ydk_id}) has no Master Duel ID.",
                path=f"{card_path}.master_duel_id"
            )

    rarity_counts = Counter(card.rarity for card in pack.cards if card.rarity is not None)
    expected = rule.rarity_composition
    actual = {
        Rarity.N: rarity_counts[Rarity.N],
        Rarity.R: rarity_counts[Rarity.R],
        Rarity.SR: rarity_counts[Rarity.SR],
        Rarity.UR: rarity_counts[Rarity.UR],
    }
    expected_counts = {
        Rarity.N: expected.normal,
        Rarity.R: expected.rare,
        Rarity.SR: expected.super_rare,
        Rarity.UR: expected.ultra_rare,
    }
    for rarity, expected_count in expected_counts.items():
        actual_count = actual[rarity]
        if actual_count != expected_count:
            _add_error(
                report,
                code="invalid-rarity-composition",
                message=f"Pack {pack.key!r} contains {actual_count} {rarity.value} cards; expected {expected_count}.",
                path=f"{path}.cards"
            )

def _validate_player(
    player: PlayerDefinition,
    packs_by_key: dict[str, PackDefinition],
    report: ValidationReport,
) -> None:
    path = f"players.{player.key}"
    if len(player.mini_pack_keys) != 3:
        _add_error(
            report,
            code="invalid-mini-pack-count",
            message=f"Player {player.key!r} has {len(player.mini_pack_keys)} mini-packs; expected exactly 3.",
            path=f"{path}.mini_pack_keys"
        )
    if len(set(player.mini_pack_keys)) != len(player.mini_pack_keys):
        _add_error(
            report,
            code="duplicate-mini-pack-reference",
            message=f"Player {player.key!r} references the same mini-pack more than once.",
            path=f"{path}.mini_pack_keys"
        )

    main = packs_by_key.get(player.main_pack_key)
    if main is None:
        _add_error(
            report,
            code="missing-main-pack",
            message=f"Player {player.key!r} references missing main pack {player.main_pack_key!r}.",
            path=f"{path}.main_pack_key"
        )
        return
    if main.type is not PackType.PERSONAL_MAIN:
        _add_error(
            report,
            code="invalid-main-pack-type",
            message=f"Pack {main.key!r} referenced as main is not PERSONAL_MAIN.",
            path=f"{path}.main_pack_key"
        )
    if main.owner_key != player.key:
        _add_error(
            report,
            code="invalid-main-pack-owner",
            message=f"Main pack {main.key!r} belongs to {main.owner_key!r}, expected {player.key!r}.",
            path=f"{path}.main_pack_key"
        )
    if main.parent_pack_key is not None:
        _add_error(
            report,
            code="main-pack-has-parent",
            message=f"Main pack {main.key!r} must not have a parent pack.",
            path=f"packs.{main.key}.parent_pack_key"
        )

    mini_packs: list[PackDefinition] = []
    for mini_key in player.mini_pack_keys:
        mini = packs_by_key.get(mini_key)
        if mini is None:
            _add_error(
                report,
                code="missing-mini-pack",
                message=f"Player {player.key!r} references missing mini-pack {mini_key!r}.",
                path=f"{path}.mini_pack_keys"
            )
            continue
        mini_packs.append(mini)
        if mini.type is not PackType.PERSONAL_MINI:
            _add_error(
                report,
                code="invalid-mini-pack-type",
                message=f"Pack {mini.key!r} referenced as mini is not PERSONAL_MINI.",
                path=f"packs.{mini.key}.type"
            )
        if mini.owner_key != player.key:
            _add_error(
                report,
                code="invalid-mini-pack-owner",
            message=f"Mini-pack {mini.key!r} belongs to {mini.owner_key!r}, expected {player.key!r}.",
                path=f"packs.{mini.key}.owner_key"
            )
        if mini.parent_pack_key != main.key:
            _add_error(
                report,
                code="invalid-mini-pack-parent",
                message=f"Mini-pack {mini.key!r} has parent {mini.parent_pack_key!r}; expected {main.key!r}.",
                path=f"packs.{mini.key}.parent_pack_key"
            )

        main_cards = {card.ydk_id: card for card in main.cards}
        for card in mini.cards:
            main_card = main_cards.get(card.ydk_id)
            if main_card is None:
                _add_error(
                    report,
                    code="mini-card-not-in-main",
                    message=f"Card {card.name!r} (YDK {card.ydk_id}) from mini-pack {mini.key!r} is not present in the main pack.",
                    path=f"packs.{mini.key}.cards"
                )
                continue
            if card.rarity != main_card.rarity:
                _add_error(
                    report,
                    code="mini-card-rarity-mismatch",
                    message=f"Card YDK {card.ydk_id} has rarity {card.rarity!r} in {mini.key!r}, but {main_card.rarity!r} in {main.key!r}.",
                    path=f"packs.{mini.key}.cards"
                )

    card_to_minis: dict[int, list[str]] = {}
    for mini in mini_packs:
        for card in mini.cards:
            card_to_minis.setdefault(card.ydk_id, []).append(mini.key)
    for ydk_id, mini_keys in card_to_minis.items():
        unique_minis = list(dict.fromkeys(mini_keys))
        if len(unique_minis) > 1:
            _add_error(
                report,
                code="mini-pack-overlap",
                message=f"YDK card ID {ydk_id} appears in multiple sibling mini-packs: {unique_minis}.",
                path=f"{path}.mini_pack_keys"
            )

def _validate_shared_packs(project: ProjectDefinition, report: ValidationReport) -> None:
    shared_packs = [pack for pack in project.packs if pack.type is PackType.SHARED_STAPLES]

    if len(shared_packs) != 1:
        _add_error(
            report,
            code="invalid-shared-staples-count",
            message=f"Project contains {len(shared_packs)} shared staples packs; expected exactly 1.",
            path="packs"
        )

    for pack in shared_packs:
        if pack.owner_key is not None:
            _add_error(
                report,
                code="shared-pack-has-owner",
                message=f"Shared pack {pack.key!r} must not have an owner.",
                path=f"packs.{pack.key}.owner_key"
            )

        if pack.parent_pack_key is not None:
            _add_error(
                report,
                code="shared-pack-has-parent",
                message=f"Shared pack {pack.key!r} must not have a parent pack.",
                path=f"packs.{pack.key}.parent_pack_key"
            )

def validate_project_definition(project: ProjectDefinition) -> ValidationReport:
    report = ValidationReport()

    _validate_unique_keys(project, report)

    packs_by_key = {pack.key: pack for pack in project.packs}

    policy_keys = {policy.key for policy in project.opening_policies}

    for pack in project.packs:
        _validate_pack(pack, policy_keys, report)

    for player in project.players:
        _validate_player(player, packs_by_key, report)

    _validate_shared_packs(project, report)

    return report