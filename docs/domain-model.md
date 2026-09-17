# Domain Model

## 1. Purpose

The domain layer defines the core data model used by **YgoMaster-PackBuilder**.

Its purpose is to represent cards, packs, players, opening policies, external pack references, and the complete project configuration independently from:

* YGOPRODeck API details;
* YAML/JSON manifest formats;
* YgoMaster JSON structures;
* filesystem operations;
* network requests;
* validation logic;
* installation and deployment logic.

The domain layer therefore represents **what the project contains**, not how that data is loaded, validated, exported, or installed.

The package is located under:

```text
src/ygomaster_packbuilder/domain/
```

Current structure:

```text
domain/
├── __init__.py
├── rarity.py
├── card.py
├── source.py
├── pack.py
├── player.py
├── policy.py
└── main.py
```

---

## 2. Design Principles

### 2.1 Domain independence

Domain objects must not depend directly on external systems.

For example, a `PackDefinition` may reference an external source through a `SourcePackRef`, but it must not know how the YGOPRODeck API works.

Similarly, domain objects must not know how YgoMaster represents packs in `Shop.json` or `ShopPackOdds.json`.

These translations belong to dedicated adapters and exporters.

---

### 2.2 Passive data models

Domain objects are intentionally kept simple.

They primarily store data and relationships.

They do not currently implement operations such as:

```text
fetch()
validate()
export()
install()
resolve()
```

These responsibilities belong to other layers.

This allows invalid or incomplete domain objects to exist temporarily during the build pipeline, so that the validation layer can later inspect them and provide meaningful error messages.

---

### 2.3 Stable internal identifiers

Entities that need to be referenced by other objects use stable string keys.

Example:

```text
livio-scaled-invasion
livio-alien
shared-staples
configuration-a
```

Keys must remain independent from:

* display names;
* YGOPRODeck pack IDs;
* YgoMaster shop IDs;
* filesystem paths.

This makes them suitable for long-term references and future ID registries.

---

### 2.4 Explicit relationships

Relations between domain objects are represented using keys instead of direct object references when appropriate.

For example:

```text
PlayerDefinition.main_pack_key
PackDefinition.parent_pack_key
PackDefinition.opening_policy_key
```

This avoids tightly coupled object graphs and simplifies:

* manifest loading;
* serialization;
* validation;
* testing;
* missing-reference detection.

---

## 3. Rarity

Defined in:

```text
domain/rarity.py
```

The `Rarity` enum represents the normalized Master Duel rarity system.

Supported values are:

```text
N
R
SR
UR
```

These correspond to:

```text
Normal
Rare
Super Rare
Ultra Rare
```

The domain layer intentionally does not use YgoMaster's internal numeric representation.

For example, the fact that YgoMaster may encode an Ultra Rare as a numeric value such as `4` is considered an exporter-specific detail.

Likewise, external rarity names such as:

```text
Common
Secret Rare
Collector's Rare
```

are not represented directly by `Rarity`.

They are preserved separately as source metadata and normalized later.

---

## 4. Card

Defined in:

```text
domain/card.py
```

`Card` represents a card imported from an external pack and progressively enriched during the build pipeline.

Conceptually:

```text
Card
├── name
├── ydk_id
├── source_rarity
├── master_duel_id
└── rarity
```

### 4.1 `name`

Human-readable card name.

Example:

```text
"A" Cell Breeding Device
```

The name is metadata and must never be used as the primary identity of the card.

Names may change, contain punctuation, or differ between external sources.

---

### 4.2 `ydk_id`

The YDK/passcode identifier associated with the card.

Example:

```text
34541863
```

This is the primary logical identifier used by YgoMaster-PackBuilder when comparing cards.

Operations such as:

```text
duplicate detection
subset checks
mini-pack overlap checks
```

must compare cards through `ydk_id`.

---

### 4.3 `source_rarity`

The rarity string provided by the external source.

Example:

```text
Common
Secret Rare
```

This value is intentionally preserved even after rarity normalization.

It allows the system to retain the original source information and makes rarity conversion auditable.

---

### 4.4 `rarity`

The normalized domain rarity.

Its type is:

```text
Rarity | None
```

It may initially be `None`.

Example pipeline:

```text
source_rarity = "Secret Rare"
rarity = None
```

After normalization:

```text
source_rarity = "Secret Rare"
rarity = Rarity.UR
```

---

### 4.5 `master_duel_id`

The internal Master Duel/YgoMaster card identifier.

Its type is:

```text
int | None
```

It may initially be unresolved.

Example:

```text
ydk_id = 34541863
master_duel_id = None
```

After resolution through `YdkIds.txt`:

```text
ydk_id = 34541863
master_duel_id = 12345
```

The mapping mechanism itself does not belong to the domain layer.

---

### 4.6 Card lifecycle

A single `Card` object can progressively move through the pipeline:

```text
Imported
│
├── name
├── ydk_id
└── source_rarity
        │
        ▼
Normalized
│
└── rarity
        │
        ▼
Resolved
│
└── master_duel_id
```

Separate classes such as `RawCard`, `NormalizedCard`, and `ResolvedCard` are intentionally not used.

---

### 4.7 Mutability

`Card` is mutable.

This allows fields such as:

```text
rarity
master_duel_id
```

to be populated after the original card has been imported.

---

## 5. External Sources

Defined in:

```text
domain/source.py
```

The source model describes where an externally defined pack comes from.

It consists of:

```text
SourceProvider
SourcePackRef
```

---

### 5.1 `SourceProvider`

`SourceProvider` identifies the external service providing the pack definition.

Currently supported:

```text
YGOPRODECK
```

with serialized value:

```text
ygoprodeck
```

Additional providers may be introduced later without modifying the rest of the domain model.

---

### 5.2 `SourcePackRef`

Represents a stable reference to an external pack.

Conceptually:

```text
SourcePackRef
├── provider
└── external_id
```

Example:

```text
provider = YGOPRODECK
external_id = "24116"
```

`external_id` is stored as a string even when the provider currently exposes numeric IDs.

This avoids coupling the domain model to the identifier format of a specific provider.

---

### 5.3 Immutability

`SourcePackRef` is immutable.

Once created, the source reference should not change.

If a pack is later determined to originate from another external source, a new source reference should be created instead of mutating the original one.

---

## 6. Pack Types

Defined in:

```text
domain/pack.py
```

The `PackType` enum identifies the role of a pack within the project.

Supported pack types are:

```text
PERSONAL_MAIN
PERSONAL_MINI
SHARED_STAPLES
```

Serialized values:

```text
personal_main
personal_mini
shared_staples
```

Pack type describes the semantic role of a pack.

It does not directly encode:

```text
number of cards
booster size
rarity distribution
```

Those are separate properties or project rules.

---

## 7. PackDefinition

`PackDefinition` represents a complete pack inside the project domain.

Conceptually:

```text
PackDefinition
├── key
├── name
├── description
├── type
├── source
├── expected_card_count
├── booster_size
├── opening_policy_key
├── owner_key
├── parent_pack_key
└── cards
```

---

### 7.1 `key`

Stable internal identifier.

Example:

```text
livio-scaled-invasion
```

This identifier should remain stable even if:

```text
the pack display name changes
the YGOPRODeck ID changes
the YgoMaster shop ID changes
```

The key will later be used by the YgoMaster ID registry.

---

### 7.2 `name`

Human-readable pack name.

Example:

```text
Scaled Invasion
```

The name may originate from the external provider.

It is display metadata and must not be used as a stable identifier.

---

### 7.3 `description`

Human-readable pack description.

This may also originate from the source provider.

---

### 7.4 `type`

The semantic role of the pack.

Possible values:

```text
PERSONAL_MAIN
PERSONAL_MINI
SHARED_STAPLES
```

---

### 7.5 `source`

Reference to the external pack definition.

Type:

```text
SourcePackRef
```

The pack itself does not perform any network request.

---

### 7.6 `expected_card_count`

Expected number of unique cards contained in the pack.

Current project rules are:

```text
PERSONAL_MAIN     100
PERSONAL_MINI      20
SHARED_STAPLES    200
```

These values are stored in the domain object but their correctness is enforced by the validation layer.

---

### 7.7 `booster_size`

Number of cards opened from one booster.

Current project rules are:

```text
PERSONAL_MAIN       7
PERSONAL_MINI       3
SHARED_STAPLES     11
```

The domain model does not automatically derive this value from `PackType`.

---

### 7.8 `opening_policy_key`

References the opening policy used by the pack.

Example:

```text
configuration-a
```

The actual `OpeningPolicy` object is stored at project level.

---

### 7.9 `owner_key`

Identifies the player that owns a personal pack.

For personal packs:

```text
owner_key = player key
```

For shared packs:

```text
owner_key = None
```

Example:

```text
livio
```

---

### 7.10 `parent_pack_key`

Used to represent the relationship between a personal mini-pack and its main pack.

Example:

```text
livio-alien
    parent_pack_key = livio-scaled-invasion
```

Main packs and shared packs normally have:

```text
parent_pack_key = None
```

---

### 7.11 `cards`

List of `Card` objects belonging to the pack.

The list is initially allowed to be empty.

Cards are expected to be populated after retrieving the source pack.

---

### 7.12 Mutability

`PackDefinition` is mutable.

Its card collection is populated during the build pipeline.

---

## 8. PlayerDefinition

Defined in:

```text
domain/player.py
```

Represents one player and their personal pack structure.

Conceptually:

```text
PlayerDefinition
├── key
├── display_name
├── main_pack_key
└── mini_pack_keys
```

---

### 8.1 `key`

Stable internal player identifier.

Example:

```text
livio
```

---

### 8.2 `display_name`

Human-readable player name.

Example:

```text
Livio
```

---

### 8.3 `main_pack_key`

References the player's personal main pack.

Example:

```text
livio-scaled-invasion
```

---

### 8.4 `mini_pack_keys`

List of keys referencing the player's personal mini-packs.

Current project rules require exactly three entries.

Example:

```text
livio-alien
livio-venom
livio-ogdoadic
```

The `PlayerDefinition` object itself does not enforce that count.

---

## 9. Opening Policies

Defined in:

```text
domain/policy.py
```

Opening policies describe pack-opening probability rules independently from YgoMaster's storage format.

The policy model contains:

```text
RarityDistribution
TenPackGuarantee
UltraRarePity
OpeningPolicy
```

---

## 10. RarityDistribution

Represents a probability distribution across the four normalized rarities.

Conceptually:

```text
RarityDistribution
├── normal
├── rare
├── super_rare
└── ultra_rare
```

Values are represented as percentages.

Example:

```text
normal      = 55.0
rare        = 35.0
super_rare  = 7.5
ultra_rare  = 2.5
```

The domain model does not itself enforce that the values sum to `100`.

That check belongs to validation.

`RarityDistribution` is immutable.

---

## 11. TenPackGuarantee

Represents the special rarity distribution applied to the final slot of the final pack in a ten-pack opening.

Conceptually:

```text
TenPackGuarantee
├── enabled
└── final_slot_distribution
```

Current Configuration A uses:

```text
N    0%
R    0%
SR  80%
UR  20%
```

This ensures that a ten-pack opening always contains at least one SR or UR in its guaranteed slot.

`TenPackGuarantee` is immutable.

---

## 12. UltraRarePity

Represents the Ultra Rare pity rule.

Conceptually:

```text
UltraRarePity
├── enabled
├── trigger_after_ten_pack_without_ur
└── guaranteed_slot_distribution
```

The current rule is:

```text
A ten-pack opening produces no UR
        │
        ▼
That pack is marked for UR pity
        │
        ▼
The next ten-pack opening of the same pack
uses a guaranteed UR final slot
```

The pity is conceptually scoped to:

```text
player + pack
```

YgoMaster already maintains this state internally.

YgoMaster-PackBuilder therefore describes the policy but does not track runtime pity state.

Current guaranteed pity distribution:

```text
N     0%
R     0%
SR    0%
UR  100%
```

`UltraRarePity` is immutable.

---

## 13. OpeningPolicy

Combines all pack-opening rules into one reusable configuration.

Conceptually:

```text
OpeningPolicy
├── key
├── normal_slot_distribution
├── ten_pack_guarantee
└── ultra_rare_pity
```

The current project uses:

```text
configuration-a
```

with the following rules.

Normal slots:

```text
N   55%
R   35%
SR  7.5%
UR  2.5%
```

Ten-pack final guaranteed slot:

```text
SR  80%
UR  20%
```

UR pity final slot:

```text
UR 100%
```

Opening policies are immutable and intended to be shared between multiple packs.

---

## 14. ProjectDefinition

Defined in:

```text
domain/main.py
```

`ProjectDefinition` is the root object of the domain model.

Conceptually:

```text
ProjectDefinition
├── name
├── players
├── packs
└── opening_policies
```

---

### 14.1 `name`

Human-readable name for the complete project.

Example:

```text
Master Duel Custom League
```

---

### 14.2 `players`

List of all `PlayerDefinition` objects.

---

### 14.3 `packs`

Flat list containing every pack in the project.

This includes:

```text
personal main packs
personal mini-packs
shared staple packs
```

Pack categories are distinguished through `PackType`.

---

### 14.4 `opening_policies`

List containing the available `OpeningPolicy` definitions.

Packs reference policies through `opening_policy_key`.

---

## 15. Domain Relationships

The complete object graph can be represented as:

```text
ProjectDefinition
│
├── PlayerDefinition[]
│   │
│   ├── main_pack_key ─────────────┐
│   └── mini_pack_keys[] ───────┐  │
│                               │  │
├── PackDefinition[]             │  │
│   │                            │  │
│   ├── PERSONAL_MAIN ◄──────────┘──┘
│   │
│   ├── PERSONAL_MINI
│   │     └── parent_pack_key ─────► PERSONAL_MAIN
│   │
│   └── SHARED_STAPLES
│
├── OpeningPolicy[]
│   ▲
│   │
│   └── PackDefinition.opening_policy_key
│
└── Cards
      ├── ydk_id
      ├── master_duel_id
      ├── source_rarity
      └── rarity
```

External packs are referenced through:

```text
PackDefinition
    │
    └── SourcePackRef
          ├── SourceProvider
          └── external_id
```

---

## 16. Current Project Invariants

The following rules belong to the validation layer and are not automatically enforced by the dataclasses.

### 16.1 Player structure

Each player must have:

```text
1 PERSONAL_MAIN pack
3 PERSONAL_MINI packs
```

---

### 16.2 Main packs

A `PERSONAL_MAIN` pack must contain:

```text
100 unique cards
```

with rarity distribution:

```text
50 N
25 R
15 SR
10 UR
```

A booster contains:

```text
7 cards
```

---

### 16.3 Mini-packs

Each `PERSONAL_MINI` pack must contain:

```text
20 unique cards
```

with rarity distribution:

```text
10 N
5 R
3 SR
2 UR
```

A booster contains:

```text
3 cards
```

Every mini-pack must belong to exactly one player and reference that player's main pack.

Every card in a mini-pack must also exist in its parent main pack.

Formally:

```text
cards(mini) ⊆ cards(main)
```

For every card contained in both:

```text
rarity(mini, card) = rarity(main, card)
```

---

### 16.4 Sibling mini-pack disjointness

Mini-packs belonging to the same main pack must not contain duplicate cards.

Given sibling mini-packs:

```text
M1
M2
M3
```

the rule is:

```text
M1 ∩ M2 = ∅
M1 ∩ M3 = ∅
M2 ∩ M3 = ∅
```

More generally:

```text
Mi ∩ Mj = ∅
for every i ≠ j
```

Card equality for this validation is determined through:

```text
Card.ydk_id
```

Since each mini-pack currently contains 20 cards, the three mini-packs together cover exactly:

```text
60 distinct cards
```

out of the 100 cards contained in the parent main pack.

The remaining 40 cards are available only through the main pack.

---

### 16.5 Shared staples pack

A `SHARED_STAPLES` pack must contain:

```text
200 unique cards
```

with rarity distribution:

```text
100 N
50 R
30 SR
20 UR
```

A booster contains:

```text
11 cards
```

Shared packs do not have an owner or parent pack.

---

### 16.6 Card identifiers

Every card must eventually have:

```text
ydk_id
master_duel_id
```

A missing `master_duel_id` is allowed during intermediate pipeline stages but must be resolved before YgoMaster export.

---

### 16.7 Keys

Player, pack, and policy keys must be stable.

Pack keys must be globally unique within a project.

Player keys must be unique within a project.

Opening policy keys must be unique within a project.

Referenced keys must resolve to existing objects before export.

---

### 16.8 Opening policy

Every pack must reference an existing opening policy.

For Configuration A:

Normal slot:

```text
55% N
35% R
7.5% SR
2.5% UR
```

Ten-pack guarantee:

```text
80% SR
20% UR
```

UR pity:

```text
100% UR
```

---

## 17. Mutability Summary

The current mutability policy is:

```text
Card
    mutable

PackDefinition
    mutable

PlayerDefinition
    mutable

ProjectDefinition
    mutable

SourcePackRef
    immutable

RarityDistribution
    immutable

TenPackGuarantee
    immutable

UltraRarePity
    immutable

OpeningPolicy
    immutable
```

Mutable objects represent data that may be progressively assembled during the build process.

Immutable objects represent stable configuration values or references.

---

## 18. Responsibilities Outside the Domain Layer

The domain package must not directly implement the following responsibilities.

```text
Manifest parsing
    → manifest/

YGOPRODeck HTTP requests
    → sources/

YGOPRODeck response normalization
    → sources/ or mapping/

YDK → Master Duel ID conversion
    → mapping/

External rarity → Rarity conversion
    → mapping/ or rules/

Project validation
    → validation/

Pack-size and rarity rules
    → rules/

YgoMaster JSON generation
    → exporters/

Generated file installation
    → install/

Command-line interface
    → cli/
```

This separation keeps the domain model independent from infrastructure details.

---

## 19. Intended Build Pipeline

The domain layer sits at the center of the complete build process.

```text
Project Manifest
       │
       ▼
Manifest Loader
       │
       ▼
External Pack References
       │
       ▼
YGOPRODeck Source Adapter
       │
       ▼
Cards and Pack Metadata
       │
       ▼
Rarity Normalization
       │
       ▼
YDK → Master Duel ID Resolution
       │
       ▼
Domain Model
       │
       ▼
Validation
       │
       ▼
YgoMaster Export
       │
       ▼
Generated Build
       │
       ▼
Installation
```

The domain model acts as the internal representation shared by all later stages.

---

## 20. Current Scope

The domain layer currently supports the requirements of the first YgoMaster-PackBuilder version:

```text
personal 100-card main packs
three 20-card targeted mini-packs per player
one shared 200-card staples pack
YGOPRODeck pack references
Master Duel rarity normalization
YDK → Master Duel ID enrichment
custom pack opening policies
ten-pack SR/UR guarantee
per-pack UR pity
```

Additional features should only be added to the domain model when required by an actual project feature.

The model should remain as small and explicit as possible.
