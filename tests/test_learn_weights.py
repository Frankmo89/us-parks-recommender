"""Learned score weights (src/learn_weights.py). Experiment only."""

from __future__ import annotations

import numpy as np
import pytest

from src import learn_weights as lw
from src.evaluate import _user_profile, load_bundle
from src.recommender import ParkRecommender


@pytest.fixture(scope="module")
def model():
    return ParkRecommender()


def test_hand_weights_reproduce_the_model_order(model):
    # The features must be read from the model's own scoring, or the
    # experiment would compare against a different ranker.
    for item in load_bundle()["profiles"]:
        data = lw.profile_data(model, item)
        expected = model.recommend(_user_profile(item), k=5)["park_code"].tolist()
        assert lw.rank(data, lw.HAND_WEIGHTS) == expected, item["id"]


def _synthetic(seed: int, n_parks: int = 30) -> lw.ProfileData:
    rng = np.random.default_rng(seed)
    X = rng.random((n_parks, len(lw.FEATURES)))
    codes = [f"p{i:02d}" for i in range(n_parks)]
    # Relevance is decided by the budget column alone.
    top = np.argsort(-X[:, 3])[:3]
    return lw.ProfileData(f"s{seed}", "train", codes, X, [codes[i] for i in top])


def test_fit_puts_weight_on_the_feature_that_decides_relevance():
    w = lw.fit([_synthetic(s) for s in range(10)], l2=0.01)
    assert np.argmax(w) == 3
    assert w[3] > 2 * np.abs(np.delete(w, 3)).max()


def test_fit_is_deterministic_and_scaled_keeps_the_hand_total():
    data = [_synthetic(s) for s in range(5)]
    assert np.array_equal(lw.fit(data), lw.fit(data))
    assert np.abs(lw.scaled(lw.fit(data))).sum() == pytest.approx(lw.HAND_WEIGHTS.sum())


def test_rank_breaks_exact_ties_by_park_code():
    data = lw.ProfileData("t", "train", ["b", "a", "c"], np.zeros((3, len(lw.FEATURES))), ["a"])
    assert lw.rank(data, lw.HAND_WEIGHTS) == ["a", "b", "c"]


def test_run_reports_train_cv_and_holdout_and_no_external_yet():
    result = lw.run()
    assert result["train_cv"]["n"] == 12
    assert result["holdout"]["n"] == 6
    assert result["external"] is None
    hand = result["train_cv"]["methods"]["hand"]["ndcg_at_k"]["mean"]
    # Hand weights on train must match the published train nDCG@5.
    assert hand == pytest.approx(0.739, abs=5e-4)
