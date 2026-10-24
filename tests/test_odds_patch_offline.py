"""Manual/offline regression script for comment-preserving main ShopPackOdds patching.

Run from the project root: python tests/test_odds_patch_offline.py
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json

from ygomaster_packbuilder.installer.odds_patch import (
    YgoMasterOddsPatchError, patch_main_odds_file, restore_main_odds_file,
)
from ygomaster_packbuilder.installer.ygomaster import (
    YgoMasterInstallError, install_ygomaster_build, uninstall_ygomaster_build,
)
from ygomaster_packbuilder.installer.state import load_install_state

ENTRIES = [{"packShopIds": [19000000], "gachaType": 1, "cardRateList": []}]
BASES = [
    b"[]",
    b'[{"packShopIds":[1]}]',
    # The upstream YgoMaster Data/ShopPackOdds.json includes trailing commas
    # inside nested cardRateList arrays (allowed by MiniJSON, not strict JSON).
    b'[\n  // Legacy pack rates (estimate)\n  {"packShopIds":[1], "cardRateList":[{"start_num":1, "rate":{"1":{"rate":"100.00"},},},],},\n]',
    b'[{"packShopIds":[1], "name":"literal ,] and ,} inside string", "cardRateList":[{"start_num":1,},],},]',

    b'[\n// Preserve comments\n{"packShopIds":[1]} // trailing comment\n]',
    b'\xef\xbb\xbf[\r\n // Existing entry\r\n{"packShopIds":[1]}\r\n]\r\n',
]

for invalid in (b'[{,}]', b'[{"packShopIds":[1], "bad":,}]'):
    try:
        patch_main_odds_file(invalid, ENTRIES)
    except YgoMasterOddsPatchError:
        pass
    else:
        raise AssertionError(f"Invalid JSON unexpectedly accepted: {invalid!r}")

for base in BASES:
    patched, digest = patch_main_odds_file(base, ENTRIES)
    assert restore_main_odds_file(patched, digest) == base
    replaced, digest2 = patch_main_odds_file(patched, [{"packShopIds": [19000001]}], digest)
    assert restore_main_odds_file(replaced, digest2) == base
    try:
        patch_main_odds_file(patched, ENTRIES)
    except YgoMasterOddsPatchError:
        pass
    else:
        raise AssertionError("Untracked PackBuilder odds block was accepted.")

with TemporaryDirectory() as temp:
    root = Path(temp)
    game = root / "YgoMaster"
    data = game / "Data"
    data.mkdir(parents=True)
    build = root / "build"
    (build / "Shop").mkdir(parents=True)
    (build / "ShopPackOdds").mkdir()
    (build / "Shop" / "ygomaster-packbuilder.json").write_text('{"PackShop":{}}', encoding="utf-8")
    (build / "ShopPackOdds" / "ygomaster-packbuilder.json").write_text(json.dumps(ENTRIES), encoding="utf-8")
    (build / "ShopSettings.patch.json").write_text('{"PerPackRarities":true}', encoding="utf-8")
    original_shop = b'{\n  // preserve me\n  "PerPackRarities": false,\n  "PackShop": {}\n}'
    original_odds = BASES[-1]
    (data / "Shop.json").write_bytes(original_shop)
    (data / "ShopPackOdds.json").write_bytes(original_odds)
    # Test installer mechanics without needing an assembled domain/project.
    with patch("ygomaster_packbuilder.installer.ygomaster._require_valid_build"):
        first = install_ygomaster_build(None, {}, build, game)
        assert len(first.changed_files) == 3
        assert first.shop_pack_odds_file == data / "ShopPackOdds.json"
        assert not (data / "ShopPackOdds").exists()
        assert load_install_state(game).version == 2
        again = install_ygomaster_build(None, {}, build, game)
        assert not again.changed_files

        odds = data / "ShopPackOdds.json"
        odds.write_bytes(odds.read_bytes() + b'\r\n// unrelated edit')
        again = install_ygomaster_build(None, {}, build, game)
        assert not again.changed_files

        (build / "ShopPackOdds" / "ygomaster-packbuilder.json").write_text(
            json.dumps([{"packShopIds": [19000001]}]), encoding="utf-8"
        )
        updated = install_ygomaster_build(None, {}, build, game)
        assert updated.changed_files == (odds,)
        assert b'19000001' in odds.read_bytes()
        uninstall_ygomaster_build(game)
        assert (data / "Shop.json").read_bytes() == original_shop
        assert odds.read_bytes() == original_odds + b'\r\n// unrelated edit'
        assert not first.shop_file.exists()
        assert load_install_state(game) is None

        install_ygomaster_build(None, {}, build, game)
        odds.write_bytes(odds.read_bytes().replace(b"19000001", b"19000002"))
        tampered = odds.read_bytes()
        try:
            uninstall_ygomaster_build(game)
        except YgoMasterInstallError as exc:
            assert "modified" in str(exc)
        else:
            raise AssertionError("Modified managed odds block was accepted.")
        assert odds.read_bytes() == tampered

        (data / "ShopPackOdds").mkdir()
        try:
            install_ygomaster_build(None, {}, build, game)
        except YgoMasterInstallError as exc:
            assert "ShopPackOdds" in str(exc)
        else:
            raise AssertionError("Upstream-bug-triggering modular odds directory was accepted.")

print("All offline main ShopPackOdds patch/installer tests passed.")
