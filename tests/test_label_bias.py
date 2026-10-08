"""Label popularity bias check (scripts/label_bias.py)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from src.evaluate import _user_profile, load_bundle
from src.recommender import ParkRecommender

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def lb():
    spec = importlib.util.spec_from_file_location("label_bias", ROOT / "scripts" / "label_bias.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def model():
    return ParkRecommender()


def test_percentiles_with_ties(lb):
    assert lb.percentiles(np.array([10.0, 30.0, 20.0])).tolist() == [0.0, 1.0, 0.5]
    assert lb.percentiles(np.array([5.0, 5.0, 9.0])).tolist() == [0.25, 0.25, 1.0]
    assert lb.percentiles(np.array([7.0])).tolist() == [0.5]


def _relabeled(model, lb, key):
    """Copy of each train profile whose picks are its top 3 candidates by `key`."""
    annual = lb.annual_visits(model)
    items = []
    for item in load_bundle()["profiles"]:
        if item.get("split", "train") != "train":
            continue
        profile = _user_profile(item)
        frame = model.candidates(profile)
        codes = frame["park_code"].astype(str).tolist()
        if key == "popular":
            ranked = sorted(codes, key=lambda c: -annual[c])
        else:
            from src.recommender import _cosine_rows

            fit = _cosine_rows(profile.content_vector(idf=model.idf), model.content_matrix[frame.index])
            ranked = [codes[i] for i in np.argsort(-fit, kind="stable")]
        items.append({**item, "split": "external", "relevant": ranked[:3]})
    return items


def test_popularity_labeler_is_flagged(lb, model):
    s = lb.analyze(_relabeled(model, lb, "popular"), model)["groups"]["external"]
    assert s["pop_pct"]["mean"] > 0.9
    assert s["pop_pct"]["ci_low"] > 0.5


def test_fit_labeler_scores_high_fit(lb, model):
    s = lb.analyze(_relabeled(model, lb, "fit"), model)["groups"]["external"]
    assert s["fit_pct"]["mean"] > 0.9


def test_hand_labels_are_not_popularity_driven(lb, model):
    s = lb.analyze(load_bundle()["profiles"], model)["groups"]["hand"]
    assert s["n"] == 18
    assert s["pop_pct"]["ci_low"] < 0.5 < s["pop_pct"]["ci_high"]
    assert s["fit_pct"]["ci_low"] > 0.5


def test_csv_responses_are_read_without_writing(lb, tmp_path):
    profiles = ROOT / "data" / "eval_profiles.json"
    before = profiles.read_bytes()
    items = lb.items_from_csv(ROOT / "tests" / "fixtures" / "form_labels_sample.csv")
    assert items and all(it["split"] == "external" for it in items)
    assert profiles.read_bytes() == before
