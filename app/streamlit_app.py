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
        "image": "https://images.unsplash.com/photo-1482192505345-5659ce51760c?auto=format&fit=crop&w=1920&q=80",
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
    (None, "Any month"),
    (3, "March"),
    (4, "April"),
    (5, "May"),
    (6, "June"),
    (7, "July"),
    (8, "August"),
    (9, "September"),
    (10, "October"),
    (11, "November"),
]


@st.cache_resource
def load_model() -> ParkRecommender:
    return ParkRecommender()


def init_state() -> None:
    defaults = {
        "step": "welcome",
        "biomes": ["desert"],
        "tags": ["hiking"],
        "difficulty": "easy",
        "days": "2-3",
        "crowd": "medium",
        "budget": "mid",
        "month": 11,
        "origin": "any",
        "max_hours": 8,
        "allow_remote": False,
        "allow_permits": True,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def paint_background(step: str) -> None:
    bg = BACKGROUNDS.get(step, BACKGROUNDS["welcome"])
    st.markdown(
        f"""
        <style>
          .stApp {{ background: #08110c; }}
          [data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer {{
            display: none !important;
          }}
          .stAppViewContainer, .stMain, .block-container {{
            background: transparent !important;
            padding-top: 1.2rem !important;
            max-width: 760px;
          }}
          #park-bg {{
            position: fixed; inset: 0; z-index: 0; overflow: hidden;
          }}
          #park-bg video, #park-bg img {{
            width: 100%; height: 100%; object-fit: cover; filter: saturate(1.05);
          }}
          #park-bg::after {{
            content: ""; position: absolute; inset: 0;
            background: linear-gradient(180deg, rgba(8,17,12,.35) 0%, rgba(8,17,12,.72) 70%, rgba(8,17,12,.88) 100%);
          }}
          .quiz-kicker {{
            position: relative; z-index: 2; letter-spacing: .18em;
            text-transform: uppercase; color: #e8d9b8; font-size: .72rem;
          }}
          .quiz-title {{
            position: relative; z-index: 2; color: #f7f1e4;
            font-size: clamp(2rem, 5vw, 3.4rem); line-height: 1.05;
            font-weight: 560; margin: .35rem 0 1.2rem;
          }}
          .quiz-sub {{ position: relative; z-index: 2; color: #d7cbb3; margin-bottom: 1.4rem; }}
          .stButton > button {{
            border-radius: 999px; height: 3rem; font-weight: 600;
            border: 0;
          }}
        </style>
        <div id="park-bg">
          <img src="{bg["image"]}" alt="" />
          <video autoplay muted loop playsinline poster="{bg["image"]}">
            <source src="{bg["video"]}" type="video/mp4" />
          </video>
        </div>
        """,
        unsafe_allow_html=True,
    )


def go(step: str) -> None:
    st.session_state.step = step
    st.rerun()


def toggle(key: str, value: str) -> None:
    current = list(st.session_state[key])
    if value in current:
        current = [item for item in current if item != value]
    else:
        current.append(value)
    st.session_state[key] = current or [value]


init_state()
model = load_model()
step = st.session_state.step
paint_background(step)

STEPS = ["welcome", "terrain", "vibe", "pace", "when", "from", "results"]


def dots() -> None:
    idx = max(STEPS.index(step) if step in STEPS else 0, 0)
    marks = "".join("\u25cf" if i <= idx else "\u25cb" for i in range(len(STEPS) - 1))
    st.markdown(f'<p class="quiz-kicker">{marks}</p>', unsafe_allow_html=True)


if step == "welcome":
    dots()
    st.markdown('<p class="quiz-title">Find the park that fits this trip.</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="quiz-sub">Six short questions. No dashboard. 63 U.S. National Parks.</p>',
        unsafe_allow_html=True,
    )
    if st.button("Start", type="primary", use_container_width=True):
        go("terrain")

elif step == "terrain":
    dots()
    st.markdown('<p class="quiz-title">What kind of ground do you want under your boots?</p>', unsafe_allow_html=True)
    cols = st.columns(4)
    for i, (code, label) in enumerate(TERRAIN):
        selected = code in st.session_state.biomes
        if cols[i % 4].button(("\u2713 " if selected else "") + label, use_container_width=True):
            toggle("biomes", code)
            st.rerun()
    c1, c2 = st.columns(2)
    if c1.button("Back", use_container_width=True):
        go("welcome")
    if c2.button("Next", type="primary", use_container_width=True):
        go("vibe")

elif step == "vibe":
    dots()
    st.markdown('<p class="quiz-title">What should the days be about?</p>', unsafe_allow_html=True)
    cols = st.columns(4)
    for i, (code, label) in enumerate(VIBES):
        selected = code in st.session_state.tags
        if cols[i % 4].button(("\u2713 " if selected else "") + label, use_container_width=True):
            toggle("tags", code)
            st.rerun()
    c1, c2 = st.columns(2)
    if c1.button("Back", use_container_width=True):
        go("terrain")
    if c2.button("Next", type="primary", use_container_width=True):
        go("pace")

elif step == "pace":
    dots()
    st.markdown('<p class="quiz-title">How hard, and for how long?</p>', unsafe_allow_html=True)
    st.session_state.difficulty = st.select_slider("Effort", ["easy", "moderate", "challenging"], value=st.session_state.difficulty)
    st.session_state.days = st.select_slider("Days", ["1", "2-3", "4-7", "7+"], value=st.session_state.days)
    st.session_state.crowd = st.select_slider("Crowds", ["low", "medium", "high"], value=st.session_state.crowd)
    c1, c2 = st.columns(2)
    if c1.button("Back", use_container_width=True):
        go("vibe")
    if c2.button("Next", type="primary", use_container_width=True):
        go("when")

elif step == "when":
    dots()
    st.markdown('<p class="quiz-title">When are you going?</p>', unsafe_allow_html=True)
    labels = [label for _, label in MONTHS]
    current = next((label for month, label in MONTHS if month == st.session_state.month), "November")
    picked = st.radio("Month", labels, index=labels.index(current), label_visibility="collapsed")
    st.session_state.month = next(month for month, label in MONTHS if label == picked)
    c1, c2 = st.columns(2)
    if c1.button("Back", use_container_width=True):
        go("pace")
    if c2.button("Next", type="primary", use_container_width=True):
        go("from")

elif step == "from":
    dots()
    st.markdown('<p class="quiz-title">Are you driving, or is anywhere fine?</p>', unsafe_allow_html=True)
    names = ["any"] + sorted(ORIGINS)
    st.session_state.origin = st.selectbox("Driving from", names, index=names.index(st.session_state.origin))
    st.session_state.max_hours = st.slider("Max drive hours", 2, 16, int(st.session_state.max_hours), disabled=st.session_state.origin == "any")
    st.session_state.allow_remote = st.checkbox("Include remote parks (Alaska, Hawaii, ferry)", value=st.session_state.allow_remote)
    st.session_state.allow_permits = st.checkbox("Timed entry / permits are OK", value=st.session_state.allow_permits)
    c1, c2 = st.columns(2)
    if c1.button("Back", use_container_width=True):
        go("when")
    if c2.button("See parks", type="primary", use_container_width=True):
        go("results")

else:
    dots()
    st.markdown('<p class="quiz-title">These parks fit the trip.</p>', unsafe_allow_html=True)
    origin_lat = origin_lon = drive = None
    if st.session_state.origin != "any":
        origin_lat, origin_lon = ORIGINS[st.session_state.origin]
        drive = float(st.session_state.max_hours)
    ranked = model.recommend(
        UserProfile(
            biomes=st.session_state.biomes,
            tags=st.session_state.tags,
            difficulty=st.session_state.difficulty,
            days_needed=st.session_state.days,
            crowd_pref=st.session_state.crowd,
            budget_tier=st.session_state.budget,
            month=st.session_state.month,
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
            hours = "" if pd.isna(row["drive_hours"]) else f" \u00b7 ~{row['drive_hours']:.1f}h"
            st.markdown(
                f"**{row['name']}**  \n"
                f"`{row['park_code']}` \u00b7 {row['score']:.2f}{hours}  \n"
                f"{row['why']}"
            )
            st.progress(min(max(float(row["score"]), 0.0), 1.0))
    if st.button("Start over", use_container_width=True):
        go("welcome")
