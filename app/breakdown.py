"""Pure helpers that turn a ranked row into the "Why this park" breakdown.

No Streamlit calls here so this stays importable and testable with plain pytest.
Reuses the model's own weight constants so the numbers always match
`python -m src.cli --explain` and the score column `ParkRecommender.recommend()`
already computed.
"""

from __future__ import annotations

import pandas as pd

from src.features import CROWD_RANK
from src.recommender import CROWD_PENALTY, W_BUDGET, W_CONTENT, W_DAYS, W_DIFF

PART_ORDER = ["Terrain & activities", "Days", "Effort", "Budget", "Crowds"]

# Worst-case crowd penalty: the widest possible gap between a park's crowd
# level and the user's, times the per-level penalty (src.recommender.CROWD_PENALTY).
MAX_CROWD_PENALTY = (max(CROWD_RANK.values()) - min(CROWD_RANK.values())) * CROWD_PENALTY

# A part's ceiling: the weight it can contribute at best (content/days/effort/budget),
# or the worst-case penalty it can subtract (crowds).
PART_MAX = {
    "Terrain & activities": W_CONTENT,
    "Days": W_DAYS,
    "Effort": W_DIFF,
    "Budget": W_BUDGET,
    "Crowds": MAX_CROWD_PENALTY,
}

# The best a park can score: every fit part at its ceiling, no crowd penalty.
MAX_SCORE = W_CONTENT + W_DAYS + W_DIFF + W_BUDGET

_SENTENCE_WORD = {
    "Terrain & activities": "terrain",
    "Days": "length",
    "Effort": "effort",
    "Budget": "budget",
}

STRONG_FRACTION = 0.8
LOSS_FRACTION = 0.1


def match_percent(score: float) -> int:
    """Score as a percentage of the best possible score, for the "Match" badge.

    A park that maxes out every fit part with no crowd penalty scores 100%.
    This is a display-only transform of `score` (monotonic, same order it
    already sorts by), so it never changes the ranking.
    """
    pct = float(score) / MAX_SCORE * 100
    return max(0, min(100, round(pct)))


def score_breakdown(row: pd.Series) -> pd.DataFrame:
    """Weighted contribution of each score part, in the same units as `score`.

    Sums to `row["score"]`. Uses the same weight constants and columns
    `src.cli --explain` prints (content, days_fit, diff_fit, budget_fit,
    crowd_penalty), just multiplied out so the bars are comparable. The
    `max` column is each part's own ceiling, used to judge fit relative to
    what that part could have contributed.
    """
    values = {
        "Terrain & activities": W_CONTENT * float(row["content"]),
        "Days": W_DAYS * float(row["days_fit"]),
        "Effort": W_DIFF * float(row["diff_fit"]),
        "Budget": W_BUDGET * float(row["budget_fit"]),
        "Crowds": -float(row["crowd_penalty"]),
    }
    return pd.DataFrame(
        {
            "part": PART_ORDER,
            "value": [values[part] for part in PART_ORDER],
            "kind": ["Loss" if values[part] < 0 else "Gain" for part in PART_ORDER],
            "max": [PART_MAX[part] for part in PART_ORDER],
        }
    )


def _join_words(words: list[str]) -> str:
    if len(words) <= 1:
        return words[0] if words else ""
    if len(words) == 2:
        return f"{words[0]} and {words[1]}"
    return ", ".join(words[:-1]) + f", and {words[-1]}"


def why_sentence(breakdown: pd.DataFrame) -> str:
    """One plain sentence: parts near their own ceiling, then the biggest gap.

    "Strong fit" is every fit part (terrain, days, effort, budget) at or
    above `STRONG_FRACTION` of its own maximum. The loss clause names
    whichever lost more against its own ceiling: the weakest fit part, or
    the crowd penalty if that gap is bigger. A loss under `LOSS_FRACTION`
    of its own maximum (that includes an exact 0.00) is not worth a clause,
    so only the strong-fit half of the sentence is shown.
    """
    fits = breakdown[breakdown["part"] != "Crowds"].copy()

    strong = fits[fits["value"] >= STRONG_FRACTION * fits["max"]].sort_values("value", ascending=False)
    words = [_SENTENCE_WORD[part] for part in strong["part"]]
    fit_clause = f"Strong fit on {_join_words(words)}" if words else "No strong fit found"

    fits["gap"] = fits["max"] - fits["value"]
    weakest = fits.sort_values("gap", ascending=False).iloc[0]
    loss_gap, loss_max, loss_word = float(weakest["gap"]), float(weakest["max"]), _SENTENCE_WORD[weakest["part"]]

    crowd = breakdown.loc[breakdown["part"] == "Crowds"].iloc[0]
    crowd_gap, crowd_max = -float(crowd["value"]), float(crowd["max"])
    if crowd_gap > loss_gap:
        loss_gap, loss_max, loss_word = crowd_gap, crowd_max, "crowds"

    if loss_gap <= 0 or round(loss_gap, 2) == 0 or loss_gap <= LOSS_FRACTION * loss_max:
        return f"{fit_clause}."
    return f"{fit_clause}; lost points for {loss_word}."


def nps_url(park_code: str) -> str:
    return f"https://www.nps.gov/{park_code}/"
