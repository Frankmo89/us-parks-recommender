"""Precision@K against hand-labeled profiles."""
from __future__ import annotations
import json
from pathlib import Path
from .features import UserProfile
from .recommender import ParkRecommender

PROFILES_PATH = Path(__file__).resolve().parents[1] / "data" / "eval_profiles.json"
PROFILE_FIELDS = {
    "biomes", "tags", "difficulty", "days_needed", "crowd_pref",
    "budget_tier", "month", "origin_lat", "origin_lon", "max_drive_hours",
    "allow_remote", "allow_permits",
}

def load_profiles(path=None):
    raw = json.loads((path or PROFILES_PATH).read_text(encoding="utf-8"))
    return raw["profiles"]

def precision_at_k(recommended, relevant, k):
    if k == 0:
        return 0.0
    return sum(1 for code in recommended[:k] if code in relevant) / k

def run(k=5):
    model = ParkRecommender()
    rows = []
    for item in load_profiles():
        payload = {key: value for key, value in item["profile"].items() if key in PROFILE_FIELDS}
        ranked = model.recommend(UserProfile(**payload), k=k)
        codes = ranked["park_code"].tolist()
        rows.append({
            "id": item["id"],
            "precision_at_k": precision_at_k(codes, item["relevant"], k),
            "recommended": codes,
            "relevant": item["relevant"],
        })
    mean = sum(r["precision_at_k"] for r in rows) / max(len(rows), 1)
    return {"k": k, "mean_precision_at_k": mean, "profiles": rows}

def main():
    result = run(k=5)
    print(f"Precision@5 = {result['mean_precision_at_k']:.3f} over {len(result['profiles'])} profiles")
    for row in result["profiles"]:
        print(f"  {row['id']}: {row['precision_at_k']:.2f}  -> {row['recommended']}")

if __name__ == "__main__":
    main()
