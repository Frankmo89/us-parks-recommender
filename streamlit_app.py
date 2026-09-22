import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.features import BIOMES, UserProfile
from src.origins import ORIGINS
from src.recommender import ParkRecommender

st.set_page_config(page_title="US Parks Recommender", page_icon="🌲", layout="wide")


@st.cache_resource
def load_model() -> ParkRecommender:
    return ParkRecommender()


st.title("US Parks Recommender")
st.caption("Content cosine + ordinal closeness. 63 U.S. National Parks.")

model = load_model()

with st.sidebar:
    st.header("Your trip")
    biomes = st.multiselect("Terrain", BIOMES, default=["desert"])
    tags = st.multiselect(
        "What matters",
        ["hiking", "family", "stargazing", "wildlife", "scenic_drive", "backpacking", "photography", "water"],
        default=["hiking", "family"],
    )
    difficulty = st.select_slider("Difficulty", options=["easy", "moderate", "challenging"], value="easy")
    days = st.select_slider("Days", options=["1", "2-3", "4-7", "7+"], value="2-3")
    crowd = st.select_slider("Crowds", options=["low", "medium", "high"], value="medium")
    budget = st.select_slider("Travel budget", options=["low", "mid", "high"], value="mid")
    month = st.selectbox("Month", options=[None] + list(range(1, 13)), index=11)
    origin_name = st.selectbox("Driving from", options=["any"] + sorted(ORIGINS))
    max_hours = st.slider("Max drive hours", 2, 16, 8, disabled=origin_name == "any")
    allow_remote = st.checkbox("Include remote parks (AK, HI, ferry)", value=False)
    allow_permits = st.checkbox("OK with timed entry / permits", value=True)
    k = st.slider("How many parks", 3, 10, 5)

origin_lat = origin_lon = drive = None
if origin_name != "any":
    origin_lat, origin_lon = ORIGINS[origin_name]
    drive = float(max_hours)

profile = UserProfile(
    biomes=biomes,
    tags=tags,
    difficulty=difficulty,
    days_needed=days,
    crowd_pref=crowd,
    budget_tier=budget,
    month=month,
    origin_lat=origin_lat,
    origin_lon=origin_lon,
    max_drive_hours=drive,
    allow_remote=allow_remote,
    allow_permits=allow_permits,
)

ranked = model.recommend(profile, k=k)

if ranked.empty:
    st.warning("No parks matched. Relax month, distance, or the remote/permit filters.")
else:
    st.subheader("Top matches")
    for _, row in ranked.iterrows():
        hours = "" if pd.isna(row["drive_hours"]) else f" · ~{row['drive_hours']:.1f}h drive"
        st.markdown(f"**{row['name']}** (`{row['park_code']}`) — score {row['score']:.3f}{hours}")
        st.caption(row["why"])
        st.progress(min(max(float(row["score"]), 0.0), 1.0))
    show = ranked[["park_code", "name", "states", "biome", "difficulty", "crowd", "score", "why"]]
    st.dataframe(show, hide_index=True, width="stretch")

st.divider()
st.markdown(
    "Score = 0.55 content cosine + 0.18 days closeness + 0.14 difficulty closeness "
    "+ 0.08 budget closeness minus crowd penalty. Season, remote and permits are hard filters."
)
