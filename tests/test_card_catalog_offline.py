"""Offline regression tests for YgoMaster CardList.json validation.

Run from the project root with the venv active:
    python tests/test_card_catalog_offline.py
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from ygomaster_packbuilder.mapping import load_master_duel_card_catalog
from ygomaster_packbuilder.validation import validate_project_card_catalog
from ygomaster_packbuilder.workflow import WorkflowError, resolve_workflow_paths


with TemporaryDirectory() as tmp:
    root = Path(tmp)
    project_root = root / "PackBuilder"
    ygomaster = root / "YgoMaster"
    project_root.mkdir()
    data_dir = ygomaster / "Data"
    data_dir.mkdir(parents=True)
    (data_dir / "YdkIds.txt").write_text("10529441 23026\n", encoding="utf-8")
    catalog = data_dir / "CardList.json"

    try:
        resolve_workflow_paths(project_root, ygomaster)
    except WorkflowError as exc:
        assert "CardList.json" in str(exc)
    else:
        raise AssertionError("Missing card catalog must block the build.")

    catalog.write_text('{"1":1,"999":4}', encoding="utf-8-sig")
    paths = resolve_workflow_paths(project_root, ygomaster)
    assert paths.card_catalog == catalog
    assert load_master_duel_card_catalog(catalog) == {1, 999}

    card = SimpleNamespace(name="Unavailable Test Card", ydk_id=10529441, master_duel_id=23026)
    unknown = SimpleNamespace(name="Unmapped Card", ydk_id=2, master_duel_id=None)
    pack = SimpleNamespace(key="shared_staples-traps_n_tricks", cards=[card, unknown])
    project = SimpleNamespace(packs=[pack])
    report = validate_project_card_catalog(project, load_master_duel_card_catalog(catalog))
    assert not report.is_valid
    assert len(report.errors) == 1
    issue = report.errors[0]
    assert issue.code == "card-not-in-ygomaster-catalog"
    assert "Unavailable Test Card" in issue.message
    assert "10529441" in issue.message and "23026" in issue.message
    assert "shared_staples-traps_n_tricks" in issue.message

    # Existing catalog IDs are accepted regardless of their official rarity code.
    catalog.write_text('{"23026":4}', encoding="utf-8")
    assert validate_project_card_catalog(project, load_master_duel_card_catalog(catalog)).is_valid

    for invalid in ('{}', '[]', '{"abc":1}', '{"1":0}', '{"1":true}', '{"1":"4"}', '{bad'):
        catalog.write_text(invalid, encoding="utf-8")
        try:
            load_master_duel_card_catalog(catalog)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid catalog was accepted: {invalid!r}")

print("All offline YgoMaster card catalog checks passed.")
