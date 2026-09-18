from ygomaster_packbuilder.domain import PackDefinition, PackType, SourcePackRef, SourceProvider
from ygomaster_packbuilder.manifest.models import ManifestPack, ManifestSharedPack
from ygomaster_packbuilder.mapping import RarityMapping, normalize_cards, resolve_cards_master_duel_ids
from ygomaster_packbuilder.rules import get_pack_rule
from ygomaster_packbuilder.sources.ygoprodeck import YgoProDeckPackData, convert_pack_cards_to_domain

def _resolve_opening_policy_key(manifest_pack: ManifestPack | ManifestSharedPack, default_opening_policy_key: str) -> str:
    if manifest_pack.opening_policy is not None:
        return manifest_pack.opening_policy
    return default_opening_policy_key

def _convert_source_ref(manifest_pack: ManifestPack | ManifestSharedPack) -> SourcePackRef:
    return SourcePackRef(
        provider=SourceProvider(
            manifest_pack.source.provider
        ),
        external_id=manifest_pack.source.external_id,
    )

def assemble_pack_definition(
        manifest_pack: ManifestPack | ManifestSharedPack,
        source_pack: YgoProDeckPackData,
        pack_type: PackType,
        default_opening_policy_key: str,
        rarity_mapping: RarityMapping,
        ydk_mapping: dict[int, int],
        *,
        owner_key: str | None = None,
        parent_pack_key: str | None = None,
) -> PackDefinition:
    if source_pack.external_id != manifest_pack.source.external_id:
        raise ValueError("Source pack external ID does not match manifest pack source external ID.")
    rule = get_pack_rule(pack_type)
    cards = convert_pack_cards_to_domain(source_pack)
    normalize_cards(cards, rarity_mapping, pack_type)
    resolve_cards_master_duel_ids(cards, ydk_mapping)
    opening_policy_key = _resolve_opening_policy_key(manifest_pack, default_opening_policy_key)
    source_ref = _convert_source_ref(manifest_pack)
    return PackDefinition(
        key=manifest_pack.key,
        name=source_pack.name,
        description=source_pack.description,
        type=pack_type,
        source=source_ref,
        expected_card_count=rule.expected_card_count,
        booster_size=rule.booster_size,
        opening_policy_key=opening_policy_key,
        owner_key=owner_key,
        parent_pack_key=parent_pack_key,
        cards=cards
    )