"""Hybrid ranker: cosine on content + closeness on ordinals + penalties."""

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
    month_distance,
    parse_biomes,
    parse_tags,
    park_content_vector,
    tag_idf,
)
from .catalog import validate_parks

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "parks.csv"

# Fixed after the first scoring rewrite. Not retuned against holdout.
W_CONTENT = 0.55
W_DAYS = 0.18
W_DIFF = 0.14
W_BUDGET = 0.08
CROWD_PENALTY = 0.12
# Soft season penalty: (circular month distance / 6) * W_MONTH_PENALTY.
# 0.35: max 6-month penalty ≈ 0.35 < W_CONTENT (0.55), so a near-perfect
# off-season content match can beat a weak in-season park; a 2-month miss
# costs ≈0.117. Chosen so content can win against a moderate season mismatch.
W_MONTH_PENALTY = 0.35
MONTH_DISTANCE_MAX = 6.0
# Adjacent parks within this absolute score gap are effectively tied
# (docs/engine-contract.md §3). Annotation only — never reorders.
TIE_EPSILON = 0.001


def annotate_ties(
    ranked: pd.DataFrame, epsilon: float = TIE_EPSILON
) -> tuple[pd.DataFrame, list[list[str]]]:
    """Mark adjacent score ties. Does not change park order or scores.

    Returns the frame with a `tied_with_neighbors` column and `tie_groups`
    (lists of park_code for each run of adjacent parks within epsilon).
    """
    if ranked.empty:
        out = ranked.copy()
        out["tied_with_neighbors"] = pd.Series(dtype=bool)
        return out, []

    scores = ranked["score"].to_numpy(dtype=float)
    codes = ranked["park_code"].astype(str).tolist()
    n = len(scores)
    tied = [False] * n
    tie_groups: list[list[str]] = []

    group = [codes[0]]
    for i in range(1, n):
        if abs(scores[i - 1] - scores[i]) <= epsilon:
            group.append(codes[i])
            tied[i] = True
            tied[i - 1] = True
        else:
            if len(group) > 1:
                tie_groups.append(group)
            group = [codes[i]]
    if len(group) > 1:
        tie_groups.append(group)

    out = ranked.copy()
    out["tied_with_neighbors"] = tied
    return out, tie_groups


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
        validate_parks(self.parks)
        self.idf = tag_idf(self.parks["tags"])
        raw = np.vstack(
            [park_content_vector(row, idf=self.idf) for _, row in self.parks.iterrows()]
        )
        self.content_matrix = _l2_normalize(raw)

    def recommend(self, profile: UserProfile, k: int = 5) -> pd.DataFrame:
        frame = self._filtered(profile)
        if frame.empty:
            empty, tie_groups = annotate_ties(frame)
            empty.attrs["tie_groups"] = tie_groups
            return empty

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

        if profile.month is None:
            month_pen = np.zeros(len(frame), dtype=float)
        else:
            month_pen = (
                frame["best_months"]
                .fillna("")
                .map(lambda raw: month_distance(profile.month, raw) / MONTH_DISTANCE_MAX)
                .to_numpy(dtype=float)
                * W_MONTH_PENALTY
            )

        frame = frame.copy()
        frame["content"] = content
        frame["days_fit"] = days_s.to_numpy()
        frame["diff_fit"] = diff_s.to_numpy()
        frame["budget_fit"] = budget_s.to_numpy()
        frame["crowd_penalty"] = penalty.to_numpy()
        frame["month_penalty"] = month_pen
        frame["score"] = (
            W_CONTENT * frame["content"]
            + W_DAYS * frame["days_fit"]
            + W_DIFF * frame["diff_fit"]
            + W_BUDGET * frame["budget_fit"]
            - frame["crowd_penalty"]
            - frame["month_penalty"]
        )

        # Primary: score descending. Exact ties: park_code ascending (portable
        # rule any client can replicate — not pandas quicksort internals).
        ranked = frame.sort_values(
            ["score", "park_code"],
            ascending=[False, True],
            kind="stable",
        ).head(k).copy()
        ranked["why"] = ranked.apply(lambda row: self._why(row, profile), axis=1)
        ranked = ranked.reset_index(drop=True)
        ranked, tie_groups = annotate_ties(ranked)
        ranked.attrs["tie_groups"] = tie_groups
        return ranked

    def _filtered(self, profile: UserProfile) -> pd.DataFrame:
        frame = self.parks.copy()
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
        bits = list(parse_biomes(row["biomes"]))
        park_tags = set(parse_tags(row["tags"]))
        bits.extend([tag for tag in profile.tags if tag in park_tags][:3])
        if profile.days_needed == row["days_needed"]:
            bits.append(f"{row['days_needed']} day trip")
        if row["crowd"] == "low":
            bits.append("low crowds")
        if pd.notna(row.get("drive_hours")):
            bits.append(f"~{row['drive_hours']:.1f}h drive")
        return " · ".join(bits)
