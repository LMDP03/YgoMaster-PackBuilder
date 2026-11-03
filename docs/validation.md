# Validation pipeline

## 1. Shared report types

`validation/models.py` defines `ValidationIssue(code, message, path, severity)` and `ValidationReport(issues)`. Severity is an enum (`ERROR`, `WARNING`); `report.errors`, `.warnings` and `.is_valid` derive from the issues list. Validators accumulate issues rather than raising at the first semantic problem. The workflow's `_require_valid()` raises `WorkflowError` if a report contains any error, including its code/path/message.

Structural parser failures (malformed YAML, malformed source response, bad YDK format, some invalid registry fields) **do raise exceptions** instead of reporting a `ValidationIssue`. These are separate from a semantic validation report.

## 2. Stage order

| Stage | Entry point | Responsibility | Happens before |
| --- | --- | --- | --- |
| Manifest | `validate_project_manifest()` | players, source/provider, pack keys/types | any source fetch |
| Policies | `validate_policies_config()` | unique policies, rates/totals, pity | any source fetch |
| Cross-config | `validate_project_configuration()` | default/override policy references | any source fetch |
| Domain | `validate_project_definition()` | full card lists, sizes, rarities, mini relationships and YDK mapping resolution | catalog validation |
| Card catalog | `validate_project_card_catalog()` | resolved MD IDs occur in the installed `Data/CardList.json` | registry allocation/build |
| Build | `validate_ygomaster_build()` | generated JSON structure and exact expected content | installation |

`build_project()` validates the staged and final builds separately. `install_ygomaster_build()` validates its input build again before touching the target YgoMaster directory.

## 3. Manifest validation codes

Implemented in `validation/manifest.py`:

| Code | Meaning |
| --- | --- |
| `no-players` | Empty player list |
| `duplicate-player-key` | Reused player key |
| `invalid-mini-pack-count` | Player does not have exactly 3 minis |
| `duplicate-pack-key` | Same key in main/mini/shared packs |
| `unsupported-source-provider` | Provider other than supported enum |
| `unsupported-shared-pack-type` | Unsupported shared type |
| `invalid-shared-staples-count` | Not exactly one shared staples pack |
| `empty-default-opening-policy` | Empty global policy key |
| `empty-opening-policy` | Explicit empty per-pack override |

`validation/project.py` adds `unknown-default-opening-policy` and `unknown-opening-policy` for references that do not occur in loaded `PoliciesConfig`.

## 4. Policy validation codes

Implemented in `validation/policies.py`:

- `no-policies`, `empty-policy-key`, `duplicate-policy-key`;
- `missing-normal-distribution`, `missing-ten-pack-guarantee`, `missing-ultra-rare-pity`;
- `probability-out-of-range`, `invalid-probability-total`;
- `invalid-ur-pity-distribution` if an enabled pity distribution is not precisely `0/0/0/100`.

`enabled: false` skips probability checking for that disabled feature's distribution; the normal distribution is always checked. The loader requires boolean `enabled` fields, so passing strings/integers may fail before validation.

## 5. Domain validation codes

Implemented in `validation/domain.py`. First, `_validate_unique_keys()` reports `duplicate-player-key`, `duplicate-pack-key` and `duplicate-opening-policy-key` at domain level.

For each pack, `_validate_pack()` checks:

| Code | Check |
| --- | --- |
| `invalid-expected-card-count` | PackDefinition count conflicts with `PackRule` |
| `invalid-booster-size` | Booster size conflicts with `PackRule` |
| `invalid-card-count` | Actual number of card entries not equal to expected count |
| `unknown-opening-policy` | No domain policy matches the pack's key |
| `duplicate-card` | Duplicate `ydk_id` within a pack |
| `unresolved-rarity` | Some `Card.rarity is None` |
| `unresolved-master-duel-id` | Some `Card.master_duel_id is None` |
| `invalid-rarity-composition` | Normalized N/R/SR/UR counts not equal to pack rule |

For players and main/mini relations:

| Code | Check |
| --- | --- |
| `invalid-mini-pack-count` | Exactly 3 required |
| `duplicate-mini-pack-reference` | Player references a mini key multiple times |
| `missing-main-pack` | Main key not found (other mini checks for that player stop here) |
| `invalid-main-pack-type`, `invalid-main-pack-owner`, `main-pack-has-parent` | Main metadata inconsistent |
| `missing-mini-pack` | A referenced mini key is not found |
| `invalid-mini-pack-type`, `invalid-mini-pack-owner`, `invalid-mini-pack-parent` | Mini metadata inconsistent |
| `mini-card-not-in-main` | Mini card's YDK ID absent from the parent main |
| `mini-card-rarity-mismatch` | Same YDK card normalizes to different rarities in main vs mini |
| `mini-pack-overlap` | A card appears in two or more sibling minis |

For shared staples: `invalid-shared-staples-count`, `shared-pack-has-owner`, `shared-pack-has-parent`.

The validator deliberately uses `Card.ydk_id`, not name or `master_duel_id`, for duplicates and main/mini membership comparisons. Export also rejects duplicate *resolved Master Duel IDs* in a single pack.

### Diagnosing source errors

A domain error with `packs.<key>.cards[...]` refers to a card already returned by YGOPRODeck. If you have edited rarities on the website but errors remain unchanged, inspect the current endpoint response: PackBuilder has no cache and a delayed source response can still contain the previous values. A missing Master Duel mapping is a separate problem: it can persist even after all rarity differences are corrected.

### YgoMaster catalog validation

After successful domain validation, `validate_project_card_catalog(project, card_ids)`
checks each resolved `Card.master_duel_id` against keys from the installed
`<YgoMaster>/Data/CardList.json`. The loader requires a nonempty JSON object with
numeric ID keys and rarity values 1–4; those rarity values are **not** compared to
the league's configured per-pack rarities.

| Code | Condition |
| --- | --- |
| `card-not-in-ygomaster-catalog` | Resolved MD ID is absent from the local card catalog |

The issue identifies the source card name, YDK ID, Master Duel ID, pack key
and card path. Missing catalog files and invalid catalog JSON fail before
fetching pack data; missing individual cards fail before writing build artifacts
or updating the stable ID registry. An out-of-date local catalog may also
produce errors, so verify the installed YgoMaster version.

## 6. Build validation codes

Implemented in `validation/ygomaster_build.py`:

| Code | Condition |
| --- | --- |
| `build-file-missing` | Missing one of the 3 required build artifacts |
| `build-invalid-json` | File cannot be parsed as JSON |
| `build-invalid-shop-root`, `build-invalid-pack-shop` | Shop payload is not a dict with `PackShop` mapping |
| `build-invalid-odds-root` | Odds payload is not an array |
| `build-invalid-settings-patch-root`, `build-per-pack-rarities-disabled` | Patch is not an object or lacks `PerPackRarities: true` |
| `build-invalid-odds-entry`, `build-invalid-odds-pack-ids` | Malformed odds entry or `packShopIds` |
| `build-shop-odds-reference-mismatch` | Set of Shop IDs differs from odds references |
| `build-temp-file-present` | A `*.tmp` file exists in the build tree |
| `build-expected-data-error` | Reconstructing the expected export failed |
| `build-shop-content-mismatch`, `build-odds-content-mismatch`, `build-settings-patch-mismatch` | Actual JSON differs from exporter-generated content |

The validator rebuilds expected structures from `(project, pack_ids)` and compares **parsed JSON content**, not raw whitespace/field ordering. It does not perform a live YgoMaster engine compatibility test or compare against unrelated installed mods.

## 7. Additional integrity checks outside the validators

The registry loader rejects duplicate assigned pack IDs and out-of-range IDs; `ensure_project_pack_ids()` rejects duplicate project pack keys. The installer checks existing managed-file SHA-256 hashes against local install state before updates/removal and checks that backups required for restore exist. Installer checks are **filesystem protections**, separate from the build validation reports.

## 8. Testing

The `tests/` directory contains Jupyter notebooks for manifest, policies, conversion, domain rules, exporters, registry, build validation, installer/uninstaller and end-to-end orchestration. Tests are run manually and may use temporary directories or fake clients. There is **no pytest suite/CI harness** wired into the package; do not describe the notebooks as a continuously executed test suite.
