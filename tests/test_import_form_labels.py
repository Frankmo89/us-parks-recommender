"""Tests for scripts/import_form_labels.py against the sample CSV."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CSV = ROOT / "tests" / "fixtures" / "form_labels_sample.csv"


@pytest.fixture()
def import_mod():
    import importlib.util

    path = ROOT / "scripts" / "import_form_labels.py"
    spec = importlib.util.spec_from_file_location("import_form_labels", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_sample_csv_appends_only_valid_external_rows(tmp_path, import_mod):
    profiles_src = ROOT / "data" / "eval_profiles.json"
    profiles_copy = tmp_path / "eval_profiles.json"
    shutil.copy(profiles_src, profiles_copy)

    before = json.loads(profiles_copy.read_text(encoding="utf-8"))
    n_before = len(before["profiles"])
    existing_ids = {p["id"] for p in before["profiles"]}
    existing_relevant = {p["id"]: list(p["relevant"]) for p in before["profiles"]}

    result = import_mod.import_csv(SAMPLE_CSV, profiles_path=profiles_copy, dry_run=False)

    after = json.loads(profiles_copy.read_text(encoding="utf-8"))
    assert len(result["appended"]) == 2
    assert len(result["skipped"]) == 3
    assert len(after["profiles"]) == n_before + 2

    # Existing profiles untouched (ids and relevant lists).
    for item in after["profiles"][:n_before]:
        assert item["id"] in existing_ids
        assert item["relevant"] == existing_relevant[item["id"]]

    new_items = after["profiles"][n_before:]
    assert all(item["split"] == "external" for item in new_items)
    assert {tuple(item["relevant"]) for item in new_items} == {
        ("deva", "jotr", "sagu"),
        ("yell", "grte", "glac"),
    }

    # First row: San Diego origin + drive hours.
    sd = next(item for item in new_items if item["relevant"] == ["deva", "jotr", "sagu"])
    assert sd["profile"]["origin_lat"] == pytest.approx(32.72)
    assert sd["profile"]["max_drive_hours"] == 8
    assert sd["profile"]["allow_remote"] is False
    assert sd["profile"]["biomes"] == ["desert", "canyon"]
    assert sd["profile"]["tags"] == ["hiking", "stargazing", "photography"]
    assert sd["profile"]["month"] == 11
    assert "unreachable" not in sd

    # Anywhere: no origin / drive fields.
    anywhere = next(item for item in new_items if item["relevant"] == ["yell", "grte", "glac"])
    assert "origin_lat" not in anywhere["profile"]
    assert "max_drive_hours" not in anywhere["profile"]
    assert anywhere["profile"]["month"] == 7


def test_sample_csv_dry_run_does_not_write(tmp_path, import_mod):
    profiles_src = ROOT / "data" / "eval_profiles.json"
    profiles_copy = tmp_path / "eval_profiles.json"
    shutil.copy(profiles_src, profiles_copy)
    before = profiles_copy.read_text(encoding="utf-8")

    result = import_mod.import_csv(SAMPLE_CSV, profiles_path=profiles_copy, dry_run=True)
    assert len(result["appended"]) == 2
    assert profiles_copy.read_text(encoding="utf-8") == before


def test_san_diego_unreachable_picks_are_skipped(import_mod):
    """San Diego ≤6h, no remote/permits, yell/havo/zion → all fail filters → skip."""
    from src.features import UserProfile
    from src.origins import ORIGINS
    from src.recommender import ParkRecommender

    model = ParkRecommender()
    lat, lon = ORIGINS["san_diego"]
    profile = UserProfile(
        biomes=["desert"],
        tags=["hiking"],
        origin_lat=lat,
        origin_lon=lon,
        max_drive_hours=6,
        allow_remote=False,
        allow_permits=False,
    )
    relevant, unreachable = import_mod.split_reachable_picks(
        model, profile, ["yell", "havo", "zion"]
    )
    assert relevant == []
    by_code = {u["park_code"]: u["reasons"] for u in unreachable}
    assert by_code["yell"] == ["drive"]
    assert by_code["havo"] == ["remote", "drive"]
    assert by_code["zion"] == ["permit", "drive"]

    # Full CSV row is skipped (no reachable pick).
    skipped_msgs = []
    profiles_src = ROOT / "data" / "eval_profiles.json"
    # Use dry-run import and look for the San Diego unreachable skip message.
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        profiles_copy = Path(tmp) / "eval_profiles.json"
        shutil.copy(profiles_src, profiles_copy)
        result = import_mod.import_csv(SAMPLE_CSV, profiles_path=profiles_copy, dry_run=True)
        skipped_msgs = result["skipped"]

    assert any("No top-3 picks pass hard filters" in msg for msg in skipped_msgs)
    assert any("yell:drive" in msg and "havo:" in msg and "zion:" in msg for msg in skipped_msgs)


def test_evaluate_all_excludes_external(tmp_path, import_mod):
    """External profiles must not move train / holdout / all aggregates."""
    from src.evaluate import run

    baseline = run(k=5)
    profiles_src = ROOT / "data" / "eval_profiles.json"
    profiles_copy = tmp_path / "eval_profiles.json"
    shutil.copy(profiles_src, profiles_copy)
    import_mod.import_csv(SAMPLE_CSV, profiles_path=profiles_copy, dry_run=False)

    # Point evaluate at the temp bundle by monkeypatching PROFILES_PATH.
    import src.evaluate as ev

    original = ev.PROFILES_PATH
    ev.PROFILES_PATH = profiles_copy
    try:
        with_external = ev.run(k=5)
    finally:
        ev.PROFILES_PATH = original

    for split in ("train", "holdout", "all"):
        assert with_external[split]["n"] == baseline[split]["n"]
        assert with_external[split]["mean_r_precision"] == pytest.approx(
            baseline[split]["mean_r_precision"]
        )
        assert with_external[split]["mean_ndcg_at_k"] == pytest.approx(
            baseline[split]["mean_ndcg_at_k"]
        )

    assert with_external["external"]["n"] == 2
    assert baseline["external"]["n"] == 0
    assert with_external["external_unreachable"]["parks"] == 0
