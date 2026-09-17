# Project Manifest

## 1. Purpose

The project manifest defines the high-level structure of a YgoMaster-PackBuilder project.

Its purpose is to describe:

* the project metadata;
* the players participating in the project;
* each player's personal main pack;
* each player's personal mini-packs;
* shared packs;
* the external source used for each pack;
* the default opening policy;
* optional per-pack opening policy overrides.

The manifest intentionally does **not** contain card data, normalized rarities, Master Duel IDs, pack size rules, or YgoMaster-specific output fields.

Those values are either:

* retrieved from external sources;
* derived from project rules;
* resolved later in the build pipeline;
* stored in other configuration files.

The project manifest is therefore a **declarative project description**, not a complete domain representation.

---

## 2. File Location

The default manifest file is:

```text
config/project.yaml
```

It is loaded through:

```text
ygomaster_packbuilder.manifest.load_project_manifest(...)
```

The YAML document is first parsed into manifest DTOs and is not converted directly into domain objects.

The current flow is:

```text
project.yaml
    ↓
PyYAML
    ↓
Manifest DTOs
    ↓
Manifest validation
    ↓
Cross-validation
    ↓
Later build stages
```

---

## 3. Root Structure

The manifest currently contains three top-level sections:

```yaml
project:
  ...

players:
  ...

shared_packs:
  ...
```

Conceptually:

```text
ProjectManifest
├── settings
├── players[]
└── shared_packs[]
```

The corresponding manifest DTOs are defined in:

```text
src/ygomaster_packbuilder/manifest/models.py
```

---

## 4. Project Section

The `project` section contains global project settings.

Example:

```yaml
project:
  name: "Master Duel Custom League"
  default_opening_policy: "configuration-a"
```

It is represented internally by the project settings DTO.

---

### 4.1 `name`

Human-readable project name.

Example:

```text
Master Duel Custom League
```

The project name is metadata and is not used as an internal identifier.

---

### 4.2 `default_opening_policy`

Key of the opening policy used by packs that do not explicitly define an override.

Example:

```yaml
default_opening_policy: "configuration-a"
```

The referenced policy must exist in:

```text
config/policies.yaml
```

The existence of the referenced policy is checked during cross-validation.

---

## 5. Players

Players are declared under:

```yaml
players:
```

Example:

```yaml
players:
  - key: "livio"
    display_name: "Livio"

    main_pack:
      ...

    mini_packs:
      ...
```

Each player contains:

```text
key
display_name
main_pack
mini_packs[]
```

---

### 5.1 Player `key`

Stable internal identifier for the player.

Example:

```text
livio
```

Player keys must be unique within the project.

They should be:

* stable;
* lowercase where practical;
* independent from display names;
* suitable for references from other project structures.

Example:

```text
livio
player-two
alice
```

---

### 5.2 `display_name`

Human-readable player name.

Example:

```text
Livio
```

This field is display metadata and is not used as a stable identifier.

---

## 6. Main Packs

Each player defines exactly one `main_pack`.

Example:

```yaml
main_pack:
  key: "livio-scaled-invasion"

  source:
    provider: "ygoprodeck"
    external_id: "24116"
```

The fact that the pack is located under:

```text
players[].main_pack
```

already identifies it as a personal main pack.

The manifest therefore does not require:

```yaml
type: "personal_main"
```

This avoids redundant or contradictory declarations.

---

### 6.1 Derived main-pack properties

The following values are not written in the manifest:

```text
type
owner_key
parent_pack_key
expected_card_count
booster_size
```

They will later be derived from the manifest structure and project rules.

For a personal main pack:

```text
type                = PERSONAL_MAIN
owner_key           = player key
parent_pack_key     = None
expected_card_count = 100
booster_size        = 7
```

---

## 7. Mini-Packs

Each player defines their mini-packs under:

```yaml
mini_packs:
```

Example:

```yaml
mini_packs:
  - key: "livio-alien"
    source:
      provider: "ygoprodeck"
      external_id: "24117"

  - key: "livio-venom"
    source:
      provider: "ygoprodeck"
      external_id: "24118"

  - key: "livio-ogdoadic"
    source:
      provider: "ygoprodeck"
      external_id: "24119"
```

Each player currently requires exactly:

```text
3 mini-packs
```

This rule is checked by the manifest validation layer.

---

### 7.1 Derived mini-pack properties

The manifest does not explicitly define:

```text
type
owner_key
parent_pack_key
expected_card_count
booster_size
```

For a mini-pack, these values will later be derived as:

```text
type                = PERSONAL_MINI
owner_key           = player key
parent_pack_key     = player's main pack key
expected_card_count = 20
booster_size        = 3
```

The parent relationship therefore comes from the manifest hierarchy rather than from a duplicated YAML field.

---

## 8. Shared Packs

Shared packs are declared under:

```yaml
shared_packs:
```

Example:

```yaml
shared_packs:
  - key: "shared-staples"
    type: "shared_staples"

    source:
      provider: "ygoprodeck"
      external_id: "25000"
```

Unlike personal packs, shared packs explicitly declare a `type`.

This allows the shared-pack section to support additional shared pack categories in the future.

---

### 8.1 Current supported shared pack type

Currently supported:

```text
shared_staples
```

This maps to the domain value:

```text
PackType.SHARED_STAPLES
```

The current project requires exactly one shared staples pack.

---

### 8.2 Derived staples properties

For a shared staples pack:

```text
owner_key           = None
parent_pack_key     = None
expected_card_count = 200
booster_size        = 11
```

These values are not duplicated in the manifest.

---

## 9. Pack Sources

Every pack must declare an external source.

Example:

```yaml
source:
  provider: "ygoprodeck"
  external_id: "24116"
```

This is represented by:

```text
ManifestPackSource
├── provider
└── external_id
```

---

### 9.1 `provider`

Identifies the external source adapter.

Currently supported:

```text
ygoprodeck
```

The value remains a string in the manifest DTO.

It is not converted directly to `SourceProvider` during parsing.

This allows the validation layer to report unsupported providers explicitly.

---

### 9.2 `external_id`

Identifier used by the external provider.

For YGOPRODeck custom packs this corresponds to the pack ID.

Example:

```text
24116
```

The internal representation is always a string:

```text
"24116"
```

even when the external system currently uses numeric identifiers.

This keeps the manifest model independent from provider-specific ID formats.

---

## 10. Opening Policy Inheritance

Opening policy selection follows an inheritance rule.

The project defines:

```yaml
project:
  default_opening_policy: "configuration-a"
```

A pack may optionally override it:

```yaml
main_pack:
  key: "some-pack"
  opening_policy: "another-policy"
```

---

### 10.1 No override

If:

```text
opening_policy = None
```

the pack inherits:

```text
project.default_opening_policy
```

This is the normal and expected behavior.

It does not generate a validation warning or error.

---

### 10.2 Explicit override

If a pack declares:

```yaml
opening_policy: "configuration-b"
```

that policy is used instead of the project default.

The referenced policy must exist in:

```text
config/policies.yaml
```

---

### 10.3 Empty override

An explicitly empty override is invalid.

Examples:

```yaml
opening_policy: ""
```

or a whitespace-only value are rejected.

This is different from an omitted field.

Conceptually:

```text
None
→ inherit default
→ valid

"configuration-a"
→ explicit override
→ valid if policy exists

""
→ explicit but empty override
→ invalid
```

---

## 11. Key Requirements

Keys are used as stable internal identifiers.

They must not depend on mutable external metadata.

Pack keys should normally use a format similar to:

```text
livio-scaled-invasion
livio-alien
livio-venom
shared-staples
```

They should be:

* stable over time;
* human-readable;
* independent from YGOPRODeck IDs;
* independent from display names;
* independent from future YgoMaster numeric IDs.

---

### 11.1 Player key uniqueness

Player keys must be unique within the project.

Invalid:

```yaml
players:
  - key: "livio"
  - key: "livio"
```

Validation code:

```text
duplicate-player-key
```

---

### 11.2 Pack key uniqueness

Pack keys must be globally unique across:

```text
main packs
mini-packs
shared packs
```

A main pack and a shared pack therefore cannot reuse the same key.

Validation code:

```text
duplicate-pack-key
```

---

## 12. Derived Values

The manifest intentionally omits information that can be derived from project structure or rules.

Current derived pack rules are:

```text
PERSONAL_MAIN
    expected cards = 100
    booster size   = 7

PERSONAL_MINI
    expected cards = 20
    booster size   = 3

SHARED_STAPLES
    expected cards = 200
    booster size   = 11
```

These values should not be repeated manually inside `project.yaml`.

This avoids configurations such as:

```text
type = PERSONAL_MINI
expected_card_count = 100
```

where two fields contradict each other.

---

## 13. Data Not Stored in the Manifest

The project manifest does not contain:

```text
card names
card lists
source rarities
normalized rarities
Master Duel IDs
rarity distributions for pack contents
pack-opening probabilities
YgoMaster shop IDs
YgoMaster JSON structures
```

These are provided by other parts of the system.

---

### 13.1 External pack metadata

Fields such as:

```text
pack name
pack description
cards
source rarity
```

are retrieved from the external source adapter.

For YGOPRODeck, these will come from the custom pack source.

---

### 13.2 Opening policy definitions

Opening probability rules are defined separately in:

```text
config/policies.yaml
```

The project manifest only references policy keys.

---

### 13.3 Domain pack properties

Values such as:

```text
PackType
owner_key
parent_pack_key
expected_card_count
booster_size
```

are derived later during project assembly.

---

## 14. Manifest Loading

The manifest loader converts YAML into manifest DTOs.

Public entry point:

```python
load_project_manifest(path)
```

Conceptually:

```text
project.yaml
    ↓
yaml.safe_load(...)
    ↓
Python mappings/lists
    ↓
ManifestPackSource
ManifestPack
ManifestSharedPack
ManifestPlayer
ManifestProjectSettings
ProjectManifest
```

The loader handles structural parsing only.

---

## 15. Loader Responsibilities

The loader is responsible for structural problems such as:

```text
file does not exist
YAML root is not a mapping
required fields are missing
players is not structurally parseable
source is malformed
```

The loader does not determine whether the resulting project configuration is semantically valid.

That responsibility belongs to the validation layer.

---

## 16. Manifest Validation

Manifest validation is performed separately through:

```python
validate_project_manifest(...)
```

It produces a:

```text
ValidationReport
```

containing zero or more:

```text
ValidationIssue
```

Validation does not stop after the first error.

Multiple problems can therefore be reported in a single run.

---

## 17. Current Manifest Validation Rules

The current validator checks the following rules.

---

### 17.1 At least one player

A project must define at least one player.

Validation code:

```text
no-players
```

---

### 17.2 Unique player keys

Player keys must not be repeated.

Validation code:

```text
duplicate-player-key
```

---

### 17.3 Exactly three mini-packs

Each player must define exactly three mini-packs.

Validation code:

```text
invalid-mini-pack-count
```

The fact that every player has exactly one main pack is already structurally enforced by the DTO:

```text
ManifestPlayer.main_pack
```

and therefore does not require a separate list-count validation.

---

### 17.4 Globally unique pack keys

Pack keys must be unique across all pack categories.

Validation code:

```text
duplicate-pack-key
```

---

### 17.5 Supported source provider

Every pack source provider must be supported.

Currently:

```text
ygoprodeck
```

Validation code:

```text
unsupported-source-provider
```

---

### 17.6 Supported shared-pack type

Shared pack types must be recognized.

Currently:

```text
shared_staples
```

Validation code:

```text
unsupported-shared-pack-type
```

---

### 17.7 Exactly one shared staples pack

The current project rules require exactly one:

```text
shared_staples
```

pack.

Validation code:

```text
invalid-shared-staples-count
```

---

### 17.8 Default opening policy must not be empty

The project-level default policy key must contain a value.

Validation code:

```text
empty-default-opening-policy
```

Its existence is checked later during cross-validation.

---

### 17.9 Explicit pack override must not be empty

An omitted override is valid.

An explicitly empty override is not.

Validation code:

```text
empty-opening-policy
```

---

## 18. Cross-Validation with Policies

Some rules cannot be checked by looking at `project.yaml` alone.

These checks require both:

```text
ProjectManifest
PoliciesConfig
```

and are performed through:

```python
validate_project_configuration(...)
```

---

### 18.1 Default policy must exist

The value referenced by:

```text
project.default_opening_policy
```

must exist among the policy definitions loaded from:

```text
config/policies.yaml
```

Validation code:

```text
unknown-default-opening-policy
```

---

### 18.2 Pack overrides must exist

If a pack explicitly defines an opening policy override, the referenced policy must exist.

Validation code:

```text
unknown-opening-policy
```

This applies to:

```text
main packs
mini-packs
shared packs
```

---

## 19. Validation Layers

The current configuration validation pipeline is intentionally separated into three levels.

```text
project.yaml
    ↓
Manifest Loader
    ↓
ProjectManifest
    ↓
Manifest Validation
```

and:

```text
policies.yaml
    ↓
Policies Loader
    ↓
PoliciesConfig
    ↓
Policies Validation
```

followed by:

```text
ProjectManifest
      +
PoliciesConfig
      ↓
Cross-Validation
```

This separation makes it possible to distinguish:

```text
errors inside project.yaml
errors inside policies.yaml
errors caused by references between the two files
```

---

## 20. Example Manifest

A simplified project manifest may look like:

```yaml
project:
  name: "Master Duel Custom League"
  default_opening_policy: "configuration-a"

players:
  - key: "livio"
    display_name: "Livio"

    main_pack:
      key: "livio-scaled-invasion"
      source:
        provider: "ygoprodeck"
        external_id: "24116"

    mini_packs:
      - key: "livio-alien"
        source:
          provider: "ygoprodeck"
          external_id: "24117"

      - key: "livio-venom"
        source:
          provider: "ygoprodeck"
          external_id: "24118"

      - key: "livio-ogdoadic"
        source:
          provider: "ygoprodeck"
          external_id: "24119"

shared_packs:
  - key: "shared-staples"
    type: "shared_staples"

    source:
      provider: "ygoprodeck"
      external_id: "25000"
```

All packs in this example inherit:

```text
configuration-a
```

because none declares an explicit `opening_policy` override.

---

## 21. Relationship to the Domain Layer

The manifest DTOs are not domain objects.

For example:

```text
ManifestPack
```

does not contain enough information to construct a complete:

```text
PackDefinition
```

because the following data may still be missing:

```text
pack name
pack description
cards
source rarities
normalized rarities
Master Duel IDs
```

The intended build flow is therefore:

```text
ProjectManifest
      │
      ├── structural project information
      │
      ▼
External source adapters
      │
      ├── pack metadata
      └── cards
      │
      ▼
Rules and mapping
      │
      ▼
Domain objects
```

The manifest should remain focused on project declaration rather than becoming a duplicate serialized version of the entire domain model.

---

## 22. Current Scope

The manifest format currently supports:

```text
project metadata
default opening policy
multiple players
one main pack per player
three mini-packs per player
shared packs
YGOPRODeck source references
optional per-pack opening-policy overrides
```

Additional fields should only be added when they represent information that:

1. must be explicitly configured by the user;
2. cannot be reliably derived elsewhere;
3. belongs logically to project declaration rather than runtime/build output.

This keeps `project.yaml` small, readable, and resistant to contradictory configuration.
