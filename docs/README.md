# Technical documentation

The documentation reflects the Python code under `src/ygomaster_packbuilder/` and the checked-in configuration as reviewed in October 2026. It is intended for maintainers and focuses on **medium-/low-level behavior**, not end-user installation instructions (see the root [README](../README.md)).

| Document | Contents |
| --- | --- |
| [Architecture](architecture.md) | Layer boundaries, dependencies, data flow and failure boundaries |
| [Manifest](manifest.md) | Project YAML schema, DTO loading, structural and semantic checks |
| [Domain model](domain-model.md) | Dataclasses, relationships, mutable/immutable fields |
| [Pack rules and policies](rules-and-policies.md) | League invariants, rarity compositions, slot odds, pity representation |
| [Sources and mappings](sources-and-mapping.md) | YGOPRODeck adapter, rarity normalization and YDK mapping |
| [Validation](validation.md) | ValidationReport, major invariants and issue codes |
| [YgoMaster export and install](ygomaster-export-and-install.md) | Shop/odds JSON, ID registry, writer, patching, backups and uninstall |
| [Workflow and CLI](workflow-and-cli.md) | Orchestration APIs, arguments, error handling, side effects and test strategy |

**Scope:** This tool builds shop packs for an existing YgoMaster installation. It does not operate YgoMaster's network stack or implement multiplayer/PvP transport. Static code review and offline notebook tests do not replace verification of the generated data against the installed YgoMaster runtime.
