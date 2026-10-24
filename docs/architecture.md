# Architecture

## 1. Purpose and boundaries

YgoMaster-PackBuilder is a Python 3.11+ pipeline for translating externally curated YGOPRODeck custom packs into files consumed by an **existing** pixeltris/YgoMaster installation. It does not modify YgoMaster source code, implement the game/server, create custom card assets, or configure online PvP networking.

The separation between **source data**, **domain configuration**, **validated build artifacts** and **installed files** is intentional. Every transformation has a focused module and the top-level workflow coordinates it.

## 2. Repository layout

```text
config/
  project.yaml                 # league and source references
  policies.yaml                # opening policies
  rarity_mapping.yaml          # source rarity -> N/R/SR/UR rules
state/
  ygomaster_ids.json           # persisted, versioned pack ID registry
build/
  Shop/ygomaster-packbuilder.json
  ShopPackOdds/ygomaster-packbuilder.json
  ShopSettings.patch.json
src/ygomaster_packbuilder/
  manifest/                    # YAML -> ProjectManifest DTOs
  policies/                    # YAML -> PoliciesConfig DTOs, domain conversion
  sources/ygoprodeck/          # HTTP client, parser and card conversion
  mapping/                     # rarity normalization; YDK ID resolution
  rules/                       # pack size, booster size and composition
  domain/                      # card, pack, player, policy, project objects
  assembly/                    # pack and project construction
  validation/                  # config/domain/build diagnostics
  registry/                    # stable pack ID allocation
  exporters/ygomaster/         # shop/odds payloads and JSON writer
  installer/                   # state, backup, install and uninstall
  workflow.py                  # orchestration
  cli.py                       # terminal interface
tests/                        # manual Jupyter notebooks, no pytest runner
```

The generated `build/` contents are ignored by Git. `state/ygomaster_ids.json` is deliberately **not ignored** and should be shared between builders so a pack key retains the same ID on different machines.

## 3. Runtime data flow

```text
config/project.yaml             config/policies.yaml
         |                               |
   load_project_manifest()       load_policies_config()
         |                               |
  validate_project_manifest()     validate_policies_config()
         +-------------+-----------------+
                       |
             validate_project_configuration()
                       |
config/rarity_mapping.yaml       YgoMaster/Data/YdkIds.txt
         |                               |
  load_rarity_mapping()            load_ydk_mapping()
         +---------------+---------------+
                         |
         assemble_project_definition() <--- YgoProDeckClient
                         |
             ProjectDefinition
                         |
          validate_project_definition()
                         |
            load_id_registry()
          ensure_project_pack_ids()
                         |
           write staged artifacts
          validate staged build
                         |
          write final build files
          validate final build
                         |
             save_id_registry()
                         |
            BuildWorkflowResult
                         |
                    [optional]
         install_ygomaster_build()
                         |
         Data/Shop/*.json; Data/ShopPackOdds/*.json
         patch Data/Shop.json; persist local state
```

For `build_and_install_project()`, installation calls `validate_ygomaster_build()` again and then installs. `uninstall_ygomaster_build()` is a separate operation using **local installation state**, not the manifest or live YGOPRODeck data.

## 4. Layer contracts

| Layer | Input | Output / responsibility | Does not do |
| --- | --- | --- | --- |
| `manifest/` | `project.yaml` | `ProjectManifest` DTOs | Fetch cards or assign IDs |
| `policies/` | `policies.yaml` | `PoliciesConfig`, then domain policies | Open packs at runtime |
| `sources/ygoprodeck/` | Source ID and HTTP response | `YgoProDeckPackData` | Know pack ownership or shop IDs |
| `mapping/` | Cards + mappings | Normalized rarity and resolved MD IDs | Silently invent missing IDs |
| `rules/` | `PackType` | Static `PackRule` | Read manifest |
| `assembly/` | DTOs, source payloads, mappings | `ProjectDefinition` | Enforce all semantic rules |
| `validation/` | DTOs/domain/output | Accumulated `ValidationReport` | Fix source data |
| `registry/` | Pack keys + registry state | Stable numeric pack IDs | Generate shop JSON |
| `exporters/` | Domain objects + IDs | YgoMaster shop/odds/patch JSON | Install into game directory |
| `installer/` | Validated build and YgoMaster root | Managed modular files + local restore state | Build cards from sources |
| `workflow.py` | PackBuilder and YgoMaster roots | Ordered end-to-end steps | Implement per-layer parsing rules |
| `cli.py` | Command-line arguments | Run workflow/uninstall, print results | Reimplement business logic |

Domain dataclasses are passive and do not fetch, validate or export themselves. The assembly stage is allowed to create incomplete objects so domain validation can report multiple issues at once.

## 5. Validation and failure boundaries

The workflow validates the manifest, policies and cross-references **before** making YGOPRODeck requests. It then validates the fully assembled project before touching the pack ID registry/build files. No unresolved `master_duel_id` may pass domain validation.

`ensure_project_pack_ids()` mutates the loaded registry object **in memory**. The workflow writes the registry to disk only after validating the final build. It first writes and validates a temporary staging build, then writes and validates the final `build/` artifacts.

**Important limitation:** staging reduces the chance of exporting invalid data but does not make the final build directory or install a multi-file transaction. The JSON writer atomically replaces individual files; a failure between files can leave mixed old/new contents. The registry save is also a separate operation. Re-run after resolving the failure and validate the outputs before installation.

A failed `install` command can leave a successful new build/registry even if the later target installation fails. Local installer backup/state logic protects managed files from accidental manual overwrite but is not an OS-level transaction across multiple files.

## 6. Cross-platform model

The Python builder uses `pathlib.Path` and is natively usable on Windows/Linux. The only expected YgoMaster layout is a root directory containing `Data/YdkIds.txt` for build, and `Data/Shop.json` for install. The installer derives `Data/Shop/` and `Data/ShopPackOdds/` itself. No CLI argument for each individual JSON file is needed.

YgoMaster's game/server execution, including any Windows/Wine arrangement, remains external to the builder. The builder does not synchronize installations, configure Tailscale or guarantee server/client runtime compatibility; those are deployment/runtime tasks.

## 7. Related documents

See [Manifest](manifest.md), [Domain](domain-model.md), [Rules and policies](rules-and-policies.md), [Validation](validation.md), [Export and install](ygomaster-export-and-install.md), and [Workflow/CLI](workflow-and-cli.md).
