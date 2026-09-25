# Changelog

## 2026-09-25 — UI and tooling

- Terrain picker now lists every biome in `parks.csv` (was 8 of 14), so
  prairie, tundra, island, rainforest, chaparral, and urban appear and new
  catalog biomes cannot drift out of the UI.
- `requirements.txt` pins exact installed versions (`pip freeze`), not floors.
- Added `pyproject.toml` for an editable install; Streamlit no longer hacks
  `sys.path`.
- `tests/test_metrics_pinned.py` asserts train/holdout R-Precision and
  nDCG@5 match the README figures exactly (to 3 decimals).

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
