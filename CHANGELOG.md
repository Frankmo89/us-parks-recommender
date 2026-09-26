# Changelog

## 2026-09-26 — README metrics and pinned-test hardening

- README Metrics table set to train 0.708 / 0.764 and holdout 0.794 / 0.813.
  Month described as a soft penalty; score formula uses live
  `W_MONTH_PENALTY` (0.35). No scoring change.
- `tests/test_metrics_pinned.py` parses the README Metrics table instead of
  hardcoded constants, so README ↔ evaluate drift fails with a clear message.

## 2026-09-26 — multi-biome catalog

- Hypothesis: a single biome column drops real matches (Yellowstone is alpine
  and forest, but a forest trip never scores the forest half).
- Renamed `biome` → `biomes` (pipe-separated). Parks keep one biome or get a
  clearly secondary one (e.g. yell `alpine|forest`); no padding.
- Content vectors pass the full biome list into the existing multi-hot.
  Catalog validation checks every listed biome. Terrain picker options come
  from every token across parks.
- Crossover (forest / hiking / wildlife / scenic_drive / 4–7 days / July):
  Yellowstone **#12 → #9**, content **0.163 → 0.322**.
- Metrics before → after (on top of soft month W=0.35):
  - train: R-Prec **0.729 → 0.708**, nDCG@5 **0.765 → 0.764**
  - holdout: R-Prec **0.794 → 0.794**, nDCG@5 **0.808 → 0.813**

## 2026-09-25 — soft month penalty

- Hypothesis: a hard month filter drops otherwise-good parks; a soft circular
  month penalty (same shape as crowd) should keep shoulder-season parks
  rankable, and strong content should still beat a weak in-season match
  when the season miss is moderate.
- Replaced the hard `best_months` filter with
  `month_penalty = (month_distance / 6) * W_MONTH_PENALTY`. Distance wraps
  Dec↔Jan. `profile.month is None` → penalty 0. Remote / permits / drive
  filters unchanged.
- Weight selection:
  - `1.60` rejected (rule 8): a 2-month miss (0.533) outweighed a ~20×
    content lead — romo lost to sagu on alpine/wildlife/family/November.
  - **`0.35` set as requested**: max 6-month penalty ≈ 0.35 (< W_CONTENT
    0.55); 2-month miss ≈ 0.117.
- Crossover (alpine / wildlife / scenic_drive / family / 4–7 days /
  month=11): romo content 0.799, month_pen 0.117, score **0.473** beats
  sagu content 0.040, month_pen 0.000, score **0.262**. Yellowstone
  (dist=2, month_pen 0.117) ranks **#13**, score 0.351.
- Metrics before → after (`W_MONTH_PENALTY=0.35`):
  - train: R-Prec **0.804 → 0.729**, nDCG@5 **0.838 → 0.765**
  - holdout: R-Prec **0.794 → 0.794**, nDCG@5 **0.820 → 0.808**
  Holdout R-Prec flat; nDCG dips slightly. Reported unedited; not used to
  retune.
- How it works / README formula updated; month is no longer a hard filter.

## 2026-09-25 — UI and tooling

- Terrain picker now lists every biome in `parks.csv` (was 8 of 14), so
  prairie, tundra, island, rainforest, chaparral, and urban appear and new
  catalog biomes cannot drift out of the UI.
- `requirements.txt` pins exact installed versions (`pip freeze`), not floors.
- Added `pyproject.toml` for an editable install; Streamlit no longer hacks
  `sys.path`.
- `tests/test_metrics_pinned.py` asserts train/holdout R-Precision and
  nDCG@5 match the README figures exactly (to 3 decimals).
- Catalog load validates biome, tags, and `best_months` tokens and raises
  naming the bad `park_code` (no scoring change).
- Result cards caption the Match % badge: "A fit score, not a probability."
- How it works notes that eval profiles have no chaparral case and only one
  island case.
- Removed redundant own-biome tokens from `parks.csv` tags (they were never
  in TAG_VOCAB, so scoring is unchanged). Validator now rejects that pattern.

## 2026-09-21 — CLAUDE.md and drive test lower bound

- Added `CLAUDE.md` with rules for this repo: model/data change scope,
  required checks (`pytest`, `src.evaluate`), changelog discipline, style,
  and commit size.
- `test_drive_hours_use_catalog_coordinates` now also asserts San Diego to
  Joshua Tree is more than 1.5 h, not just under 3.5 h, so the test catches
  a drive model that becomes unrealistically fast. No model change; current
  value is ~2.0 h. Metrics unchanged (train R-Prec 0.804 / nDCG 0.838,
  holdout 0.794 / 0.820).

## 2026-09-21 — docs and fixture honesty

- README / eval JSON no longer call the holdout "blind". It was seen during
  development; labels were revised once. Treat the suite as regression checks.
- `quiet_canyon` no longer lists Bryce (`crowd=high`) as relevant for a
  low-crowd profile.
- Drive-hour tests now read lat/lon from `parks.csv` instead of hardcoded
  coordinates that were not the catalog values.

## 2026-09-21 — drive model and labels

- Drive speed 50 mph → 65 mph. With the 1.25 detour factor the old setting
  behaved like 40 mph, so Saguaro was scored at ~10 h from San Diego
  (real drive ~6 h) and dropped out of an 8 h radius.
- Evaluation labels rewritten once the same day. Previous holdout numbers
  (R-Prec 0.736 / nDCG 0.840) were computed under the slow drive model
  and are retired.
- Yosemite `best_months` now includes July and August (catalog error).
- Test `test_easy_short_trip_ranks_joshua_tree_ahead_of_far_saguaro` removed.
  It passed only because Saguaro was filtered out.
- Activity tags use smoothed IDF so ubiquitous tags like `hiking` do not
  dominate rarer ones like `stargazing`. Side effect: parks with extra rare
  tags the user did not ask for get a longer content vector and a lower cosine.
- Imports moved to the top of `recommender.py`. Streamlit `use_container_width`
  replaced with `width="stretch"`.
