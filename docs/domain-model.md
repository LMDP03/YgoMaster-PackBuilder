# Domain model

## 1. Scope

The package `src/ygomaster_packbuilder/domain/` defines the intermediate representation used after importing cards and before exporting YgoMaster JSON. It contains **no HTTP logic, YAML parsing, filesystem writes or validation methods**. Object construction and domain validation are separate.

```text
domain/
  rarity.py    Rarity
  card.py      Card
  source.py    SourceProvider, SourcePackRef
  pack.py      PackType, PackDefinition
  player.py    PlayerDefinition
  policy.py    RarityDistribution, TenPackGuarantee, UltraRarePity, OpeningPolicy
  project.py   ProjectDefinition
```

## 2. Enums and identifiers

`Rarity(StrEnum)` contains `N`, `R`, `SR`, `UR`. The names are independent of YGOPRODeck source rarity strings and of YgoMaster's integer rarity codes. Conversion to YgoMaster integers `1..4` occurs in `exporters/ygomaster/shop.py`.

`SourceProvider(StrEnum)` currently contains `YGOPRODECK = "ygoprodeck"`. `PackType(StrEnum)` contains `PERSONAL_MAIN = "personal_main"`, `PERSONAL_MINI = "personal_mini"` and `SHARED_STAPLES = "shared_staples"`.

**Do not confuse three IDs:**

- `Card.ydk_id`: card passcode from YGOPRODeck, used for card identity, set comparisons and mapping lookup.
- `Card.master_duel_id`: YgoMaster-internal card ID resolved through `YdkIds.txt`, used in exported `cardList` and icon fields.
- YgoMaster `packId` / absolute `shopId`: numeric pack/shop IDs allocated by `registry/` from the stable string `PackDefinition.key`.

## 3. Dataclasses

### `Card` — mutable

```python
@dataclass(slots=True)
class Card:
    name: str
    ydk_id: int
    source_rarity: str
    master_duel_id: int | None = None
    rarity: Rarity | None = None
```

Cards enter assembly with name/passcode/original rarity. `mapping.normalize_cards()` assigns `rarity` and `mapping.resolve_cards_master_duel_ids()` assigns `master_duel_id` when found. Missing mapping leaves `None`; the domain validator rejects it before export. The source rarity string is retained even after normalization for auditability.

### `SourcePackRef` — immutable

```python
@dataclass(slots=True, frozen=True)
class SourcePackRef:
    provider: SourceProvider
    external_id: str
```

The external source ID is normalized to a string by the manifest loader and carried into the domain reference. Neither the external ID nor the display name should be used as the stable internal pack key.

### `PackDefinition` — mutable

```python
@dataclass(slots=True)
class PackDefinition:
    key: str
    name: str
    description: str
    type: PackType
    source: SourcePackRef
    expected_card_count: int
    booster_size: int
    opening_policy_key: str
    owner_key: str | None = None
    parent_pack_key: str | None = None
    cards: list[Card] = field(default_factory=list)
```

`key` is the persistent identity for registry allocation. `name` and `description` come from the source pack; editing these does not allocate a new numeric pack ID. `expected_card_count` and `booster_size` come from `rules.get_pack_rule(pack_type)`, not from YGOPRODeck or the YAML manifest. `owner_key` is set for personal packs, and a mini-pack's `parent_pack_key` points to the player's main pack key. Shared staples has no owner or parent.

### `PlayerDefinition` — mutable

The player stores `key`, `display_name`, `main_pack_key` and `mini_pack_keys: list[str]`. These are **references by stable string key**, not object pointers. The domain validator verifies that referenced packs exist, have the correct role/owner/parent, and obey the sibling mini-pack rules. For a missing main pack, `_validate_player()` intentionally stops checking that player's mini relations after reporting `missing-main-pack`.

### Opening policies — immutable

```python
@dataclass(slots=True, frozen=True)
class RarityDistribution:
    normal: float
    rare: float
    super_rare: float
    ultra_rare: float

@dataclass(slots=True, frozen=True)
class TenPackGuarantee:
    enabled: bool
    final_slot_distribution: RarityDistribution

@dataclass(slots=True, frozen=True)
class UltraRarePity:
    enabled: bool
    guaranteed_slot_distribution: RarityDistribution

@dataclass(slots=True, frozen=True)
class OpeningPolicy:
    key: str
    normal_slot_distribution: RarityDistribution
    ten_pack_guarantee: TenPackGuarantee
    ultra_rare_pity: UltraRarePity
```

Distributions use **percent values**, e.g. `7.5` means 7.5%, not `0.075`. Validation checks totals. `UltraRarePity` has **no** `trigger_after_ten_pack_without_ur` field; trigger/persistence are YgoMaster runtime behavior. This domain only describes the rarity distribution to export.

### `ProjectDefinition` — mutable

```python
@dataclass(slots=True)
class ProjectDefinition:
    name: str
    players: list[PlayerDefinition] = field(default_factory=list)
    packs: list[PackDefinition] = field(default_factory=list)
    opening_policies: list[OpeningPolicy] = field(default_factory=list)
```

`packs` is one flat list containing all personal mains, minis and shared packs. Players and packs link through string keys; packs and policies link by `opening_policy_key`. This makes missing-reference detection explicit.

## 4. Relationships and construction

```text
ProjectDefinition
├── players: PlayerDefinition[]
│     ├── main_pack_key ────────┐
│     └── mini_pack_keys[] ─────┼────────────┐
├── packs: PackDefinition[] ◄───┘            │
│     ├── PERSONAL_MAIN ◄─────────────────────┤ parent_pack_key of minis
│     ├── PERSONAL_MINI ◄─────────────────────┘
│     └── SHARED_STAPLES
├── opening_policies: OpeningPolicy[]
│     ▲       ▲
│     └───────┴── packs[].opening_policy_key
└── cards held by each PackDefinition
```

`assembly/pack.py` selects the rule by `PackType`, converts source cards, normalizes rarity by **pack type**, resolves YDK IDs, selects the policy (override or default), and returns `PackDefinition`. `assembly/project.py` fetches each source pack, creates player + pack relations and converts `PoliciesConfig` to domain opening policies.

Construction does **not** guarantee validity. A project with an unresolved card, wrong card count or overlapping minis is a valid temporary Python object and an **invalid domain project**. `validate_project_definition()` reports those defects before registry/export operations.

## 5. League invariants

The current validated constraints are described fully in [Rules and policies](rules-and-policies.md): main 100 cards, 3 minis of 20 per player, 1 staples pack of 200; normalized rarity composition per type; mini cards belong to the parent main and preserve rarity; sibling minis do not overlap by `ydk_id`; every exported card has a resolved Master Duel ID.

## 6. Responsibility boundaries

- Mutable data: `Card`, `PackDefinition`, `PlayerDefinition`, `ProjectDefinition`.
- Immutable values/references: `SourcePackRef`, `RarityDistribution`, `TenPackGuarantee`, `UltraRarePity`, `OpeningPolicy`.
- Load YAML in `manifest/` and `policies/`; download/parse cards in `sources/`; normalize/enrich in `mapping/`; validate in `validation/`; export in `exporters/`.

There is deliberately **no runtime pity counter** or YgoMaster shop state in the domain object graph.
