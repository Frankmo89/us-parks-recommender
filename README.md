# US Parks Recommender

Content-based recommender for the **63 U.S. National Parks**.

You describe a trip (terrain, days, crowds, month, driving radius). The model ranks parks in the same feature space with **cosine similarity**, then applies hard filters (season, remote parks, permits, max drive hours).

This repo is standalone. It does **not** copy editorial content from any product site.

## What I built vs. what I used

| Piece | Source |
|---|---|
| Catalog of 63 parks + coordinates | Public NPS identities |
| Feature tags | Curated in `data/parks.csv` |
| Ranking model | `src/recommender.py` |
| Evaluation | `data/eval_profiles.json` |
| UI | Streamlit demo |

Not in this project: LLM wrappers, booking, trail-by-trail routing.

## How the model works

1. Each park becomes a vector: biome, tags, difficulty, trip length, crowd, budget, season, permit, remote.
2. The user profile is encoded in that same space.
3. Rank by cosine similarity.
4. Filter out-of-season, too-far, remote, or permit parks when asked.
5. Crowd penalty when the user wants solitude.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/build_parks_csv.py   # already committed
```

## CLI

```bash
python -m src.cli --biome desert --tag hiking --tag stargazing --days 2-3 --month 11 --crowd low --origin san_diego --max-hours 8 --no-remote
```

Origins: san_diego, los_angeles, phoenix, denver, seattle, salt_lake, nyc.

## Demo

```bash
streamlit run app/streamlit_app.py
python -m src.evaluate
```

Current catalog: **Precision@5 = 0.60** on six labeled profiles.

## License

MIT.
