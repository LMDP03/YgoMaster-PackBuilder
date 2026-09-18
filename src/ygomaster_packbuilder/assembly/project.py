from ygomaster_packbuilder.domain import PackDefinition, PackType, PlayerDefinition, ProjectDefinition, SourceProvider
from ygomaster_packbuilder.manifest import ProjectManifest
from ygomaster_packbuilder.manifest.models import ManifestPack, ManifestPlayer, ManifestSharedPack
from ygomaster_packbuilder.mapping import RarityMapping
from ygomaster_packbuilder.policies import PoliciesConfig, convert_policies_to_domain
from ygomaster_packbuilder.sources.ygoprodeck import YgoProDeckClient, YgoProDeckPackData, parse_custom_pack

from .pack import assemble_pack_definition

def _fetch_source_pack(manifest_pack: ManifestPack | ManifestSharedPack, ygoprodeck_client: YgoProDeckClient) -> YgoProDeckPackData:
    provider = manifest_pack.source.provider
    if provider != SourceProvider.YGOPRODECK.value:
        raise ValueError(f"Unsupported source provider: {provider!r}")
    external_id = manifest_pack.source.external_id
    raw_data = ygoprodeck_client.fetch_custom_pack_raw(external_id)
    return parse_custom_pack(external_id, raw_data)

def _assemble_player(
    manifest_player: ManifestPlayer,
    default_opening_policy_key: str,
    rarity_mapping: RarityMapping,
    ydk_mapping: dict[int, int],
    ygoprodeck_client: YgoProDeckClient
) -> tuple[PlayerDefinition, list[PackDefinition]]:
    main_source = _fetch_source_pack(manifest_player.main_pack, ygoprodeck_client)
    main_pack = assemble_pack_definition(
        manifest_pack=manifest_player.main_pack,
        source_pack=main_source,
        pack_type=PackType.PERSONAL_MAIN,
        default_opening_policy_key=default_opening_policy_key,
        rarity_mapping=rarity_mapping,
        ydk_mapping=ydk_mapping,
        owner_key=manifest_player.key
    )

    mini_packs: list[PackDefinition] = []
    for manifest_mini in manifest_player.mini_packs:
        mini_source = _fetch_source_pack(manifest_mini, ygoprodeck_client)
        mini_pack = assemble_pack_definition(
            manifest_pack=manifest_mini,
            source_pack=mini_source,
            pack_type=PackType.PERSONAL_MINI,
            default_opening_policy_key=default_opening_policy_key,
            rarity_mapping=rarity_mapping,
            ydk_mapping=ydk_mapping,
            owner_key=manifest_player.key,
            parent_pack_key=main_pack.key
        )
        mini_packs.append(mini_pack)

    player = PlayerDefinition(
        key=manifest_player.key,
        display_name=manifest_player.display_name,
        main_pack_key=main_pack.key,
        mini_pack_keys=[pack.key for pack in mini_packs]
    )
    return player, [main_pack, *mini_packs]

def _assemble_shared_pack(
    manifest_pack: ManifestSharedPack,
    default_opening_policy_key: str,
    rarity_mapping: RarityMapping,
    ydk_mapping: dict[int, int],
    ygoprodeck_client: YgoProDeckClient
) -> PackDefinition:
    source_pack = _fetch_source_pack(manifest_pack, ygoprodeck_client)
    try:
        pack_type = PackType(manifest_pack.type)
    except ValueError as exc:
        raise ValueError(f"Unsupported shared pack type: {manifest_pack.type!r}.") from exc

    return assemble_pack_definition(
        manifest_pack=manifest_pack,
        source_pack=source_pack,
        pack_type=pack_type,
        default_opening_policy_key=default_opening_policy_key,
        rarity_mapping=rarity_mapping,
        ydk_mapping=ydk_mapping
    )

def assemble_project_definition(
    manifest: ProjectManifest,
    policies: PoliciesConfig,
    rarity_mapping: RarityMapping,
    ydk_mapping: dict[int, int],
    *,
    ygoprodeck_client: YgoProDeckClient | None = None
) -> ProjectDefinition:
    client = (ygoprodeck_client if ygoprodeck_client is not None else YgoProDeckClient())
    players: list[PlayerDefinition] = []
    packs: list[PackDefinition] = []
    default_opening_policy_key = manifest.settings.default_opening_policy
    for manifest_player in manifest.players:
        player, player_packs = _assemble_player(
            manifest_player=manifest_player,
            default_opening_policy_key=default_opening_policy_key,
            rarity_mapping=rarity_mapping,
            ydk_mapping=ydk_mapping,
            ygoprodeck_client=client
        )
        players.append(player)
        packs.extend(player_packs)

    for manifest_shared_pack in manifest.shared_packs:
        shared_pack = _assemble_shared_pack(
            manifest_pack=manifest_shared_pack,
            default_opening_policy_key=default_opening_policy_key,
            rarity_mapping=rarity_mapping,
            ydk_mapping=ydk_mapping,
            ygoprodeck_client=client
        )
        packs.append(shared_pack)

    opening_policies = convert_policies_to_domain(policies)
    return ProjectDefinition(
        name=manifest.settings.name,
        players=players,
        packs=packs,
        opening_policies=opening_policies
    )