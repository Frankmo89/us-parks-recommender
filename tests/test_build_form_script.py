"""Keep create_label_form.gs in sync with the importer form spec."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_create_label_form_gs_matches_importer_spec():
    """Fail if scripts/create_label_form.gs is stale vs get_form_spec()."""
    builder = _load("build_form_script", "scripts/build_form_script.py")
    gs_path = ROOT / "scripts" / "create_label_form.gs"
    assert gs_path.is_file(), f"missing {gs_path}; run python scripts/build_form_script.py"
    rendered = builder.render_apps_script()
    assert gs_path.read_text(encoding="utf-8") == rendered, (
        "scripts/create_label_form.gs is out of date with "
        "scripts/import_form_labels.get_form_spec(). "
        "Run: python scripts/build_form_script.py"
    )


def test_form_spec_titles_match_importer_columns():
    importer = _load("import_form_labels", "scripts/import_form_labels.py")
    spec = importer.get_form_spec()
    titles = [q["title"] for q in spec["questions"]]
    assert titles == [
        importer.COL_TERRAINS,
        importer.COL_ACTIVITIES,
        importer.COL_DIFFICULTY,
        importer.COL_DAYS,
        importer.COL_CROWD,
        importer.COL_BUDGET,
        importer.COL_MONTH,
        importer.COL_CITY,
        importer.COL_HOURS,
        importer.COL_REMOTE,
        importer.COL_PERMITS,
        importer.COL_TOP3,
    ]
    assert spec["title"] == importer.FORM_TITLE
    assert spec["description"] == importer.FORM_DESCRIPTION
    assert len(spec["questions"]) == 12

    # Display choices must be importable by the CSV mapper.
    assert all(c in importer.BIOME_FROM_LABEL for c in importer.BIOME_FORM_CHOICES)
    assert all(c in importer.TAG_FROM_LABEL for c in importer.TAG_FORM_CHOICES)
    assert all(c in importer.DIFFICULTY_FROM_LABEL for c in importer.DIFFICULTY_FORM_CHOICES)
    assert all(c in importer.DAYS_FROM_LABEL for c in importer.DAYS_FORM_CHOICES)
    assert all(c in importer.CROWD_FROM_LABEL for c in importer.CROWD_FORM_CHOICES)
    assert all(c in importer.BUDGET_FROM_LABEL for c in importer.BUDGET_FORM_CHOICES)
    assert all(c in importer.MONTH_FROM_LABEL for c in importer.MONTH_FORM_CHOICES)
    assert all(c in importer.ORIGIN_FROM_LABEL for c in importer.ORIGIN_FORM_CHOICES)

    top3 = next(q for q in spec["questions"] if q["title"] == importer.COL_TOP3)
    assert top3["validation"] == "exactly_3"
    assert len(top3["choices"]) == 63
    assert top3["required"] is True

    hours = next(q for q in spec["questions"] if q["title"] == importer.COL_HOURS)
    assert hours["type"] == "text"
    assert hours["required"] is False
    assert hours["validation"] == "number_gt_0"

    # Required except terrains, activities, max drive hours.
    optional = {importer.COL_TERRAINS, importer.COL_ACTIVITIES, importer.COL_HOURS}
    for q in spec["questions"]:
        if q["title"] in optional:
            assert q["required"] is False
        else:
            assert q["required"] is True


def test_generated_gs_contains_createLabelForm_and_links():
    text = (ROOT / "scripts" / "create_label_form.gs").read_text(encoding="utf-8")
    assert "function createLabelForm()" in text
    assert "Help me test a national park recommender" in text
    assert "Picture one trip you would really take" in text
    assert "requireSelectExactly(3)" in text
    assert "requireNumberGreaterThan(0)" in text
    assert "setDestination(FormApp.DestinationType.SPREADSHEET" in text
    assert "Form edit link" in text
    assert "Form public link" in text
    assert "Responses sheet" in text
    assert "How to run this (first time with Apps Script)" in text


def test_terrain_and_activity_limits_and_filter_help_text():
    text = (ROOT / "scripts" / "create_label_form.gs").read_text(encoding="utf-8")
    assert "q1.setValidation(FormApp.createCheckboxValidation().requireSelectAtMost(3)" in text
    assert "q2.setValidation(FormApp.createCheckboxValidation().requireSelectAtMost(4)" in text
    # Early responses mixed up drive hours and permits with the parks they picked.
    assert "If you would fly there, choose Anywhere" in text
    assert "Choose Anywhere if you would fly." in text
    assert "timed-entry reservation in peak season" in text
