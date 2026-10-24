# Project manifest

## 1. Role and location

`config/project.yaml` declares **which players and external packs belong to the project**. It deliberately excludes card lists, normalized rarities, Master Duel IDs, pack sizes, numeric YgoMaster IDs and probability percentages. Those are provided by the source adapter, mapping/rules modules, ID registry or separate policy file.

The current YAML root contains three sections:

```yaml
settings:
  name: "Master Duel Custom League"
  default_opening_policy: "configuration-a"
players:
  - key: "livio"
    display_name: "Marzius"
    main_pack:
      key: "livio-scaled_invasion"
      source: {provider: "ygoprodeck", external_id: "24116"}
    mini_packs:
      - key: "livio-scaled_invasion-molting_evolution"
        source: {provider: "ygoprodeck", external_id: "24176"}
      - key: "livio-scaled_invasion-venomous_strike"
        source: {provider: "ygoprodeck", external_id: "24172"}
      - key: "livio-scaled_invasion-alien_attack"
        source: {provider: "ygoprodeck", external_id: "24175"}
shared_packs:
  - key: "shared_staples-traps_n_tricks"
    type: "shared_staples"
    source: {provider: "ygoprodeck", external_id: "24110"}
```

**Important correction to older examples:** the global key is **`settings:`**, not `project:`. The actual checked-in manifest defines **3 players** (`livio`, `matteo`, `lorenzo`) and **13 total packs**; the example above is a shortened schema illustration, not a complete valid three-player project.

## 2. DTO model and loader

`manifest/models.py` defines:

| Dataclass | Fields |
| --- | --- |
| `ManifestProjectSettings` | `name`, `default_opening_policy` |
| `ManifestPackSource` | `provider`, `external_id` |
| `ManifestPack` | `key`, `source`, `opening_policy` |
| `ManifestSharedPack` | `key`, `type`, `source`, `opening_policy` |
| `ManifestPlayer` | `key`, `display_name`, `main_pack`, `mini_packs` |
| `ProjectManifest` | `settings`, `players`, `shared_packs` |

Public loader: `load_project_manifest(file_path: str | Path) -> ProjectManifest`. The loader uses `yaml.safe_load()`, enforces basic shape/types and required fields, and converts an integer or string `source.external_id` into a **string**. Missing/invalid fields raise Python exceptions during parsing. Fields like `opening_policy` may be omitted; the DTO then holds `None`.

The loader **does not** fetch cards, check distribution totals or validate relationships between players and actual card lists.

## 3. Manifest semantics

### `settings`

`name` is human-readable. `default_opening_policy` must refer to a key defined in `config/policies.yaml`; its existence is checked by `validate_project_configuration()`.

### `players`

Each entry has a globally unique player `key`, display name, one `main_pack` object and **exactly 3** `mini_packs`. The nested position of a pack determines its semantic role; no redundant `type` is needed on personal packs.

During assembly:

| Manifest location | Assigned type | Owner | Parent | Size / booster |
| --- | --- | --- | --- | --- |
| `players[].main_pack` | `PERSONAL_MAIN` | player key | `None` | 100 / 7 |
| `players[].mini_packs[]` | `PERSONAL_MINI` | player key | player's main pack key | 20 / 3 |

`display_name` can change without changing stable pack IDs. **Pack `key` must remain stable** to preserve IDs and YgoMaster per-pack shop/pity state; display names and external source IDs are not stable replacements for that key.

### `shared_packs`

Each entry declares a `type`; currently only `shared_staples` is supported and **exactly one** such pack is required. It has no owner/parent, contains 200 unique cards and opens 11 cards per booster. A shared-pack type is not inferred from a player's hierarchy.

### `source`

```yaml
source:
  provider: "ygoprodeck"
  external_id: "24116"
```

`provider` is currently limited to `ygoprodeck`. `external_id` is the YGOPRODeck custom pack ID, **not** a card passcode and not a YgoMaster shop ID. The loader accepts an integer/string but converts it to a string in the DTO. The YGOPRODeck adapter fetches cards using that ID at build time.

### Optional `opening_policy`

A pack may declare `opening_policy: "configuration-b"` alongside `key` and `source`. If the field is absent/`None`, assembly uses `settings.default_opening_policy`. A specified empty/whitespace-only string is invalid. Referenced policy keys must exist.

## 4. Configuration validation stages

The top-level workflow runs three independent checks before downloading packs:

```python
manifest = load_project_manifest(paths.manifest)
policies = load_policies_config(paths.policies)
validate_project_manifest(manifest)
validate_policies_config(policies)
validate_project_configuration(manifest, policies)
```

`validate_project_manifest()` checks player count, duplicate player/pack keys, exactly three minis, supported sources/types, exactly one staples pack and empty policy keys/overrides. `validate_project_configuration()` checks that the default and per-pack policy references exist. Both return `ValidationReport` objects; the workflow raises `WorkflowError` for reports with errors.

The **card-level** restrictions (main–mini membership/rarity, overlaps, counts, Master Duel ID resolution) cannot be validated from this YAML alone. They are checked after assembly by `validate_project_definition()`; see [Validation](validation.md).

## 5. Editing guidelines

- Keep `key` unchanged when renaming a pack or changing its source ID, unless you explicitly intend to allocate a new numeric YgoMaster pack ID.
- Updating a YGOPRODeck pack may not immediately change its API response. The builder does not cache the response; build against data the endpoint currently supplies.
- The current project supports exactly three minis per player; removing one will produce `invalid-mini-pack-count` before network requests.
- Composition constraints cannot be relaxed by altering `project.yaml` alone; update `rules/` and domain validation together if the league rules change.
- Avoid placing user-specific YgoMaster paths in the manifest. `--ygomaster-dir` is a CLI/runtime parameter.

Related: [Rules and policies](rules-and-policies.md), [Sources and mapping](sources-and-mapping.md), [Workflow and CLI](workflow-and-cli.md).
