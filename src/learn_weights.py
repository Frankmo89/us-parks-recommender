"""Learn the score weights from labels instead of setting them by hand.

Experiment only: this module never changes the weights in src/recommender.py.

The model's score is a weighted sum of six parts it already computes for
every candidate park:

    content, days_fit, diff_fit, budget_fit   (higher is better)
    crowd excess levels, month distance / 6   (subtracted)

Hand weights: 0.55, 0.18, 0.14, 0.08, 0.12, 0.35.

We learn the same six weights with pairwise logistic regression. Within one
profile, every (relevant park, non-relevant park) pair says "the relevant one
should score higher". The loss is log(1 + exp(-w . (x_rel - x_other))), each
profile weighted equally, plus an L2 term. Only the order of scores matters,
so learned weights are compared after scaling to the hand weights' total.

Protocol (CLAUDE.md):
- Iterate on train only, with leave-one-profile-out cross-validation.
- Holdout is scored once, by weights fit on all of train.
- External (crowd labels) is scored by weights fit on train + holdout, and
  only when external profiles exist.

Run: python -m src.learn_weights
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import uncertainty
from .evaluate import _user_profile, load_bundle, ndcg_at_k, r_precision
from .recommender import (
    CROWD_PENALTY,
    W_BUDGET,
    W_CONTENT,
    W_DAYS,
    W_DIFF,
    W_MONTH_PENALTY,
    ParkRecommender,
)

FEATURES = ("content", "days_fit", "diff_fit", "budget_fit", "crowd", "month")
HAND_WEIGHTS = np.array([W_CONTENT, W_DAYS, W_DIFF, W_BUDGET, CROWD_PENALTY, W_MONTH_PENALTY])
L2 = 0.1
MAX_ITER = 100
K = 5


@dataclass
class ProfileData:
    id: str
    split: str
    codes: list[str]
    # Each row: content, days, diff, budget, -crowd_levels, -month_distance/6.
    # Signs are folded in so score = X @ weights with all weights positive.
    X: np.ndarray
    relevant: list[str]


def profile_data(model: ParkRecommender, item: dict) -> ProfileData:
    """Score parts for every candidate, read from the model's own scoring."""
    profile = _user_profile(item)
    frame = model.recommend(profile, k=len(model.parks))
    if frame.empty:
        X = np.zeros((0, len(FEATURES)))
        codes: list[str] = []
    else:
        X = np.column_stack(
            [
                frame["content"],
                frame["days_fit"],
                frame["diff_fit"],
                frame["budget_fit"],
                -frame["crowd_penalty"] / CROWD_PENALTY,
                -frame["month_penalty"] / W_MONTH_PENALTY,
            ]
        ).astype(float)
        codes = frame["park_code"].astype(str).tolist()
    return ProfileData(item["id"], item.get("split", "train"), codes, X, list(item["relevant"]))


def rank(data: ProfileData, weights: np.ndarray, k: int = K) -> list[str]:
    """Top-k codes by score; exact ties by park_code, as in the model."""
    if not data.codes:
        return []
    scores = data.X @ weights
    order = np.lexsort((np.array(data.codes), -scores))
    return [data.codes[i] for i in order[:k]]


def _pair_diffs(data: ProfileData) -> np.ndarray:
    rel = [i for i, c in enumerate(data.codes) if c in data.relevant]
    other = [i for i, c in enumerate(data.codes) if c not in data.relevant]
    if not rel or not other:
        return np.zeros((0, len(FEATURES)))
    return (data.X[rel][:, None, :] - data.X[other][None, :, :]).reshape(-1, len(FEATURES))


def fit(profiles: list[ProfileData], l2: float = L2, max_iter: int = MAX_ITER) -> np.ndarray:
    """Pairwise logistic regression by Newton's method. Deterministic."""
    blocks = [_pair_diffs(p) for p in profiles]
    blocks = [b for b in blocks if len(b)]
    if not blocks:
        return HAND_WEIGHTS.copy()
    D = np.vstack(blocks)
    # Each profile counts equally, however many pairs it has.
    sample_w = np.concatenate([np.full(len(b), 1.0 / len(b)) for b in blocks]) / len(blocks)
    w = np.zeros(len(FEATURES))
    for _ in range(max_iter):
        margin = D @ w
        p = 1.0 / (1.0 + np.exp(margin))  # sigmoid(-margin)
        grad = -(D * (sample_w * p)[:, None]).sum(axis=0) + l2 * w
        hess = (D * (sample_w * p * (1 - p))[:, None]).T @ D + l2 * np.eye(len(FEATURES))
        step = np.linalg.solve(hess, grad)
        w -= step
        if np.abs(step).max() < 1e-10:
            break
    return w


def scaled(weights: np.ndarray) -> np.ndarray:
    """Rescale to the hand weights' total so the two read side by side."""
    total = np.abs(weights).sum()
    return weights * (HAND_WEIGHTS.sum() / total) if total else weights


def _scores(datas: list[ProfileData], weight_sets: list[np.ndarray]) -> dict[str, list[float]]:
    r, n = [], []
    for data, w in zip(datas, weight_sets):
        top = rank(data, w)
        r.append(r_precision(top, data.relevant))
        n.append(ndcg_at_k(top, data.relevant, K))
    return {"r_precision": r, "ndcg_at_k": n}


def _content_only() -> np.ndarray:
    return np.array([1.0, 0, 0, 0, 0, 0])


def compare(datas: list[ProfileData], learned_sets: list[np.ndarray]) -> dict:
    """Learned vs hand vs content-only on the same profiles, with paired tests."""
    hand = _scores(datas, [HAND_WEIGHTS] * len(datas))
    learned = _scores(datas, learned_sets)
    content = _scores(datas, [_content_only()] * len(datas))
    out = {"n": len(datas), "methods": {}, "learned_vs": {}}
    for name, s in (("learned", learned), ("hand", hand), ("content_only", content)):
        out["methods"][name] = {m: uncertainty.metric_summary(v) for m, v in s.items()}
    for name, s in (("hand", hand), ("content_only", content)):
        out["learned_vs"][name] = {m: uncertainty.paired_test(learned[m], s[m]) for m in s}
    return out


def run(l2: float = L2) -> dict:
    model = ParkRecommender()
    items = load_bundle()["profiles"]
    datas = [profile_data(model, item) for item in items]
    train = [d for d in datas if d.split == "train"]
    holdout = [d for d in datas if d.split == "holdout"]
    external = [d for d in datas if d.split == "external"]

    folds = [fit([d for d in train if d is not held], l2=l2) for held in train]
    w_train = fit(train, l2=l2)
    result = {
        "l2": l2,
        "weights": {"hand": HAND_WEIGHTS.tolist(), "train": scaled(w_train).tolist()},
        "train_cv": compare(train, folds),
        "holdout": compare(holdout, [w_train] * len(holdout)),
        "external": None,
    }
    if external:
        w_all = fit(train + holdout, l2=l2)
        result["weights"]["train_holdout"] = scaled(w_all).tolist()
        result["external"] = compare(external, [w_all] * len(external))
    return result


def _format_p(p: float) -> str:
    return "p<0.001" if p < 0.001 else f"p={p:.3f}"


def _print_compare(title: str, block: dict) -> None:
    print(f"{title} (n={block['n']})")
    for name, label in (("learned", "Learned"), ("hand", "Hand"), ("content_only", "Content-only")):
        parts = []
        for metric, mname in (("r_precision", "R-Prec"), ("ndcg_at_k", "nDCG@5")):
            s = block["methods"][name][metric]
            parts.append(f"{mname} {s['mean']:.3f} [{s['ci_low']:.3f}, {s['ci_high']:.3f}]")
        print(f"  {label:<13} " + "   ".join(parts))
    for name, label in (("hand", "Hand"), ("content_only", "Content-only")):
        for metric, mname in (("r_precision", "R-Prec"), ("ndcg_at_k", "nDCG@5")):
            t = block["learned_vs"][name][metric]
            print(
                f"  learned - {label:<13} {mname:<7} {t['mean_diff']:+.3f} "
                f"[{t['ci_low']:+.3f}, {t['ci_high']:+.3f}]  {_format_p(t['p_value'])}  "
                f"{t['wins']}/{t['ties']}/{t['losses']}"
            )


def main() -> None:
    result = run()
    print(f"Pairwise logistic regression, L2={result['l2']}. Experiment only; the app's weights are unchanged.")
    print()
    print(f"{'Part':<10} {'Hand':>6} {'Learned (train, scaled)':>24}")
    for name, hand, learned in zip(FEATURES, result["weights"]["hand"], result["weights"]["train"]):
        print(f"{name:<10} {hand:>6.2f} {learned:>24.2f}")
    print()
    _print_compare("Train, leave-one-profile-out", result["train_cv"])
    print()
    _print_compare("Holdout, weights fit on all train (scored once)", result["holdout"])
    print()
    if result["external"] is None:
        print("External: no external profiles yet (import form responses first).")
    else:
        _print_compare("External, weights fit on train + holdout", result["external"])


if __name__ == "__main__":
    main()
