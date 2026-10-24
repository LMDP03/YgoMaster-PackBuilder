# YgoMaster IDs, export and installation

## 1. Source-of-truth files

PackBuilder is designed to integrate with **pixeltris/YgoMaster**, without modifying its code. It creates two **modular** shop data files and a separate settings patch:

```text
build/
├── Shop/ygomaster-packbuilder.json
├── ShopPackOdds/ygomaster-packbuilder.json
└── ShopSettings.patch.json
```

YgoMaster loads the main `Data/Shop.json` and modular `Data/Shop/*.json`; the upstream loader for modular `Data/ShopPackOdds/*.json` currently uses an incorrect directory enumeration; therefore PackBuilder merges its odds into the main `Data/ShopPackOdds.json` at install time. The main shop loader handles global options such as `PerPackRarities`, but does **not** apply this setting from modular shop files. Consequently, `ShopSettings.patch.json` is an *instruction for the installer* and must **not** be copied as an independent runtime shop JSON file.

The exporter does not currently generate `ShopPackOddsVisuals.json`, image assets, textures or new card data. It uses existing card IDs for icons/previews.

## 2. Stable numeric IDs

`registry/ids.py` provides `YgoMasterIdRegistry(version, next_pack_id, pack_ids)`, `load_id_registry`, `ensure_project_pack_ids`, `save_id_registry` and `get_pack_shop_id`.

`state/ygomaster_ids.json` initially has:

```json
{
  "version": 1,
  "next_pack_id": 9000000,
  "pack_ids": {}
}
```

The custom range is `packId=9,000,000..9,999,999`. The absolute shop ID is calculated as:

```python
shop_id = 10_000_000 + pack_id
```

Thus pack IDs correspond to shop IDs `19,000,000..19,999,999`. The `10_000_000` offset is the Pack category base shop ID in YgoMaster.

For each project, `ensure_project_pack_ids(project, registry)`:

1. Reuses IDs already associated with a pack's **stable key**.
2. Sorts unassigned pack keys before allocating new IDs.
3. Advances `next_pack_id`, skipping any occupied IDs.
4. Never reuses removed pack IDs; an old key retains its mapping and gets its original ID if restored.

The registry is **persistent state, not a cache**. Commit its changes after a successful build and distribute the same version to every builder. Renaming a pack's `key` is an ID migration, unlike changing the human-readable name.

The loader validates version, ID range, key strings and duplicate assigned ID values. The writer persists the registry by replacing a `.tmp` file. The workflow saves it **after final build validation**, not after merely allocating IDs.

## 3. Shop export

`build_shop_export(project, pack_ids)` emits a dictionary with a `PackShop` mapping keyed by **absolute string shop IDs**. The item contains:

| Field | Source / meaning |
| --- | --- |
| `packId` | Stable custom pack ID |
| `packType` | `2` (`Selection`) for all league packs |
| `secretType` | `0`; the builder does not use auto-unlocked `Secret` pack semantics |
| `nameTextId` | Source pack name (YgoMaster accepts plain text through its ID-string fallback) |
| `descShortTextId`, `descFullTextId` | Source pack description, fallback to name |
| `pack_card_num` | Rule-driven 7 / 3 / 11 card booster |
| `cardList` | `{ "<MasterDuelCardID>": rarity_integer }` |
| `iconMrk`, `iconType`, `iconData`, `preview` | Cover card/icon referencing an existing MD card |
| `price`, `priceX10` | `100`, `1000` (currently hard-coded) |
| `subCategory`, `productType` | Currently `1`, `1` |

The cover card is selected from resolved cards by maximum **normalized rarity** (first winner on ties). There is no custom art URL in the Shop payload. The exporter rejects any missing `master_duel_id`, unresolved `rarity`, duplicate `master_duel_id` within a pack or missing pack ID.

YgoMaster rarity encoding is N=1, R=2, SR=3, UR=4. With `PerPackRarities=true` the per-pack values in `cardList` are significant; without it, YgoMaster may use its default card rarities instead of the league normalization.

## 4. Odds export

`build_pack_odds_export(project, pack_ids)` emits a **JSON array**, one entry per pack. Each entry binds an absolute ID via:

```json
{
  "packShopIds": [19000000],
  "gachaType": 1,
  "cardRateList": [
    {
      "start_num": 1,
      "end_num": 7,
      "standard": false,
      "rate": {"1": {"rate": "55.00"}, "2": {"rate": "35.00"}, "3": {"rate": "7.50"}, "4": {"rate": "2.50"}}
    },
    {
      "start_num": 7,
      "end_num": 7,
      "standard": false,
      "settle_rare_min": 3,
      "settle_rare_max": 4,
      "rate": {"3": {"rate": "80.00"}, "4": {"rate": "20.00"}}
    },
    {
      "start_num": 7,
      "end_num": 7,
      "standard": false,
      "settle_rare_min": 4,
      "settle_rare_max": 4,
      "rate": {"4": {"rate": "100.00"}}
    }
  ],
  "premiereRateList": []
}
```

This is an **illustrative excerpt** (the actual exporter includes its fixed `premiereRateList` instead of `[]`, and rates change based on the selected policy and booster size). The final-slot index is `pack.booster_size`. For a disabled ten-pack guarantee or pity, its conditional row is omitted. Zero-rate rarities are omitted from each `rate` map.

Pity state and x10 counters are owned by the YgoMaster runtime and scoped to the player/pack; PackBuilder only supplies odds rows and does not simulate or persist draws. Verify the behavior against the installed game/server version before using it in live competitive play.

## 5. JSON writer and build validator

`write_ygomaster_build(project, pack_ids, build_dir)` builds the three Python structures, serializes all to UTF-8 JSON (`indent=2`, `ensure_ascii=False`, trailing newline), then writes the managed files individually through `.tmp` replacement. It does **not** clean unrelated build files or offer an all-files transaction.

The workflow first writes/validates a staging directory, then writes/validates the final build; only after the final build passes does it save `state/ygomaster_ids.json`. The build validator checks file presence, JSON roots, Shop/odds references, `.tmp` leftovers and full structural equality with freshly computed exports.

## 6. Installer target layout (version 2)

The **build format remains unchanged**, but installation now merges generated odds into the **main** `Data/ShopPackOdds.json`, avoiding a modular odds directory that can trigger the current upstream YgoMaster loader bug.

```text
<YgoMaster>/
├── Data/
│   ├── Shop.json                           # PerPackRarities enabled
│   ├── Shop/ygomaster-packbuilder.json      # Managed modular shop file
│   └── ShopPackOdds.json                   # Existing odds + marked custom entries
└── .ygomaster-packbuilder/
    ├── install-state.json
    └── backup/                              # Pre-existing managed shop file, if any
```

The installer requires the existing main Shop and ShopPackOdds files. It refuses installation if `Data/ShopPackOdds/` already exists; back up or relocate that directory manually after checking its contents.

`ShopSettings.patch.json` is an installer instruction and enables `PerPackRarities` in the existing main `Data/Shop.json`. The main Shop patcher preserves original comments and text where possible. The odds patcher parses a comment-masked copy that also tolerates trailing commas (as in upstream YgoMaster's MiniJSON parser) to validate the JSON array, but **does not reserialize existing entries**: it inserts a delimited block after the opening bracket, using the original BOM and line-ending style. Its SHA-256 is recorded in the installation state.

The beginning/end markers are:
```text
// YGOMASTER-PACKBUILDER ODDS BEGIN
... generated per-pack odds ...
// YGOMASTER-PACKBUILDER ODDS END
```

Existing odds entries remain in place and may have unrelated user edits between updates. A collision between existing `packShopIds` and generated IDs is rejected before installation. Reinstalling with unchanged data is idempotent.

## 7. Local installation state, updates and removal

The local installation state is now **version 2** and contains `odds_block_sha256` in addition to the original global Shop setting and the managed modular Shop file:

```json
{
  "version": 2,
  "per_pack_rarities_before": false,
  "odds_block_sha256": "<64-character SHA-256 digest>",
  "managed_files": {
    "Data/Shop/ygomaster-packbuilder.json": {
      "relative_path": "Data/Shop/ygomaster-packbuilder.json",
      "preexisting": false,
      "installed_sha256": "<64-character SHA-256 digest>"
    }
  }
}
```

The `odds_block_sha256` protects **only the generated block**, so unrelated changes elsewhere in the main odds file are preserved during update/uninstall. If the marked block is missing, duplicated or manually changed, the operation fails rather than rewriting potentially user-owned data. The uninstall removes only the generated block, restores the original `PerPackRarities` setting and restores or deletes the managed Shop file according to the original backup state.

**Migration:** state version 1 installations are not automatically migrated. If the old installer was previously used, uninstall with the old version first and remove any old modular odds directory after backing it up, **before upgrading to this release**. Version 2 rejects incompatible old state. No changes are made to user data on disk until an installation is explicitly requested.

The installer uses atomic writes for each file, but a multi-file update is not an all-or-nothing transaction under unexpected filesystem errors. Stop YgoMaster before installing or uninstalling and restart it afterward.

## 8. Deployment caveats

- The installer checks collisions against existing `packShopIds` in the main odds file, but **does not scan all existing modular shop files** for colliding shop IDs. The custom range is chosen to avoid stock IDs, but users should still inspect a heavily modded target.
- Per-file atomic replaces do not make a multi-file install/uninstall rollback-proof under I/O failure.
- Installing data does not automatically distribute it across other machines or live network peers.
- Shop display and gacha behavior in a specific YgoMaster version must be tested; no `ShopPackOddsVisuals` file or new art is produced.
- The persistent project ID registry belongs in version control, whereas the target-local `.ygomaster-packbuilder/` directory does not.
