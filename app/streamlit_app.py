import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.features import UserProfile
from src.origins import ORIGINS
from src.recommender import ParkRecommender

st.set_page_config(page_title="Find your park", page_icon="🌲", layout="wide", initial_sidebar_state="collapsed")

BACKGROUNDS = {
    "welcome": {
        "image": "https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=1920&q=80",
        "video": "https://videos.pexels.com/video-files/3571264/3571264-hd_1920_1080_30fps.mp4",
    },
    "terrain": {
        "image": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1920&q=80",
        "video": "https://videos.pexels.com/video-files/857251/857251-hd_1920_1080_30fps.mp4",
    },
    "vibe": {
        "image": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1920&q=80",
        "video": "https://videos.pexels.com/video-files/2169880/2169880-hd_1920_1080_30fps.mp4",
    },
    "pace": {
        "image": "https://images.unsplash.com/photo-1533240332313-0db49b459ad6?auto=format&fit=crop&w=1920&q=80",
        "video": "https://videos.pexels.com/video-files/1093662/1093662-hd_1920_1080_25fps.mp4",
    },
    "when": {
        "image": "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=1920&q=80",
        "video": "https://videos.pexels.com/video-files/857195/857195-hd_1920_1080_30fps.mp4",
    },
    "from": {
        "image": "https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=1920&q=80",
        "video": "https://videos.pexels.com/video-files/1542006/1542006-hd_1920_1080_24fps.mp4",
    },
    "results": {
        "image": "https://images.unsplash.com/photo-1426604966848-d7adac402bff?auto=format&fit=crop&w=1920&q=80",
        "video": "https://videos.pexels.com/video-files/3571264/3571264-hd_1920_1080_30fps.mp4",
    },
}

TERRAIN = [
    ("desert", "Desert"),
    ("canyon", "Canyon"),
    ("alpine", "Alpine"),
    ("forest", "Forest"),
    ("coast", "Coast"),
    ("volcano", "Volcano"),
    ("wetland", "Wetland"),
    ("cave", "Cave"),
]
VIBES = [
    ("hiking", "Hiking"),
    ("family", "Family"),
    ("stargazing", "Dark skies"),
    ("wildlife", "Wildlife"),
    ("scenic_drive", "Scenic drive"),
    ("photography", "Photos"),
    ("water", "Water"),
    ("backpacking", "Backpacking"),
]
MONTHS = [
    (1, "January"),
    (2, "February"),
    (3, "March"),
    (4, "April"),
    (5, "May"),
    (6, "June"),
    (7, "July"),
    (8, "August"),
    (9, "September"),
    (10, "October"),
    (11, "November"),
    (12, "December"),
]
MONTH_LABELS = ["Any"] + [label for _, label in MONTHS]
MONTH_NUMBER = {label: number for number, label in MONTHS}

ORIGIN_LABELS = {
    "san_diego": "San Diego",
    "los_angeles": "Los Angeles",
    "phoenix": "Phoenix",
    "denver": "Denver",
    "seattle": "Seattle",
    "salt_lake": "Salt Lake City",
    "nyc": "New York City",
}
ORIGIN_CHOICES = ["Anywhere"] + sorted(ORIGIN_LABELS.values())
ORIGIN_KEY_BY_LABEL = {label: code for code, label in ORIGIN_LABELS.items()}

STEPS = ["welcome", "terrain", "vibe", "pace", "when", "from", "results"]

MAX_TERRAIN = 3
MAX_VIBES = 3


@st.cache_resource
def load_model() -> ParkRecommender:
    return ParkRecommender()


def inject_base_css() -> None:
    st.html(
        """
        <style>
          .stApp { background: transparent; }
          #park-bg { position: fixed; inset: 0; z-index: 0; overflow: hidden; }
          #park-bg video, #park-bg img {
            width: 100%; height: 100%; object-fit: cover; filter: saturate(1.05);
          }
          #park-bg::after {
            content: ""; position: absolute; inset: 0;
            background: linear-gradient(180deg, rgba(8,17,12,.30) 0%, rgba(8,17,12,.55) 60%, rgba(8,17,12,.72) 100%);
          }
          .quiz-kicker {
            position: relative; z-index: 2; letter-spacing: .18em;
            text-transform: uppercase; color: #e8d9b8; font-size: .72rem;
          }
          .quiz-title {
            position: relative; z-index: 2; color: #f7f1e4;
            font-size: clamp(1.7rem, 4.2vw, 2.8rem); line-height: 1.1;
            font-weight: 560; margin: .35rem 0 .9rem;
          }
          .quiz-sub { position: relative; z-index: 2; color: #d7cbb3; margin-bottom: 1.2rem; }
          .quiz-hint { position: relative; z-index: 2; color: #cfe8d9; font-size: .82rem; margin: .5rem 0 .9rem; }
          .quiz-hint-warn { color: #f4b56a; font-weight: 600; }
          .st-key-app_shell {
            position: relative; z-index: 2; max-width: 760px; margin: 0 auto;
            padding: 2.4rem 1rem 3rem;
          }
          .st-key-quiz_panel {
            background: rgba(6, 14, 10, .82);
            border: 1px solid rgba(247, 241, 228, .14);
            border-radius: 20px;
            padding: 1.8rem 1.8rem 1.5rem;
            backdrop-filter: blur(8px);
          }
        </style>
        """
    )


def paint_background(step: str) -> None:
    bg = BACKGROUNDS.get(step, BACKGROUNDS["welcome"])
    st.html(
        f"""
        <div id="park-bg">
          <img src="{bg["image"]}" alt="" />
          <video autoplay muted loop playsinline poster="{bg["image"]}">
            <source src="{bg["video"]}" type="video/mp4" />
          </video>
        </div>
        """
    )


def init_state() -> None:
    defaults = {
        "step": "welcome",
        "biomes_pills": ["desert"],
        "tags_pills": ["hiking"],
        "difficulty": "easy",
        "days": "2-3",
        "crowd": "medium",
        "budget": "mid",
        "month_pills": "November",
        "origin_label": "Anywhere",
        "max_hours": 8,
        "allow_remote": False,
        "allow_permits": True,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def go(step: str) -> None:
    st.session_state.step = step
    st.rerun()


def dots(step: str) -> None:
    idx = max(STEPS.index(step) if step in STEPS else 0, 0)
    marks = "".join("●" if i <= idx else "○" for i in range(len(STEPS) - 1))
    st.markdown(f'<p class="quiz-kicker">{marks}</p>', unsafe_allow_html=True)


init_state()
model = load_model()
step = st.session_state.step
inject_base_css()
paint_background(step)

with st.container(key="app_shell"):
    with st.container(key="quiz_panel"):
        dots(step)

        if step == "welcome":
            st.markdown('<p class="quiz-title">Find the park that fits this trip.</p>', unsafe_allow_html=True)
            st.markdown(
                '<p class="quiz-sub">Six short questions. No dashboard. 63 U.S. National Parks.</p>',
                unsafe_allow_html=True,
            )
            if st.button("Start", type="primary", width="stretch"):
                go("terrain")

        elif step == "terrain":
            st.markdown(
                '<p class="quiz-title">What kind of ground do you want under your boots?</p>',
                unsafe_allow_html=True,
            )
            st.pills(
                "Terrain",
                options=[code for code, _ in TERRAIN],
                format_func=dict(TERRAIN).get,
                selection_mode="multi",
                default=st.session_state.biomes_pills,
                key="biomes_pills",
                label_visibility="collapsed",
            )
            picked = st.session_state.biomes_pills
            if len(picked) > MAX_TERRAIN:
                st.markdown(
                    f'<p class="quiz-hint quiz-hint-warn">Pick up to {MAX_TERRAIN} — remove one to continue.</p>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f'<p class="quiz-hint">Pick up to {MAX_TERRAIN}.</p>', unsafe_allow_html=True)
            valid = bool(picked) and len(picked) <= MAX_TERRAIN
            c1, c2 = st.columns(2)
            if c1.button("Back", width="stretch"):
                go("welcome")
            if c2.button("Next", type="primary", width="stretch", disabled=not valid):
                go("vibe")

        elif step == "vibe":
            st.markdown('<p class="quiz-title">What should the days be about?</p>', unsafe_allow_html=True)
            st.pills(
                "Activities",
                options=[code for code, _ in VIBES],
                format_func=dict(VIBES).get,
                selection_mode="multi",
                default=st.session_state.tags_pills,
                key="tags_pills",
                label_visibility="collapsed",
            )
            picked_tags = st.session_state.tags_pills
            if len(picked_tags) > MAX_VIBES:
                st.markdown(
                    f'<p class="quiz-hint quiz-hint-warn">Pick up to {MAX_VIBES} — remove one to continue.</p>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f'<p class="quiz-hint">Pick up to {MAX_VIBES}.</p>', unsafe_allow_html=True)
            valid = bool(picked_tags) and len(picked_tags) <= MAX_VIBES
            c1, c2 = st.columns(2)
            if c1.button("Back", width="stretch"):
                go("terrain")
            if c2.button("Next", type="primary", width="stretch", disabled=not valid):
                go("pace")

        elif step == "pace":
            st.markdown('<p class="quiz-title">How hard, how long, how busy, how much?</p>', unsafe_allow_html=True)
            st.segmented_control(
                "Effort",
                ["easy", "moderate", "challenging"],
                default=st.session_state.difficulty,
                key="difficulty",
                required=True,
                format_func=str.title,
            )
            st.segmented_control(
                "Days", ["1", "2-3", "4-7", "7+"], default=st.session_state.days, key="days", required=True
            )
            st.segmented_control(
                "Crowds",
                ["low", "medium", "high"],
                default=st.session_state.crowd,
                key="crowd",
                required=True,
                format_func=str.title,
            )
            st.segmented_control(
                "Budget",
                ["low", "mid", "high"],
                default=st.session_state.budget,
                key="budget",
                required=True,
                format_func=str.title,
            )
            c1, c2 = st.columns(2)
            if c1.button("Back", width="stretch"):
                go("vibe")
            if c2.button("Next", type="primary", width="stretch"):
                go("when")

        elif step == "when":
            st.markdown('<p class="quiz-title">When are you going?</p>', unsafe_allow_html=True)
            st.pills(
                "Month",
                MONTH_LABELS,
                default=st.session_state.month_pills,
                key="month_pills",
                required=True,
                label_visibility="collapsed",
            )
            c1, c2 = st.columns(2)
            if c1.button("Back", width="stretch"):
                go("pace")
            if c2.button("Next", type="primary", width="stretch"):
                go("from")

        elif step == "from":
            st.markdown('<p class="quiz-title">Are you driving, or is anywhere fine?</p>', unsafe_allow_html=True)
            st.selectbox(
                "Driving from",
                ORIGIN_CHOICES,
                index=ORIGIN_CHOICES.index(st.session_state.origin_label),
                key="origin_label",
            )
            if st.session_state.origin_label != "Anywhere":
                st.slider("Max drive hours", 2, 16, value=st.session_state.max_hours, key="max_hours")
            st.toggle("Include remote parks (AK, HI, ferry)", value=st.session_state.allow_remote, key="allow_remote")
            st.toggle("OK with timed entry / permits", value=st.session_state.allow_permits, key="allow_permits")
            c1, c2 = st.columns(2)
            if c1.button("Back", width="stretch"):
                go("when")
            if c2.button("See parks", type="primary", width="stretch"):
                go("results")

        else:
            st.markdown('<p class="quiz-title">These parks fit the trip.</p>', unsafe_allow_html=True)
            origin_label = st.session_state.origin_label
            origin_lat = origin_lon = drive = None
            if origin_label != "Anywhere":
                origin_lat, origin_lon = ORIGINS[ORIGIN_KEY_BY_LABEL[origin_label]]
                drive = float(st.session_state.max_hours)
            ranked = model.recommend(
                UserProfile(
                    biomes=st.session_state.biomes_pills,
                    tags=st.session_state.tags_pills,
                    difficulty=st.session_state.difficulty,
                    days_needed=st.session_state.days,
                    crowd_pref=st.session_state.crowd,
                    budget_tier=st.session_state.budget,
                    month=MONTH_NUMBER.get(st.session_state.month_pills),
                    origin_lat=origin_lat,
                    origin_lon=origin_lon,
                    max_drive_hours=drive,
                    allow_remote=st.session_state.allow_remote,
                    allow_permits=st.session_state.allow_permits,
                ),
                k=5,
            )
            if ranked.empty:
                st.warning("Nothing matched. Loosen month, distance, or the remote filter.")
            else:
                for _, row in ranked.iterrows():
                    hours = "" if pd.isna(row["drive_hours"]) else f" · ~{row['drive_hours']:.1f}h"
                    st.markdown(
                        f"**{row['name']}**  \n"
                        f"`{row['park_code']}` · {row['score']:.2f}{hours}  \n"
                        f"{row['why']}"
                    )
                    st.progress(min(max(float(row["score"]), 0.0), 1.0))
            if st.button("Start over", width="stretch"):
                go("welcome")
