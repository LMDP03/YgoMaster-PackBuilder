# Pack rules and opening policies

## 1. Separate concerns

Two different probability/rarity concepts must not be conflated:

1. **Pack composition** describes which distinct cards (and normalized rarities) are eligible within a pack; enforced by `rules/packs.py` and `validation/domain.py`.
2. **Opening odds** describe how YgoMaster should sample rarities in booster slots; loaded from `config/policies.yaml`, converted to domain policies, then exported to `ShopPackOdds`.

A pack can have exactly 10 UR cards in its card pool while a normal booster slot still has only a 2.5% UR rate.

## 2. Hard-coded pack rules

`rules/packs.py` exposes `PACK_RULES: dict[PackType, PackRule]` and `get_pack_rule(pack_type)`; `PackRule` holds `expected_card_count`, `booster_size` and `RarityComposition`.

| Pack type | Distinct cards | Cards / booster | N | R | SR | UR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `PERSONAL_MAIN` | 100 | 7 | 50 | 25 | 15 | 10 |
| `PERSONAL_MINI` | 20 | 3 | 10 | 5 | 3 | 2 |
| `SHARED_STAPLES` | 200 | 11 | 100 | 60 | 20 | 20 |

All counts are of **distinct cards within the pack**; duplicates by `Card.ydk_id` are rejected. Every mini's 20 cards must exist in the same player's main pack and use the **same normalized rarity** there. The three sibling minis must be pairwise disjoint by `ydk_id`, so they cover 60 distinct main-pack cards. The remaining 40 main cards need not appear in any mini.

The one shared staples pack has no owner or parent. Its normalized 200-card composition is **100 N / 60 R / 20 SR / 20 UR** (not older 100/50/30/20 numbers).

## 3. Context-specific Secret Rare normalization

`config/rarity_mapping.yaml` has global mappings for Common→N, Rare→R, Super Rare→SR, Ultra Rare→UR. It has per-`PackType` overrides for `Secret Rare`:

| Source rarity | Personal main | Personal mini | Shared staples |
| --- | --- | --- | --- |
| `Secret Rare` | N | N | UR |

The override is consulted **before** the global map. Unsupported source rarities raise `ValueError`. The `Card.source_rarity` string remains unchanged; only `Card.rarity` receives the normalized `Rarity` enum.

Because main and mini use the same Secret Rare mapping, the same card can appear in both without a mismatch **only when their source rarities normalize identically**. Changing rarity on YGOPRODeck in one pack but not its main is a domain validation failure.

## 4. Configuration A

`config/policies.yaml` defines `configuration-a`. All rates are **percentages**, validated to sum to 100.

Normal slot:

| N | R | SR | UR |
| ---: | ---: | ---: | ---: |
| 55% | 35% | 7.5% | 2.5% |

A normal single-pack opening is not given a special last-slot rarity distribution by this exporter: the normal row covers slots `1` through `pack.booster_size`.

**Ten-pack guarantee:** when enabled, the final slot of the **tenth** pack has SR 80% / UR 20%:

| N | R | SR | UR |
| ---: | ---: | ---: | ---: |
| 0% | 0% | 80% | 20% |

**UR pity:** if YgoMaster's runtime records a qualifying x10 opening without UR for a player/pack, the following qualifying x10 opening of that same pack gets a UR-only final slot (100% UR). Pity storage, activation and consumption are runtime features, **not** implemented by PackBuilder. `UltraRarePity` contains only `enabled` and `guaranteed_slot_distribution`; there is no old `trigger_after_ten_pack_without_ur` field.

## 5. Policy DTOs, conversion and validation

`policies/loader.py` reads the root `policies: [...]` list and creates `PoliciesConfig` DTOs. `policies/converter.py` creates immutable domain `OpeningPolicy` objects. `validation/policies.py` checks unique nonempty keys, probability bounds, `100.0` totals for active distributions, and the canonical 100% UR pity distribution when pity is enabled.

Example:

```yaml
policies:
  - key: "configuration-a"
    normal_slot_distribution: {normal: 55.0, rare: 35.0, super_rare: 7.5, ultra_rare: 2.5}
    ten_pack_guarantee:
      enabled: true
      final_slot_distribution: {normal: 0, rare: 0, super_rare: 80, ultra_rare: 20}
    ultra_rare_pity:
      enabled: true
      guaranteed_slot_distribution: {normal: 0, rare: 0, super_rare: 0, ultra_rare: 100}
```

Loader `enabled` values are required to be booleans; do not use `0`/`1` instead. The current floating-point validator uses strict `total == 100.0` equality, so prefer simple decimal percentages with exact totals.

## 6. YgoMaster odds encoding

`exporters/ygomaster/odds.py` converts each policy to `cardRateList`:

- Base row: `start_num=1`, `end_num=booster_size`, `standard=false`, normal percentages.
- Ten-pack row: final slot only, `settle_rare_min=3`, `settle_rare_max=4`, SR/UR rates.
- Pity row: final slot only, `settle_rare_min=4`, `settle_rare_max=4`, UR 100%.

The rows are associated with the pack's absolute shop ID through `packShopIds`. The YgoMaster runtime selects the applicable row based on its rarity-guarantee state; the builder does not simulate pulls or store the pity counter. The exporter also emits a fixed `premiereRateList` for card finish/style odds.

**Runtime note:** the rule representation is based on the upstream YgoMaster shop/odds data model. Whether a particular installed version applies the requested x10/pity behavior must be tested in-game; successful JSON validation alone does not prove the draw system behaves as intended.
