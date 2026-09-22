"""R-Precision and nDCG@K on labeled fixtures.

These are acceptance fixtures, not a published benchmark.
Train was used only to sanity-check the first weight set.
Holdout was not used to pick weights.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from .features import UserProfile
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


def score_split(model: ParkRecommender, profiles: list[dict], k: int = 5) -> dict:
    rows = []
    for item in profiles:
        payload = {key: value for key, value in item["profile"].items() if key in PROFILE_FIELDS}
        ranked = model.recommend(UserProfile(**payload), k=k)
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
    n = max(len(rows), 1)
    return {
        "k": k,
        "n": len(rows),
        "mean_r_precision": sum(r["r_precision"] for r in rows) / n,
        "mean_ndcg_at_k": sum(r["ndcg_at_k"] for r in rows) / n,
        "profiles": rows,
    }


def run(k: int = 5) -> dict:
    bundle = load_bundle()
    model = ParkRecommender()
    train = [p for p in bundle["profiles"] if p.get("split") != "holdout"]
    holdout = [p for p in bundle["profiles"] if p.get("split") == "holdout"]
    return {
        "train": score_split(model, train, k=k),
        "holdout": score_split(model, holdout, k=k),
        "all": score_split(model, bundle["profiles"], k=k),
    }


def _print_block(title: str, block: dict) -> None:
    print(
        f"{title}: n={block['n']}  R-Prec={block['mean_r_precision']:.3f}  "
        f"nDCG@{block['k']}={block['mean_ndcg_at_k']:.3f}"
    )
    for row in block["profiles"]:
        print(
            f"  {row['id']}: R={row['r_precision']:.2f} nDCG={row['ndcg_at_k']:.2f} "
            f"n={row['n_returned']}  -> {row['recommended']}"
        )


def main() -> None:
    result = run(k=5)
    _print_block("train", result["train"])
    print()
    _print_block("holdout", result["holdout"])
    print()
    _print_block("all", result["all"])


if __name__ == "__main__":
    main()
