# US Parks Recommender

**Live demo:** https://us-national-parks-recommender.streamlit.app

Content-based recommender for the **63 U.S. National Parks**.

A trip profile (terrain, days, crowds, month, driving radius) is scored against
every park. Content overlap uses cosine similarity on biome + **IDF-weighted**
activity tags. Trip length, difficulty and budget use closeness
(`1 − |Δ| / max`). Crowds are a penalty. Month is a soft circular penalty on
distance to `best_months` (not a hard filter). Remote parks and permits are
hard filters.

The catalog is the official set of 63 national parks with structured tags.
This repo does not copy editorial content from any product site.

## Score

```
score = 0.55 * cosine(biome + IDF(tags))
      + 0.18 * days_closeness
      + 0.14 * difficulty_closeness
      + 0.08 * budget_closeness
      − 0.12 * max(0, park_crowd − wanted_crowd)
      − 0.35 * (month_distance / 6)
```

The last term is `W_MONTH_PENALTY * (month_distance / 6)` with
`W_MONTH_PENALTY=0.35` from `src/recommender.py`.
`month_distance` is the circular months to the nearest `best_months` entry
(December wraps to January). Max distance is 6. Remote parks, permits and
the optional `states` list (two-letter codes, e.g. `["UT"]`) stay hard
filters. Parks that cross state lines are listed under every state they
span, per NPS (Yellowstone `WY,MT,ID`), so `["MT"]` returns Yellowstone.

Drive time is `great_circle_miles × 1.25 / 65 mph`. That is a highway sketch,
not Google Maps. Each park has an `access` value (`road`, `boat`, `flight`).
With a drive limit, parks you can only fly to drop out, and boat parks show
the drive to the port as "~Xh drive + boat". With no drive limit, results say
"flight needed" or "boat needed". `permit_likely` is a coarse 2026-09 snapshot and will go stale.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

```bash
python -m src.cli --biome desert --tag hiking --tag stargazing \
  --days 2-3 --month 11 --origin san_diego --max-hours 8 --no-remote --explain

python -m src.evaluate
pytest
streamlit run app/streamlit_app.py
```

Starting point: `--zip 02108` (any 5-digit U.S. ZIP in the table below; ZIP+4
like `92101-1234` uses the first five digits) or a
city preset `--origin` (`san_diego`, `los_angeles`, `phoenix`, `denver`,
`seattle`, `salt_lake`, `nyc`). Passing both is an error. A bad ZIP stops
with `ZIP not found`. `--max-hours` only applies with a starting point.

## Metrics

18 hand-written fixtures. Treat them as a **regression suite**, not a blind
holdout or a user study. The holdout was seen during development. Labels were
revised once on 2026-09-21. Weights were not retuned after that pass.

Baselines and ablations use the same hard filters as the model (remote,
permits, drive hours). **Popularity** ranks by crowd high→low (ties by
`park_code`). **Random** is the mean of 100 shuffles of the filtered parks
(seeds 0–99). **Content-only** ranks by cosine similarity alone (no days,
difficulty, budget, crowd, or month terms). A profile is **filter-only** when
random scores 1.0 on both metrics — every remaining candidate is relevant, so
ranking cannot change the score.

Holdout averages about 22 candidates after hard filters versus about 42 on
train. Two holdout profiles (`washington_alpine`, `beginner_family_east`) are
filter-only and lift the holdout average; excluding them, holdout no longer
beats train on R-Precision.

| Method | Split | n | R-Precision | nDCG@5 |
|---|---|---|---|---|
| Model | Train | 12 | 0.708 | 0.764 |
| Model | Holdout | 6 | 0.794 | 0.813 |
| Model | All | 18 | 0.737 | 0.781 |
| Model (excl. filter-only) | Train | 12 | 0.708 | 0.764 |
| Model (excl. filter-only) | Holdout | 4 | 0.692 | 0.720 |
| Model (excl. filter-only) | All | 16 | 0.704 | 0.753 |
| Popularity | Train | 12 | 0.124 | 0.153 |
| Popularity | Holdout | 6 | 0.442 | 0.425 |
| Popularity | All | 18 | 0.230 | 0.243 |
| Popularity (excl. filter-only) | Train | 12 | 0.124 | 0.153 |
| Popularity (excl. filter-only) | Holdout | 4 | 0.163 | 0.137 |
| Popularity (excl. filter-only) | All | 16 | 0.133 | 0.149 |
| Random | Train | 12 | 0.136 | 0.185 |
| Random | Holdout | 6 | 0.483 | 0.498 |
| Random | All | 18 | 0.252 | 0.289 |
| Random (excl. filter-only) | Train | 12 | 0.136 | 0.185 |
| Random (excl. filter-only) | Holdout | 4 | 0.224 | 0.246 |
| Random (excl. filter-only) | All | 16 | 0.158 | 0.200 |
| Content-only | Train | 12 | 0.588 | 0.751 |
| Content-only | Holdout | 6 | 0.794 | 0.869 |
| Content-only | All | 18 | 0.656 | 0.790 |
| Content-only (excl. filter-only) | Train | 12 | 0.588 | 0.751 |
| Content-only (excl. filter-only) | Holdout | 4 | 0.692 | 0.804 |
| Content-only (excl. filter-only) | All | 16 | 0.614 | 0.764 |

**Ablation finding (weights unchanged):** Excluding filter-only profiles
(n=16), the full model scores R-Prec 0.704 / nDCG@5 0.753, and content-only
scores 0.614 / 0.764. The days, difficulty, budget, crowd, and month terms
raise R-Precision by about 0.09 but do not improve nDCG@5. On holdout,
content-only beats the full model on nDCG@5 (0.804 vs 0.720), but n=4 is too
small to conclude anything.

See `CHANGELOG.md` for the 50 mph drive bug. Those older figures are retired.

Yosemite `best_months` was missing July/August in the catalog; that is a
data fix, not a label tweak.

## External labels

Crowd labels from other people use the form in `docs/label-form.md`. Create the
Google Form with `scripts/create_label_form.gs` (generated by
`scripts/build_form_script.py` from the importer's titles/choices). Import a
CSV export with `scripts/import_form_labels.py`. Those profiles get
`split: "external"` and appear on their own evaluate lines. They are for
testing only — never tune on them. The `all` aggregate stays train + holdout.

## ZIP origins

`data/zcta_centroids.csv` maps 5-digit ZIP codes to coordinates (`zip,lat,lon`,
33,791 rows). It comes from the U.S. Census Bureau **2026 Gazetteer Files**,
ZIP Code Tabulation Areas national file (public domain):
https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2026_Gazetteer/2026_Gaz_zcta_national.zip
(index: https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html).
Each row is the ZCTA's internal point. ZCTAs approximate USPS ZIP codes; a
PO-box-only or brand-new ZIP may be missing. Rebuild with
`python scripts/build_zcta_table.py --year 2026` (downloads the file) or
`--source path/to/2026_Gaz_zcta_national.zip`.

Known limit: `access` assumes the trip starts on the U.S. mainland. A
traveler starting in Hawaii (e.g. ZIP 96720) with a drive limit loses the
Hawaii parks they could drive to, because `flight` parks always drop out
under a drive limit. Use Anywhere (no drive limit) to see them.

## Layout

```
data/parks.csv
data/zcta_centroids.csv
data/eval_profiles.json
data/engine_fixtures.json
docs/engine-contract.md
web/engine_data.json
scripts/export_engine_data.py
scripts/check_engine_version_bump.py
scripts/build_zcta_table.py
ts/
src/features.py
src/recommender.py
src/evaluate.py
src/cli.py
src/origins.py
src/zipcodes.py
app/streamlit_app.py
.github/workflows/ci.yml
```

## License

MIT. Park names are used descriptively. NPS logos and photography are not bundled.
