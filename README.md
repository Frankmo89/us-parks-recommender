# US Parks Recommender

Content-based recommender for the **63 U.S. National Parks**.

A trip profile (terrain, days, crowds, month, driving radius) is scored against
every park. Content overlap uses cosine similarity on biome + **IDF-weighted**
activity tags. Trip length, difficulty and budget use closeness
(`1 − |Δ| / max`). Crowds are a penalty only. Season, remote parks and permits
are hard filters.

The catalog is the official set of 63 national parks with structured tags.
This repo does not copy editorial content from any product site.

## Score

```
score = 0.55 * cosine(biome + IDF(tags))
      + 0.18 * days_closeness
      + 0.14 * difficulty_closeness
      + 0.08 * budget_closeness
      − 0.12 * max(0, park_crowd − wanted_crowd)
```

Drive time is `great_circle_miles × 1.25 / 65 mph`. That is a highway sketch,
not Google Maps. `permit_likely` is a coarse 2026-09 snapshot and will go stale.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

```bash
python -m src.cli --biome desert --tag hiking --tag stargazing \
  --days 2-3 --month 11 --origin san_diego --max-hours 8 --no-remote --explain

python -m src.evaluate
pytest
streamlit run app/streamlit_app.py
```

Origins: `san_diego`, `los_angeles`, `phoenix`, `denver`, `seattle`, `salt_lake`, `nyc`.

## Metrics

18 hand-written fixtures. Treat them as a **regression suite**, not a blind
holdout or a user study. The holdout was seen during development. Labels were
revised once on 2026-09-21. Weights were not retuned after that pass.

| Split | n | R-Precision | nDCG@5 |
|---|---|---|---|
| Train | 12 | 0.804 | 0.838 |
| Holdout | 6 | 0.794 | 0.820 |

See `CHANGELOG.md` for the 50 mph drive bug. Those older figures are retired.

Yosemite `best_months` was missing July/August in the catalog; that is a
data fix, not a label tweak.

## Layout

```
data/parks.csv
data/eval_profiles.json
src/features.py
src/recommender.py
src/evaluate.py
src/cli.py
src/origins.py
app/streamlit_app.py
.github/workflows/ci.yml
```

## License

MIT. Park names are used descriptively. NPS logos and photography are not bundled.
