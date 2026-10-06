"""Pure helpers that turn a ranked row into the "Why this park" breakdown.

No Streamlit calls here so this stays importable and testable with plain pytest.
Reuses the model's own weight constants so the numbers always match
`python -m src.cli --explain` and the score column `ParkRecommender.recommend()`
already computed.
"""

from __future__ import annotations

import pandas as pd

from src.features import CROWD_RANK
from src.recommender import (
    CROWD_PENALTY,
    W_BUDGET,
    W_CONTENT,
    W_DAYS,
    W_DIFF,
    W_MONTH_PENALTY,
    access_label,
)

PART_ORDER = ["Terrain & activities", "Days", "Effort", "Budget", "Crowds", "Season"]

# Worst-case crowd penalty: the widest possible gap between a park's crowd
# level and the user's, times the per-level penalty (src.recommender.CROWD_PENALTY).
MAX_CROWD_PENALTY = (max(CROWD_RANK.values()) - min(CROWD_RANK.values())) * CROWD_PENALTY

# A part's ceiling: the weight it can contribute at best (content/days/effort/budget),
# or the worst-case penalty it can subtract (crowds / season).
PART_MAX = {
    "Terrain & activities": W_CONTENT,
    "Days": W_DAYS,
    "Effort": W_DIFF,
    "Budget": W_BUDGET,
    "Crowds": MAX_CROWD_PENALTY,
    "Season": W_MONTH_PENALTY,
}

# The best a park can score: every fit part at its ceiling, no penalties.
MAX_SCORE = W_CONTENT + W_DAYS + W_DIFF + W_BUDGET

_SENTENCE_WORD = {
    "Terrain & activities": "terrain",
    "Days": "length",
    "Effort": "effort",
    "Budget": "budget",
}

STRONG_FRACTION = 0.8
LOSS_FRACTION = 0.1

# Label settings for the chart's "Contribution to score" axis. Streamlit
# cannot see the screen width, so these have to work at every width: at most
# about 3 ticks, overlapping labels dropped, end labels kept inside the plot,
# a smaller font, and trailing zeros trimmed ("0.1", not "0.10"). On a phone
# the defaults gave 0.05 steps whose labels ran together ("0.000.05").
VALUE_AXIS_LABELS = {
    "tickCount": 3,
    "labelOverlap": "greedy",
    "labelFlush": True,
    "labelFontSize": 10,
    "format": ".2~f",
}


MINUS = "\u2212"  # typographic minus, same glyph Vega's "+.2f" format used


def format_contribution(value: float) -> str:
    """Bar label for one score part: "+0.26", "\u22120.12", or "0".

    Anything that rounds to 0.00 prints as plain "0". Penalties are stored
    as negated values, so a zero penalty is -0.0 and Vega printed it as
    "\u22120.00".
    """
    rounded = round(float(value), 2)
    if rounded == 0:
        return "0"
    sign = "+" if rounded > 0 else MINUS
    return f"{sign}{abs(rounded):.2f}"


# Share of the plot width kept free for value labels on each side that has
# bars: "+0.26" at 11 px is ~37 px with its offset, about 28% of the
# ~135 px plot on a 390 px phone.
LABEL_SHARE = 0.28
ROW_STEP = 30  # px per chart row; bars fill 60% of it


def value_domain(breakdown: pd.DataFrame) -> tuple[float, float]:
    """x-axis bounds that fit the bars plus room for their value labels.

    Positive labels sit right of their bar (zero parts too, at x=0), so
    the right side always gets label room; the left side gets it only when
    a part is negative.
    """
    lo = min(0.0, float(breakdown["value"].min()))
    hi = max(0.0, float(breakdown["value"].max()))
    span = (hi - lo) or 0.1
    sides = 2 if lo < 0 else 1
    pad = span * LABEL_SHARE / (1 - sides * LABEL_SHARE)
    return (lo - pad if lo < 0 else 0.0, hi + pad)


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
        "Season": -float(row.get("month_penalty", 0.0)),
    }
    # `+ 0.0` turns a zero penalty's -0.0 into 0.0.
    values = {part: value + 0.0 for part, value in values.items()}
    return pd.DataFrame(
        {
            "part": PART_ORDER,
            "value": [values[part] for part in PART_ORDER],
            "label": [format_contribution(values[part]) for part in PART_ORDER],
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
    above `STRONG_FRACTION` of its own maximum. The second clause names
    whichever left the most on the table: the weakest fit part that is not
    already strong, or a penalty (crowds, season) if that gap is bigger.

    Wording follows the sign of the part, so it never contradicts the chart:
    only a negative part (a penalty) "lost points"; a fit part that is
    positive but below the strong cutoff is a "partial match"; a fit part at
    0.00 is "no match". A gap under `LOSS_FRACTION` of its own maximum (that
    includes an exact 0.00 penalty) is not worth a clause, so only the
    strong-fit half of the sentence is shown.
    """
    fits = breakdown[~breakdown["part"].isin(["Crowds", "Season"])].copy()

    is_strong = fits["value"] >= STRONG_FRACTION * fits["max"]
    strong = fits[is_strong].sort_values("value", ascending=False)
    words = [_SENTENCE_WORD[part] for part in strong["part"]]
    fit_clause = f"Strong fit on {_join_words(words)}" if words else "No strong fit found"

    gap_clause = ""
    loss_gap, loss_max = 0.0, 0.0
    partial = fits[~is_strong].copy()
    if not partial.empty:
        partial["gap"] = partial["max"] - partial["value"]
        weakest = partial.sort_values("gap", ascending=False).iloc[0]
        loss_gap, loss_max = float(weakest["gap"]), float(weakest["max"])
        word = _SENTENCE_WORD[weakest["part"]]
        matched = round(float(weakest["value"]), 2) > 0
        gap_clause = f"partial match on {word}" if matched else f"no match on {word}"

    for part, word in (("Crowds", "crowds"), ("Season", "season")):
        row = breakdown.loc[breakdown["part"] == part].iloc[0]
        gap, part_max = -float(row["value"]), float(row["max"])
        if gap > loss_gap:
            loss_gap, loss_max, gap_clause = gap, part_max, f"lost points for {word}"

    if not gap_clause or round(loss_gap, 2) == 0 or loss_gap <= LOSS_FRACTION * loss_max:
        return f"{fit_clause}."
    return f"{fit_clause}; {gap_clause}."


def card_meta(row: pd.Series) -> str:
    """States plus the travel note shown next to the Match badge.

    Multi-state parks read "WY, MT, ID" (the catalog stores "WY,MT,ID").

    Same label the engine puts at the end of `why` (src.recommender.access_label):
    "~Xh drive", "~Xh drive + boat", "boat needed", "flight needed", or none.
    """
    bits = [", ".join(code.strip() for code in str(row["states"]).split(","))]
    travel = access_label(row.get("access"), row.get("drive_hours"))
    if travel:
        bits.append(travel)
    return " · ".join(bits)


def nps_url(park_code: str) -> str:
    return f"https://www.nps.gov/{park_code}/"
