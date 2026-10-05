"""R-Precision and nDCG@K on labeled fixtures.

These are acceptance fixtures, not a published benchmark.
Train was used only to sanity-check the first weight set.
Holdout was not used to pick weights.

Baselines (popularity, random) use the same hard-filtered candidate set as
the model so the comparison is fair. They do not change scoring.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

from .features import CROWD_RANK, UserProfile
from .recommender import ParkRecommender

PROFILES_PATH = Path(__file__).resolve().parents[1] / "data" / "eval_profiles.json"

PROFILE_FIELDS = {
    "biomes",
    "tags",
    "difficulty",
    "days_needed",
    "crowd_pref",
    "budget_tier",
    "month",
    "origin_lat",
    "origin_lon",
    "max_drive_hours",
    "allow_remote",
    "allow_permits",
}

RANDOM_SEEDS = range(100)  # 0..99


def load_bundle(path: Path | None = None) -> dict:
    return json.loads((path or PROFILES_PATH).read_text(encoding="utf-8"))


def r_precision(recommended: list[str], relevant: list[str]) -> float:
    if not relevant:
        return 0.0
    k = len(relevant)
    hits = sum(1 for code in recommended[:k] if code in relevant)
    return hits / k


def dcg(recommended: list[str], relevant: set[str], k: int) -> float:
    total = 0.0
    for i, code in enumerate(recommended[:k], start=1):
        rel = 1.0 if code in relevant else 0.0
        total += rel / math.log2(i + 1)
    return total


def ndcg_at_k(recommended: list[str], relevant: list[str], k: int) -> float:
    if not relevant:
        return 0.0
    ideal = dcg(relevant, set(relevant), k)
    if ideal == 0:
        return 0.0
    return dcg(recommended, set(relevant), k) / ideal


def _user_profile(item: dict) -> UserProfile:
    payload = {key: value for key, value in item["profile"].items() if key in PROFILE_FIELDS}
    return UserProfile(**payload)


def _aggregate(rows: list[dict], k: int) -> dict:
    n = max(len(rows), 1)
    return {
        "k": k,
        "n": len(rows),
        "mean_r_precision": sum(r["r_precision"] for r in rows) / n,
        "mean_ndcg_at_k": sum(r["ndcg_at_k"] for r in rows) / n,
        "profiles": rows,
    }


def score_split(model: ParkRecommender, profiles: list[dict], k: int = 5) -> dict:
    rows = []
    for item in profiles:
        ranked = model.recommend(_user_profile(item), k=k)
        codes = ranked["park_code"].tolist()
        rows.append(
            {
                "id": item["id"],
                "split": item.get("split", "train"),
                "r_precision": r_precision(codes, item["relevant"]),
                "ndcg_at_k": ndcg_at_k(codes, item["relevant"], k),
                "n_returned": len(codes),
                "recommended": codes,
                "relevant": item["relevant"],
            }
        )
    return _aggregate(rows, k)


def popularity_rank(model: ParkRecommender, profile: UserProfile, k: int = 5) -> list[str]:
    """Rank hard-filtered parks by crowd high→low, then park_code ascending."""
    frame = model._filtered(profile)
    if frame.empty:
        return []
    ranked = frame.assign(_crowd=frame["crowd"].map(CROWD_RANK)).sort_values(
        ["_crowd", "park_code"],
        ascending=[False, True],
        kind="stable",
    )
    return ranked["park_code"].astype(str).head(k).tolist()


def score_split_popularity(
    model: ParkRecommender, profiles: list[dict], k: int = 5
) -> dict:
    rows = []
    for item in profiles:
        codes = popularity_rank(model, _user_profile(item), k=k)
        rows.append(
            {
                "id": item["id"],
                "split": item.get("split", "train"),
                "r_precision": r_precision(codes, item["relevant"]),
                "ndcg_at_k": ndcg_at_k(codes, item["relevant"], k),
                "n_returned": len(codes),
                "recommended": codes,
                "relevant": item["relevant"],
            }
        )
    return _aggregate(rows, k)


def random_rank_means(
    model: ParkRecommender,
    profile: UserProfile,
    relevant: list[str],
    k: int = 5,
) -> tuple[float, float]:
    """Mean R-Precision and nDCG@k over 100 shuffles (seeds 0..99)."""
    base = sorted(model._filtered(profile)["park_code"].astype(str).tolist())
    if not base:
        return 0.0, 0.0
    r_sum = 0.0
    n_sum = 0.0
    n_seeds = 0
    for seed in RANDOM_SEEDS:
        shuffled = base.copy()
        random.Random(seed).shuffle(shuffled)
        top = shuffled[:k]
        r_sum += r_precision(top, relevant)
        n_sum += ndcg_at_k(top, relevant, k)
        n_seeds += 1
    return r_sum / n_seeds, n_sum / n_seeds


def score_split_random(
    model: ParkRecommender, profiles: list[dict], k: int = 5
) -> dict:
    rows = []
    for item in profiles:
        r_prec, ndcg = random_rank_means(
            model, _user_profile(item), item["relevant"], k=k
        )
        rows.append(
            {
                "id": item["id"],
                "split": item.get("split", "train"),
                "r_precision": r_prec,
                "ndcg_at_k": ndcg,
                "n_returned": k,
                "recommended": [],
                "relevant": item["relevant"],
            }
        )
    return _aggregate(rows, k)


def run(k: int = 5) -> dict:
    bundle = load_bundle()
    model = ParkRecommender()
    train = [p for p in bundle["profiles"] if p.get("split") != "holdout"]
    holdout = [p for p in bundle["profiles"] if p.get("split") == "holdout"]
    all_profiles = bundle["profiles"]
    return {
        # Top-level train/holdout/all stay model-only for Streamlit / existing tests.
        "train": score_split(model, train, k=k),
        "holdout": score_split(model, holdout, k=k),
        "all": score_split(model, all_profiles, k=k),
        "popularity": {
            "train": score_split_popularity(model, train, k=k),
            "holdout": score_split_popularity(model, holdout, k=k),
            "all": score_split_popularity(model, all_profiles, k=k),
        },
        "random": {
            "train": score_split_random(model, train, k=k),
            "holdout": score_split_random(model, holdout, k=k),
            "all": score_split_random(model, all_profiles, k=k),
        },
    }


def _print_block(title: str, block: dict) -> None:
    print(
        f"{title}: n={block['n']}  R-Prec={block['mean_r_precision']:.3f}  "
        f"nDCG@{block['k']}={block['mean_ndcg_at_k']:.3f}"
    )
    for row in block["profiles"]:
        recommended = row.get("recommended") or []
        print(
            f"  {row['id']}: R={row['r_precision']:.2f} nDCG={row['ndcg_at_k']:.2f} "
            f"n={row['n_returned']}  -> {recommended}"
        )


def _print_comparison_table(result: dict) -> None:
    methods = [
        ("Model", None),
        ("Popularity", "popularity"),
        ("Random", "random"),
    ]
    splits = ("train", "holdout", "all")
    print(f"{'Method':<12} {'Split':<8} {'n':>3}  {'R-Prec':>7}  {'nDCG@5':>7}")
    print("-" * 42)
    for label, key in methods:
        block_root = result if key is None else result[key]
        for split in splits:
            block = block_root[split]
            print(
                f"{label:<12} {split:<8} {block['n']:>3}  "
                f"{block['mean_r_precision']:>7.3f}  "
                f"{block['mean_ndcg_at_k']:>7.3f}"
            )


def main() -> None:
    result = run(k=5)
    _print_comparison_table(result)
    print()
    _print_block("train (model)", result["train"])
    print()
    _print_block("holdout (model)", result["holdout"])
    print()
    _print_block("all (model)", result["all"])


if __name__ == "__main__":
    main()
