# Sources and card mappings

## 1. Adapter boundary

`src/ygomaster_packbuilder/sources/ygoprodeck/` is the only implemented external card-pack source. It consists of:

```text
client.py      YgoProDeckClient — HTTP transport
parser.py      parse_custom_pack — response parsing / consistency
models.py      YgoProDeckPackCard, YgoProDeckPackData
converter.py   convert_pack_cards_to_domain — source card -> Card
```

The adapter receives the string `external_id` from `ManifestPackSource`; the manifest `key`, owner and parent are unknown to the HTTP client and parser. Those are attached in assembly.

## 2. HTTP request and API limitations

`YgoProDeckClient.fetch_custom_pack_raw(external_id: str) -> list[dict]` performs a synchronous request using a `requests.Session`:

```text
GET https://ygoprodeck.com/api/pack-sim/getPackInfo.php?id=<external_id>
```

Default timeout: **15 seconds**. The method calls `raise_for_status()`, parses JSON, and requires a list root. The client accepts an injected `requests.Session`, and project assembly accepts an optional injected `ygoprodeck_client` for offline tests.

This is an **internal custom-pack endpoint** rather than a documented stable public v7 API. Its payload/availability/change propagation are external dependencies. **PackBuilder has no response cache**: each fetch performs a fresh client request. YGOPRODeck or intermediary HTTP caches may still return stale responses after editing a pack.

## 3. Parser contract

`parse_custom_pack(external_id, raw_data)` requires nonempty rows. The first row provides pack-level fields:

- `pack_name`, `pack_description`, `username`, `img_url`;
- each card row must contain `name`, `id`, `type`, `card_rarity`.

The parser checks that the pack-level fields match between the first row and every subsequent row. It converts `id` to an integer YDK/passcode and preserves `card_rarity` verbatim. It produces `YgoProDeckPackData` with source ID, name, description, creator, image ID and `YgoProDeckPackCard` rows.

`converter.py` turns each source card into a mutable domain `Card(name, ydk_id, source_rarity)`, leaving `master_duel_id` and normalized `rarity` unset. `PackDefinition.name` and `.description` therefore come from **the API response**, not the `key` in YAML.

The `img_url` metadata is read, but the current Shop exporter does **not** download or embed custom pack artwork. Shop preview/thumbnail references are derived from an existing Master Duel card ID instead.

## 4. Source rarity normalization

`mapping/rarity.py` parses `config/rarity_mapping.yaml` into `RarityMapping(rarities, overrides)`. `resolve_rarity(source_rarity, pack_type, mapping)` checks the pack-specific override, then the global map; unknown source rarity raises an error.

The current policy is:

```text
Common        -> N
Rare          -> R
Super Rare    -> SR
Ultra Rare    -> UR
Secret Rare + PERSONAL_MAIN   -> N
Secret Rare + PERSONAL_MINI   -> N
Secret Rare + SHARED_STAPLES -> UR
```

`normalize_card_rarity()` updates `Card.rarity` in place. The source string remains for diagnostics; this is necessary because normalized rarity, not raw source rarity, determines compatibility between main and mini cards.

## 5. YDK/passcode -> Master Duel ID

The mapping file belongs to the **installed YgoMaster**, at `<YgoMaster>/Data/YdkIds.txt`. `workflow.resolve_workflow_paths()` derives this path from `--ygomaster-dir`. There is no separate YDK-file argument in the CLI.

Each meaningful line has exactly two whitespace-delimited integer columns:

```text
<YDK card ID> <Master Duel internal card ID>
34541863 7128
```

Empty lines and lines starting with `#` are skipped. `load_ydk_mapping()` rejects invalid line lengths, nonintegers and **duplicate YDK keys**; duplicate *values* (Master Duel IDs) are not rejected by this loader. `resolve_card_master_duel_id()` sets `Card.master_duel_id` if found and returns `False` on a missing key; `resolve_cards_master_duel_ids()` returns unresolved cards.

The domain validator later emits `unresolved-master-duel-id` if `Card.master_duel_id` is still `None`. The exporter checks again and fails rather than fabricating a game-internal ID.

**Example diagnostic:** a YGOPRODeck card may have a valid `ydk_id` but be absent from a given version of YgoMaster's `YdkIds.txt`. That indicates an unresolved mapping for that installation, not necessarily a typo in YGOPRODeck. Confirm the actual game/card mapping or remove/substitute the unsupported card. Do **not** invent an internal ID or modify the registry to mask the issue; the registry maps **pack keys**, not card IDs.

## 6. Assembly call path

`assembly/project.py` coordinates one HTTP fetch per manifest pack:

```text
ManifestPack / ManifestSharedPack
      -> _fetch_source_pack()
      -> YgoProDeckClient.fetch_custom_pack_raw()
      -> parse_custom_pack()
      -> assemble_pack_definition()
           -> convert_pack_cards_to_domain()
           -> normalize_cards()           # context-specific
           -> resolve_cards_master_duel_ids()
           -> set PackRule + relations + policy
```

`assemble_pack_definition()` checks that the fetched `YgoProDeckPackData.external_id` matches the manifest source ID. It uses `get_pack_rule(pack_type)` for expected count and booster size. It **does not** itself reject an invalid total count or overlapping mini cards; `validation/domain.py` enforces that after all packs have been assembled.

## 7. Offline testing strategy

The `tests/` notebooks use injected fake clients/session objects rather than calling the live endpoint. The end-to-end workflow notebook generates synthetic packs and a synthetic `YdkIds.txt` under `TemporaryDirectory` to test all layers deterministically. Live notebook runs exercise real source updates and can fail on external delays, card pool changes, or missing YDK mappings.
