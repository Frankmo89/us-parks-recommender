"""Content-based park ranking with cosine similarity + hard filters."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize
from .features import CROWD_RANK, UserProfile, haversine_hours, park_vector

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "parks.csv"

class ParkRecommender:
    def __init__(self, csv_path=None):
        path = csv_path or DATA_PATH
        self.parks = pd.read_csv(path)
        matrix = np.vstack([park_vector(row) for _, row in self.parks.iterrows()])
        self.matrix = normalize(matrix)

    def recommend(self, profile: UserProfile, k=5):
        scores = cosine_similarity(profile.vector().reshape(1, -1), self.matrix)[0]
        frame = self.parks.copy()
        frame["similarity"] = scores
        if profile.month is not None:
            month = str(profile.month)
            in_season = frame["best_months"].fillna("").apply(
                lambda raw: month in {part.strip() for part in str(raw).split(",")}
            )
            frame = frame.loc[in_season]
        if not profile.allow_remote:
            frame = frame.loc[frame["remote"] == 0]
        if not profile.allow_permits:
            frame = frame.loc[frame["permit_likely"] == 0]
        if profile.origin_lat is not None and profile.origin_lon is not None and profile.max_drive_hours is not None:
            hours = [haversine_hours(profile.origin_lat, profile.origin_lon, row.lat, row.lon) for row in frame.itertuples()]
            frame = frame.assign(drive_hours=hours)
            frame = frame.loc[frame["drive_hours"] <= profile.max_drive_hours]
        else:
            frame = frame.assign(drive_hours=np.nan)
        if frame.empty:
            return frame
        want = CROWD_RANK[profile.crowd_pref]
        penalty = frame["crowd"].map(CROWD_RANK).astype(float) - want
        frame["score"] = frame["similarity"] - 0.08 * penalty.clip(lower=0)
        ranked = frame.sort_values("score", ascending=False).head(k).copy()
        ranked["why"] = ranked.apply(self._why, axis=1, profile=profile)
        return ranked.reset_index(drop=True)

    def _why(self, row, profile):
        bits = [row["biome"]]
        park_tags = set(str(row["tags"]).split("|"))
        bits.extend([tag for tag in profile.tags if tag in park_tags][:3])
        if profile.month and str(profile.month) in str(row["best_months"]).split(","):
            bits.append(f"good season in month {profile.month}")
        if row["crowd"] == "low":
            bits.append("low crowds")
        if pd.notna(row.get("drive_hours")):
            bits.append(f"~{row['drive_hours']:.1f}h drive")
        return " · ".join(bits)
