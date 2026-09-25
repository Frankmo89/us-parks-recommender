import altair as alt
import pandas as pd
import streamlit as st

from app.breakdown import PART_ORDER, match_percent, nps_url, score_breakdown, why_sentence
from src.evaluate import run as run_evaluation
from src.features import DRIVE_DETOUR, DRIVE_MPH, UserProfile
from src.origins import ORIGINS
from src.recommender import CROWD_PENALTY, W_BUDGET, W_CONTENT, W_DAYS, W_DIFF, ParkRecommender

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

# Display labels for biomes present in the catalog. Options themselves are
# always read from parks.csv via catalog_terrains() so new biomes appear here.
BIOME_LABELS = {
    "alpine": "Alpine",
    "canyon": "Canyon",
    "cave": "Cave",
    "chaparral": "Chaparral",
    "coast": "Coast",
    "desert": "Desert",
    "forest": "Forest",
    "island": "Island",
    "prairie": "Prairie",
    "rainforest": "Rainforest",
    "tundra": "Tundra",
    "urban": "Urban",
    "volcano": "Volcano",
    "wetland": "Wetland",
}


def catalog_terrains(parks: pd.DataFrame) -> list[tuple[str, str]]:
    """Biome picker options from the loaded catalog — never a hardcoded subset."""
    codes = sorted({str(biome) for biome in parks["biome"].dropna().unique()})
    return [
        (code, BIOME_LABELS.get(code, code.replace("_", " ").title()))
        for code in codes
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


@st.cache_data
def load_evaluation() -> dict:
    return run_evaluation(k=5)


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
          .park-name { color: #f7f1e4; font-weight: 600; font-size: 1rem; margin: 0 0 .4rem; }
          .park-name-lg { font-size: 1.35rem; }
          .park-meta { color: #d7cbb3; font-size: .85rem; }
          .match-badge {
            display: inline-block; background: #e8d9b8; color: #16210f;
            font-weight: 700; font-size: .78rem; padding: .18rem .6rem;
            border-radius: 999px; margin-right: .5rem; vertical-align: middle;
          }
          .why-sentence { color: #d7cbb3; font-size: .88rem; margin-top: .6rem; }
          .how-h { color: #e8d9b8; font-weight: 700; font-size: 1.05rem; margin: 1.5rem 0 .5rem; }
          .how-list { color: #d7cbb3; font-size: .9rem; line-height: 1.55; padding-left: 1.2rem; margin: 0 0 .5rem; }
          .how-list li { margin-bottom: .4rem; }
          .how-note { color: #8fa393; font-size: .8rem; margin: .4rem 0 0; }
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


DEFAULT_ANSWERS = {
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


def init_state() -> None:
    defaults = {"step": "welcome", **DEFAULT_ANSWERS}
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def go(step: str) -> None:
    st.session_state.step = step
    st.rerun()


def start_over() -> None:
    for key, value in DEFAULT_ANSWERS.items():
        st.session_state[key] = value
    go("welcome")


def open_how_it_works() -> None:
    st.session_state.how_it_works_from = st.session_state.step
    go("how_it_works")


def dots(step: str) -> None:
    idx = max(STEPS.index(step) if step in STEPS else 0, 0)
    marks = "".join("●" if i <= idx else "○" for i in range(len(STEPS) - 1))
    st.markdown(f'<p class="quiz-kicker">{marks}</p>', unsafe_allow_html=True)


def why_chart(breakdown: pd.DataFrame) -> alt.Chart:
    base = alt.Chart(breakdown).encode(
        y=alt.Y(
            "part:N",
            sort=PART_ORDER,
            title=None,
            axis=alt.Axis(labelColor="#d7cbb3", labelFontSize=12, domain=False, ticks=False, grid=False),
        ),
        x=alt.X(
            "value:Q",
            title="Contribution to score",
            axis=alt.Axis(
                labelColor="#8fa393",
                titleColor="#8fa393",
                gridColor="#2a3a30",
                domain=False,
                tickCount=4,
            ),
        ),
    )
    bars = base.mark_bar(size=16, cornerRadiusEnd=3).encode(
        color=alt.Color(
            "kind:N",
            sort=["Gain", "Loss"],
            scale=alt.Scale(domain=["Gain", "Loss"], range=["#0ca30c", "#d03b3b"]),
            legend=alt.Legend(title=None, orient="bottom", labelColor="#d7cbb3"),
        ),
        tooltip=[alt.Tooltip("part:N", title="Part"), alt.Tooltip("value:Q", title="Contribution", format="+.2f")],
    )
    zero_rule = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="#4a5a4e", strokeWidth=1).encode(x="x:Q")
    labels_pos = (
        base.transform_filter(alt.datum.value >= 0)
        .mark_text(align="left", dx=5, color="#f7f1e4", fontSize=11)
        .encode(text=alt.Text("value:Q", format="+.2f"))
    )
    labels_neg = (
        base.transform_filter(alt.datum.value < 0)
        .mark_text(align="right", dx=-5, color="#f7f1e4", fontSize=11)
        .encode(text=alt.Text("value:Q", format="+.2f"))
    )
    return (
        (zero_rule + bars + labels_pos + labels_neg)
        .properties(height=160, background="transparent")
        .configure_view(strokeWidth=0)
    )


def _why_expander(row: pd.Series) -> None:
    with st.expander("Why this park"):
        breakdown = score_breakdown(row)
        st.altair_chart(why_chart(breakdown), width="stretch", theme=None)
        st.markdown(f'<p class="why-sentence">{why_sentence(breakdown)}</p>', unsafe_allow_html=True)


def _card_meta(row: pd.Series) -> str:
    bits = [str(row["states"])]
    if pd.notna(row.get("drive_hours")):
        bits.append(f"~{row['drive_hours']:.1f}h drive")
    return " · ".join(bits)


def render_top_card(row: pd.Series) -> None:
    with st.container(border=True):
        st.markdown(f'<p class="park-name park-name-lg">{row["name"]}</p>', unsafe_allow_html=True)
        st.markdown(
            f'<span class="match-badge">Match {match_percent(row["score"])}%</span>'
            f'<span class="park-meta">{_card_meta(row)}</span>',
            unsafe_allow_html=True,
        )
        st.link_button("NPS page", nps_url(row["park_code"]))
        _why_expander(row)


def render_small_card(row: pd.Series) -> None:
    with st.container(border=True):
        st.markdown(f'<p class="park-name">{row["name"]}</p>', unsafe_allow_html=True)
        st.markdown(
            f'<span class="match-badge">Match {match_percent(row["score"])}%</span>'
            f'<span class="park-meta">{_card_meta(row)}</span>',
            unsafe_allow_html=True,
        )
        st.link_button("NPS page", nps_url(row["park_code"]))
        _why_expander(row)


def render_how_it_works(model: ParkRecommender) -> None:
    back_target = st.session_state.get("how_it_works_from", "welcome")
    if st.button("← Back", width="content"):
        go(back_target)

    st.markdown('<p class="quiz-title">How it works</p>', unsafe_allow_html=True)

    st.markdown('<p class="how-h">The idea</p>', unsafe_allow_html=True)
    st.markdown(
        "<p class=\"quiz-sub\">Parks and trips share one feature space of biome and activity "
        "tags. The score blends a content match in that space with closeness on days, effort "
        "and budget, minus a penalty for crowds above what you asked for.</p>",
        unsafe_allow_html=True,
    )

    st.markdown('<p class="how-h">The formula</p>', unsafe_allow_html=True)
    st.code(
        f"score = {W_CONTENT:.2f} * content_match\n"
        f"      + {W_DAYS:.2f} * days_closeness\n"
        f"      + {W_DIFF:.2f} * difficulty_closeness\n"
        f"      + {W_BUDGET:.2f} * budget_closeness\n"
        f"      - {CROWD_PENALTY:.2f} * crowd_excess",
        language=None,
    )
    st.markdown(
        '<p class="how-note">Weights read live from src/recommender.py '
        "(W_CONTENT, W_DAYS, W_DIFF, W_BUDGET, CROWD_PENALTY) — not typed by hand.</p>",
        unsafe_allow_html=True,
    )

    st.markdown('<p class="how-h">Filters</p>', unsafe_allow_html=True)
    st.markdown(
        '<ul class="how-list">'
        "<li><b>Month</b> keeps only parks whose best months include the one you picked.</li>"
        "<li><b>Remote</b> drops parks that need a flight or ferry (Alaska, Hawaii, island parks) "
        "unless you allow them.</li>"
        "<li><b>Permits</b> drops parks with timed entry or a permit likely needed, unless you "
        "allow them.</li>"
        f"<li><b>Drive hours</b> drops parks outside your radius. Drive time is estimated as "
        f"straight-line distance &times; {DRIVE_DETOUR:g} detour factor, at {DRIVE_MPH:g} mph "
        "&mdash; a highway sketch, not turn-by-turn directions.</li>"
        "</ul>",
        unsafe_allow_html=True,
    )

    st.markdown('<p class="how-h">Evaluation</p>', unsafe_allow_html=True)
    result = load_evaluation()
    summary = pd.DataFrame(
        [
            {
                "Split": label,
                "n": result[key]["n"],
                "R-Precision": f'{result[key]["mean_r_precision"]:.3f}',
                "nDCG@5": f'{result[key]["mean_ndcg_at_k"]:.3f}',
            }
            for key, label in [("train", "Train"), ("holdout", "Holdout"), ("all", "Overall")]
        ]
    )
    st.dataframe(summary, hide_index=True, width="stretch")

    code_to_name = dict(zip(model.parks["park_code"], model.parks["name"]))
    for profile_row in result["all"]["profiles"]:
        relevant_codes = profile_row["relevant"]
        relevant_set = set(relevant_codes)
        label = (
            f'{profile_row["id"]} ({profile_row["split"]}) — '
            f'R-Prec {profile_row["r_precision"]:.2f} · nDCG {profile_row["ndcg_at_k"]:.2f}'
        )
        with st.expander(label):
            relevant_text = ", ".join(code_to_name.get(code, code) for code in relevant_codes)
            st.markdown(f"**Relevant:** {relevant_text}")
            top5_bits = []
            for code in profile_row["recommended"]:
                name = code_to_name.get(code, code)
                top5_bits.append(f"✓ **{name}**" if code in relevant_set else name)
            st.markdown("**Model's top 5:** " + " · ".join(top5_bits))

    st.markdown('<p class="how-h">Known limits</p>', unsafe_allow_html=True)
    st.markdown(
        '<ul class="how-list">'
        "<li>18 hand-written profiles &mdash; a regression check, not a user study or a blind "
        "holdout.</li>"
        "<li>The holdout split was seen during development; labels were revised once.</li>"
        "<li>Smoothed IDF down-weights common tags, so parks with extra rare tags the user did "
        "not ask for score a lower cosine.</li>"
        "<li>Drive times are a highway sketch (great-circle distance &times; detour &times; "
        "speed), not routed directions.</li>"
        "<li>Permit likelihood is a 2026-09 snapshot and will go stale.</li>"
        "</ul>",
        unsafe_allow_html=True,
    )


init_state()
model = load_model()
step = st.session_state.step
inject_base_css()
paint_background(step)

with st.container(key="app_shell"):
    with st.container(key="quiz_panel"):
        if step != "how_it_works":
            dots(step)

        if step == "welcome":
            st.markdown('<p class="quiz-title">Find the park that fits this trip.</p>', unsafe_allow_html=True)
            st.markdown(
                '<p class="quiz-sub">Six short questions. No dashboard. 63 U.S. National Parks.</p>',
                unsafe_allow_html=True,
            )
            if st.button("Start", type="primary", width="stretch"):
                go("terrain")
            if st.button("How it works", type="tertiary", width="stretch"):
                open_how_it_works()

        elif step == "terrain":
            st.markdown(
                '<p class="quiz-title">What kind of ground do you want under your boots?</p>',
                unsafe_allow_html=True,
            )
            terrain = catalog_terrains(model.parks)
            terrain_labels = dict(terrain)
            st.pills(
                "Terrain",
                options=[code for code, _ in terrain],
                format_func=terrain_labels.get,
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

        elif step == "results":
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
                render_top_card(ranked.iloc[0])
                rest = ranked.iloc[1:]
                if not rest.empty:
                    st.markdown('<p class="quiz-hint">More picks</p>', unsafe_allow_html=True)
                    rest_rows = list(rest.iterrows())
                    for start in range(0, len(rest_rows), 2):
                        cols = st.columns(2)
                        for col, (_, row) in zip(cols, rest_rows[start : start + 2]):
                            with col:
                                render_small_card(row)
            c1, c2, c3 = st.columns(3)
            if c1.button("Change answers", width="stretch"):
                go("terrain")
            if c2.button("How it works", type="tertiary", width="stretch"):
                open_how_it_works()
            if c3.button("Start over", width="stretch"):
                start_over()

        else:
            render_how_it_works(model)
