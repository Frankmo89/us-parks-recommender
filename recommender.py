"""Hybrid ranker: cosine on content + closeness on ordinals + crowd penalty."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .features import (
    BUDGET_ORD,
    CROWD_RANK,
    DAYS_ORD,
    DIFF_ORD,
    UserProfile,
    closeness,
    drive_hours,
    parse_months,
    parse_tags,
    park_content_vector,
    tag_idf,
)

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "parks.csv"

# Fixed after the first scoring rewrite. Not retuned against holdout.
W_CONTENT = 0.55
W_DAYS = 0.18
W_DIFF = 0.14
W_BUDGET = 0.08
CROWD_PENALTY = 0.12


def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.clip(norms, 1e-12, None)


def _cosine_rows(user_vec: np.ndarray, park_matrix: np.ndarray) -> np.ndarray:
    user = user_vec.reshape(1, -1)
    user = user / np.clip(np.linalg.norm(user), 1e-12, None)
    parks = _l2_normalize(park_matrix)
    return (parks @ user.T).ravel()


class ParkRecommender:
    def __init__(self, csv_path: Path | None = None) -> None:
        path = csv_path or DATA_PATH
        self.parks = pd.read_csv(path)
        self.idf = tag_idf(self.parks["tags"])
        raw = np.vstack(
            [park_content_vector(row, idf=self.idf) for _, row in self.parks.iterrows()]
        )
        self.content_matrix = _l2_normalize(raw)

    def recommend(self, profile: UserProfile, k: int = 5) -> pd.DataFrame:
        frame = self._filtered(profile)
        if frame.empty:
            return frame

        content = _cosine_rows(
            profile.content_vector(idf=self.idf),
            self.content_matrix[frame.index],
        )

        days_u = DAYS_ORD[profile.days_needed]
        diff_u = DIFF_ORD[profile.difficulty]
        budget_u = BUDGET_ORD[profile.budget_tier]
        crowd_u = CROWD_RANK[profile.crowd_pref]

        days_s = frame["days_needed"].map(DAYS_ORD).astype(float).map(
            lambda v: closeness(v, days_u, 3.0)
        )
        diff_s = frame["difficulty"].map(DIFF_ORD).astype(float).map(
            lambda v: closeness(v, diff_u, 2.0)
        )
        budget_s = frame["budget_tier"].map(BUDGET_ORD).astype(float).map(
            lambda v: closeness(v, budget_u, 2.0)
        )
        crowd_p = frame["crowd"].map(CROWD_RANK).astype(float)
        penalty = (crowd_p - crowd_u).clip(lower=0) * CROWD_PENALTY

        frame = frame.copy()
        frame["content"] = content
        frame["days_fit"] = days_s.to_numpy()
        frame["diff_fit"] = diff_s.to_numpy()
        frame["budget_fit"] = budget_s.to_numpy()
        frame["crowd_penalty"] = penalty.to_numpy()
        frame["score"] = (
            W_CONTENT * frame["content"]
            + W_DAYS * frame["days_fit"]
            + W_DIFF * frame["diff_fit"]
            + W_BUDGET * frame["budget_fit"]
            - frame["crowd_penalty"]
        )

        ranked = frame.sort_values("score", ascending=False).head(k).copy()
        ranked["why"] = ranked.apply(lambda row: self._why(row, profile), axis=1)
        return ranked.reset_index(drop=True)

    def _filtered(self, profile: UserProfile) -> pd.DataFrame:
        frame = self.parks.copy()
        if profile.month is not None:
            month = str(profile.month)
            keep = frame["best_months"].fillna("").map(lambda raw: month in parse_months(raw))
            frame = frame.loc[keep]
        if not profile.allow_remote:
            frame = frame.loc[frame["remote"] == 0]
        if not profile.allow_permits:
            frame = frame.loc[frame["permit_likely"] == 0]
        if (
            profile.origin_lat is not None
            and profile.origin_lon is not None
            and profile.max_drive_hours is not None
        ):
            hours = [
                drive_hours(profile.origin_lat, profile.origin_lon, row.lat, row.lon)
                for row in frame.itertuples()
            ]
            frame = frame.assign(drive_hours=hours)
            frame = frame.loc[frame["drive_hours"] <= profile.max_drive_hours]
        else:
            frame = frame.assign(drive_hours=np.nan)
        return frame

    def _why(self, row: pd.Series, profile: UserProfile) -> str:
        bits = [str(row["biome"])]
        park_tags = set(parse_tags(row["tags"]))
        bits.extend([tag for tag in profile.tags if tag in park_tags][:3])
        if profile.days_needed == row["days_needed"]:
            bits.append(f"{row['days_needed']} day trip")
        if row["crowd"] == "low":
            bits.append("low crowds")
        if pd.notna(row.get("drive_hours")):
            bits.append(f"~{row['drive_hours']:.1f}h drive")
        return " · ".join(bits)
