# Changelog

## 2026-10-08 — label form: clearer description and a response target (form text only)

- Form description now says labelers don't need to have visited the parks,
  that it takes about 3 minutes, and that no names or emails are collected.
  Why: people who think they must know a park tend to pick only famous ones,
  and a stated time and privacy line make strangers more likely to finish.
  Changed in `FORM_DESCRIPTION` (`scripts/import_form_labels.py`); the Apps
  Script was regenerated with `scripts/build_form_script.py`.
- `docs/label-form.md` gains "How many responses": target about 120, from a
  paired-test power estimate on the current per-profile spread (a 0.05 nDCG@5
  gap needs ~95 profiles; 0.10 needs ~25).
- No question, choice or importer column changed. Metrics unchanged.

## 2026-10-08 — evaluation: bootstrap ranges and paired tests (evaluation only)

- Why: 18 hand-written profiles is a small sample. Before tuning weights or
  adding features, we need to know which metric gaps are real and which are
  noise.
- New `src/uncertainty.py`: a 95% bootstrap range for each mean (10,000
  resamples of profiles, seed 0) and a paired test for two methods on the
  same profiles (bootstrap range of the mean difference plus an exact
  sign-flip p-value over all 2^n sign patterns). numpy, deterministic.
- `src.evaluate` prints a new "Uncertainty" section after the existing
  output and adds `result["uncertainty"]`, for train + holdout with and
  without filter-only profiles. Every earlier output line is unchanged.
- Finding: model vs content-only is +0.065 R-Prec (range −0.053 to +0.194,
  p=0.398) and −0.017 nDCG@5 (range −0.092 to +0.061, p=0.678): not
  distinguishable. Model vs popularity and vs random: p<0.001 on both
  metrics. README gains an Uncertainty section with these numbers.
- Metrics (unedited, unchanged): train R-Prec 0.685 / nDCG@5 0.739, holdout
  0.794 / 0.842, all 0.721 / 0.773. No weight, feature or label changed.

## 2026-10-08 — app: own background photos (app only)

- Replaced the stock Unsplash photos and Pexels videos behind the quiz with six
  photos taken by the author: Joshua Tree (sunset path, arch), Yosemite
  (El Capitan, forest) and Grand Canyon (trail, tree). Welcome and results
  share the sunset photo. The app no longer loads media from other sites.
- The photos sit in `app/static` (1440 × 1920 JPEG, 250-700 KB each, EXIF
  removed so no GPS data ships). `.streamlit/config.toml` turns on
  `enableStaticServing`.
- Dropped the looping videos: there are no author videos, and a photo is
  lighter on phones.
- `tests/test_app_backgrounds.py` checks each step has its file, the files
  carry no EXIF data, static serving is on, and no stock-site link is left.
- No engine change. `src.evaluate` output and the fixtures are identical.

## 2026-10-08 — app: quiz keeps its answers (app only)

- Bug: Streamlit deletes a widget's key once the widget is not drawn, and
  `init_state` then restored the default. Answers to terrain, activities,
  pace and month were lost on the next step, so the results page always ranked
  the defaults (desert, hiking, easy, 2-3 days, medium crowds, mid budget,
  November). Only the last step's answers (ZIP, states, toggles) survived.
- Fix: `keep_answers` saves every answer again on each run. The widgets no
  longer pass `default=`/`value=` next to a session key.
- New `tests/test_app_quiz_answers.py` walks the whole quiz with Streamlit's
  AppTest and a non-default answer on every step (forest, wildlife,
  challenging, 4-7 days, low crowds, high budget, July, ZIP 98101). It checks
  that the results match those answers. It fails on main without the fix.
- No engine change. `src.evaluate` output and the fixtures are identical.

## 2026-10-05 — app: results card polish (app only)

Measured in Chrome at 390 px wide (phone), before → after:
- Zero parts: Crowds and Season printed "−0.00" (a zero penalty is stored
  as −0.0) → "0". Labels now come from `format_contribution` in
  `app/breakdown.py` ("+0.26", "−0.12", "0"); the tooltip uses the same text.
- Bar spacing: the whole chart was 160 px tall including axis, title and
  legend, so 6 rows got ~13 px each while bars were a fixed 16 px and
  overlapped → each row is a 30 px step with bars at 60% of it
  (`paddingInner` 0.4), so bars are separate and labels no longer touch the
  next row's bar.
- Width and axis: the chart was 200 px wide on a 390 px phone (five nested
  paddings) and the axis ran to a nice 0.3 with no label plan → narrow
  screens trim the shell, panel, card and expander side padding, so the
  chart is 285 px wide, and the x bounds come from the data
  (`value_domain`), keeping 28% of the plot free for value labels on each
  side that has bars. The #24 axis settings (3 ticks, overlap removal) stay;
  no axis labels overlap at 390 px.
- Card header: "A fit score, not a probability. ·" wrapped and left a
  dangling dot → the states/drive line (`card_meta_html`) is its own line,
  with no-break spaces around every "·".
- `docs/demo.png`: new screenshot from a local run (Chromium, 390 px CSS
  width, device scale 3) of the quiz with canyon + hiking, easy, 2-3 days,
  medium crowds, mid budget, April, Anywhere: Capitol Reef National Park,
  Match 65%, why chart open. Clipped from the "These parks fit the trip."
  heading to the card bottom with an 8 px margin (1020 × 1947), resized to
  900 × 1718, 256-color PNG via libimagequant (141 KB). README alt text
  updated.
- Known bug, not fixed here: the quiz loses answers between steps.
  Streamlit deletes a widget's key once the widget is not drawn, and
  `init_state` then restores the default, so results always use the default
  answers (desert, hiking, easy, 2-3 days, medium, mid, November). The
  screenshot run used a local, uncommitted 5-line patch that re-assigns the
  answer keys each run; the card and chart code are exactly this release.
- No engine change: `data/engine_fixtures.json` (`--check`) and
  `web/engine_data.json` unchanged, and `src.evaluate` output is identical.
  Metrics (unedited, unchanged):
  - model train: R-Prec **0.685**, nDCG@5 **0.739** → **0.685** / **0.739**
  - model holdout: **0.794** / **0.842** → **0.794** / **0.842**
  - popularity, random and content-only baselines also unchanged.

## 2026-10-05 — demo screenshot: results card (docs only)

- `docs/demo.png` now shows a live-app results card after #24/#25 (Arches
  National Park, Match 63%, ~11.1h drive, the "Why this park" chart and
  sentence) instead of the last quiz step with the old low-contrast button.
- Source screenshot 1206 × 1603 (already cropped: no browser bars, no
  "Manage app" button, no "More picks"). Cropped from the heading "These
  parks fit the trip." to the Arches card's bottom border with an even 24 px
  margin, box (161, 1)–(1045, 1592) = 884 × 1591, then scaled up 1.8% to
  900 × 1620 and saved as a 256-color PNG with libimagequant (211 KB).
  Pillow's median-cut palette turned the red "Loss" legend swatch gray, so
  it was not used.
- README alt text updated to describe the new image.
- No code or engine change; metrics unchanged (train 0.685 / 0.739, holdout
  0.794 / 0.842, unedited).

## 2026-10-05 — README top for a quick read (docs only)

- New README top: one-sentence summary, live demo link and screenshot
  (`docs/demo.png`), "How it works" (5 bullets checked against the code), a
  short results table on all 18 profiles (model 0.721 / 0.773, content-only
  0.656 / 0.790, popularity 0.246 / 0.266, random 0.252 / 0.289; copied
  from `python -m src.evaluate`), "What I learned" and "What's next" (goal:
  beat content-only on nDCG@5).
- Removed the old intro paragraph that the new top duplicates. The
  editorial-content note moved to License; all other sections unchanged.
- `docs/demo.png`: phone screenshot of the last quiz step, resized from
  1206 × 1644 to 900 × 1227 and saved as a 256-color PNG (173 KB). It shows
  the See parks button before the contrast fix in the previous entry.
- No code or engine change; metrics unchanged (train 0.685 / 0.739, holdout
  0.794 / 0.842, unedited).

## 2026-10-05 — app: readable primary buttons (app only)

- Why: Start, Next and See parks had light text on cream and were hard to
  read on a phone. Streamlit draws primary buttons in the theme
  `primaryColor` (#e8d9b8) with white text.
- Contrast before → after (WCAG AA for text is 4.5:1; measured in Chrome at
  390 px wide, computed with the WCAG formula):
  - normal: white on #e8d9b8 **1.40** → #16210f on #e8d9b8 **11.96**
  - hover and keyboard focus: white on #d6bb80 **1.86** → #16210f on
    #d6bb80 **8.96**; focus also gets a 2 px #f7f1e4 outline
  - pressed: white on #e8d9b8 **1.40** → #16210f on #c9a96a **7.44**
  - disabled (Next with no terrain, See parks with an unknown ZIP): no
    fill, #f7f1e4 at 40% opacity on the quiz card, **3.06–3.47** → solid
    #b3ad9f, **5.26–8.86**, plus a dashed border so it still looks
    disabled. The range is the card (rgba(6, 14, 10, .82)) over a white vs
    a black photo.
- Colors and the contrast math live in `app/contrast.py`, which builds the
  CSS. `tests/test_contrast.py` checks every state is at least 4.5:1 and
  that the theme `primaryColor` is the cream the ratios assume.
- No engine change: `data/engine_fixtures.json` (`--check`) and
  `web/engine_data.json` unchanged, and `src.evaluate` output is identical.
  Metrics (unedited, unchanged):
  - model train: R-Prec **0.685**, nDCG@5 **0.739** → **0.685** / **0.739**
  - model holdout: **0.794** / **0.842** → **0.794** / **0.842**
  - popularity, random and content-only baselines also unchanged.

## 2026-10-05 — app: why-sentence wording, phone chart axis, no self demo link (app only)

- Why sentence (`app/breakdown.py`): it said "lost points for terrain" even
  when terrain was the biggest gain on the chart. Example: desert, hiking,
  easy, 2-3 days, mid budget, medium crowds, November. Death Valley's
  breakdown is terrain +0.26 (of 0.55), days +0.18, effort +0.07, budget
  +0.08, crowds 0, season 0.
  - Before: "Strong fit on length and budget; lost points for terrain."
  - After: "Strong fit on length and budget; partial match on terrain."
  - Now "lost points" is only for negative parts (crowds, season). A fit
    part that is positive but below the strong cutoff reads "partial match
    on <part>", and a fit part at 0.00 reads "no match on <part>".
  - The second clause no longer names a part that is already in "Strong
    fit". Before, terrain's 0.55 ceiling gave it the biggest absolute gap,
    which produced "Strong fit on terrain, length, and budget; lost points
    for terrain."
- Why chart: on a phone-width screen the x-axis labels ran together
  ("0.000.05"). Vega drew 0.05 steps despite `tickCount=4`. The axis now
  uses `tickCount=3`, `labelOverlap="greedy"`, `labelFlush=True`, font 10
  and format `.2~f` ("0.1", not "0.10"), which works at any width since
  Streamlit cannot see the screen size. Settings live in
  `VALUE_AXIS_LABELS`.
- Start screen: removed the "Live demo" link, which pointed at the app
  itself. The README keeps it.
- Tests: Death Valley case from the real engine, the bug-report numbers,
  strong parts not named in the second clause, zero fit, negative parts
  still "lost points" (crowds, season), and the axis settings.
- No engine change: `data/engine_fixtures.json` (`--check`) and
  `web/engine_data.json` unchanged, and `src.evaluate` output is identical.
  Metrics (unedited, unchanged):
  - model train: R-Prec **0.685**, nDCG@5 **0.739** → **0.685** / **0.739**
  - model holdout: **0.794** / **0.842** → **0.794** / **0.842**
  - model all: **0.721** / **0.773** → **0.721** / **0.773**
  - popularity, random and content-only baselines also unchanged.

## 2026-10-05 — month-aware crowd from NPS peak months (engine_version 0.5.0 → 0.6.0)

- Why: crowd is one fixed level per park, so Yosemite in January paid the
  same crowd penalty as Yosemite in July.
- Hypothesis (stated before the change): for a `crowd_pref` low user, parks
  outside their peak months rise, e.g. Zion in March or November (in season,
  not peak). Train metrics may move, because quiet-park profiles now meet
  busy parks with relief in their months.
- Rule: a month is a **peak month** when its NPS recreation visits are at
  least **0.7 × the park's busiest month**, using the 2023–2025 monthly
  average (`src/visits.py`, `PEAK_CUTOFF=0.7`). When the profile has a
  `month` that is not one of the park's peak months, the crowd penalty uses
  one level lower (high → medium, medium → low; low stays low). With no
  month, nothing changes. `facts.crowd` stays the catalog value.
- Shutdown rule: Oct 1–Nov 12, 2025 (federal shutdown) counts as missing
  data, not low visits. October and November average 2023 and 2024 only,
  for every park. Shutdown impact: **11 parks' peak sets changed** versus a
  plain 3-year average: acad −Oct, drto −Nov, havo −Nov, neri −Oct; npsa,
  blca, chis, maca, pefo +Oct; deva +Nov; kova +Oct,+Nov.
- Hawaii Volcanoes (havo): October does **not** become peak. October
  2023–24 averages 106,118 visits (113,614 and 98,621; 2025 was 125,237),
  below the cutoff 0.7 × January 168,049 = 117,634. Peak months are 1, 2,
  3, 4, 6, 7, 8, 9, 12; the shutdown rule removes November, which a plain
  3-year average had included.
- Peak-month distribution (parks per number of peak months): 1 month: 3
  parks (jeff, lavo July; shen October), 2: 9, 3: 13, 4: 12, 5: 13, 6: 4,
  7: 3, 8: 4, 9: 1 (havo), 12: 1 (hale). Examples: yose 6–10, zion 4–10,
  dena 6–8, jotr 2, 3, 4, 11, 12.
- `data/parks.csv` gains `peak_months` (after `best_months`, same quoted
  format), generated by `scripts/build_parks_csv.py` (byte-for-byte test) and
  checked against the raw data by `scripts/build_peak_months.py --check`.
  `src/catalog.py` rejects missing/empty values, tokens outside 1–12 and
  repeats.
- Known limit (spikes): a single spike month can define the whole peak.
  Gateway Arch (jeff, high) peaks only in July and Shenandoah (shen, high)
  only in October, so both count as medium the rest of the year, including
  Shenandoah's busy summer. Shenandoah now appears in some July lists.
- Crossover test (CLAUDE.md point 8), `crowd_pref` low:
  - (a) Yosemite, alpine/forest, hiking/waterfalls/photography, moderate,
    2-3 days, no origin. January: rank 2 → 2, score 0.3845 → 0.5045 (content
    0.7264, days/difficulty/budget 1.0, month penalty 0.175, crowd penalty
    0.24 → 0.12). kica stays #1 (0.508 → 0.628) because it gets the same
    relief. July (peak): unchanged, rank 2, 0.5595, crowd penalty 0.24. A
    realistic rank change does happen: climbing+hiking, alpine/forest, from
    Los Angeles within 8h, April: Yosemite 2 → 1 over Pinnacles (0.4769 →
    0.5969 vs 0.5853).
  - (b) Zion, canyon/desert, hiking/photography, moderate, 2-3 days, from
    Phoenix within 8h. March and November: Zion 2 → 1 over Death Valley,
    0.5665 → 0.6865 (crowd penalty 0.24 → 0.12) vs deva 0.5857 (March and
    November are deva peak months). The same holds with no origin and from
    LA, Salt Lake City and San Diego. May (Zion peak) is unchanged. Both
    cases are tests (`tests/test_peak_months.py`).
- Popularity baseline now ranks by average annual NPS recreation visits,
  2023–2025, same shutdown handling (top 5: grsm, zion, grca, yell, romo);
  it used to rank by catalog crowd high → low.
- Fixtures: 30 profiles (added `near_tie_no_month`, which keeps the cuva/acad
  near-tie coverage, and `off_peak_crowd_zion_march`). Rank changes:
  - `quiet_canyon` (Oct, low): blca, brca, care, arch, whsa → blca, brca,
    whsa, care, grsa
  - `avoid_permits_and_flights` (Apr, low): care, blca, pefo, cong, sagu →
    care, blca, cuva, grsa, pefo
  - `sierra_weekend_from_la` (Jul, medium): kica, seki, yose, zion, grca →
    kica, seki, yose, jotr, zion
  - `stargazing_desert` (Nov, low): deva, blca, care, whsa, sagu → care,
    deva, whsa, sagu, blca
  - `desert_weekend_from_sd` (Nov, medium): deva, sagu, jotr, pinn, zion →
    deva, sagu, jotr, zion, grca
  - `beginner_family_east` (May, medium): neri, cuva, acad, shen → acad,
    shen, neri, cuva (cuva/acad tie group gone)
  - `history_easy_walk` (May, medium): maca, jeff, … → jeff, maca, hosp,
    cave, cuva
  - `no_remote_no_permits_desert` (Nov, low): sagu, care, blca, deva, whsa →
    sagu, care, whsa, blca, deva
  - `null_enum_fields_use_defaults` (Nov): deva, care, arch, sagu, bibe →
    arch, deva, care, sagu, bibe
  - Score only: `cave_daytrip` and `midwest_easy` jeff +0.12. The other 17
    profiles keep order and scores; every park entry gains
    `facts.peak_months`.
- Result: metrics before / after (unedited). **Model train drops.**
  - model train: R-Prec **0.708**, nDCG@5 **0.764** → **0.685** / **0.739**
  - model holdout: **0.794** / **0.813** → **0.794** / **0.842**
  - model all: **0.737** / **0.781** → **0.721** / **0.773**
  - model excl. filter-only: train 0.708 / 0.764 → 0.685 / 0.739; holdout
    (n=4) 0.692 / 0.720 → 0.692 / 0.763; all (n=16) 0.704 / 0.753 → 0.686 /
    0.745
  - popularity: train 0.124 / 0.153 → 0.149 / 0.160; holdout 0.442 / 0.425
    → 0.442 / 0.479; all 0.230 / 0.243 → 0.246 / 0.266; excl. filter-only
    train 0.124 / 0.153 → 0.149 / 0.160, holdout 0.163 / 0.137 → 0.163 /
    0.218, all 0.133 / 0.149 → 0.152 / 0.174
  - random (0.136 / 0.185, 0.483 / 0.498, 0.252 / 0.289) and content-only
    (0.588 / 0.751, 0.794 / 0.869, 0.656 / 0.790) unchanged.
  - Train profiles that moved: `quiet_canyon` R 0.67 → 0.33, nDCG 0.70 →
    0.67 (whsa, off-peak in October, passes care); `avoid_permits_and_flights`
    R 0.60 → 0.40, nDCG 0.64 → 0.47; `stargazing_desert` R 0.50 → 0.75,
    nDCG 0.71 → 0.61.
  - Why train dropped: in both losing profiles, a park that matches the
    trip less well gains 0.12 from off-peak crowd relief and passes a
    relevant park that is at peak.
    - `quiet_canyon` (October): White Sands (desert, not a canyon; content
      0.427) loses its 0.12 crowd penalty because October is not one of its
      peak months (3, 4), and its score goes 0.515 → 0.635. That passes
      Capitol Reef (content 0.701, score 0.605), which is at peak in October
      and keeps its 0.12 penalty. Capitol Reef drops from #3 to #4.
    - `avoid_permits_and_flights` (April): Cuyahoga Valley (forest, content
      0.184) and Great Sand Dunes (desert, content 0.151) each gain 0.12
      (0.323 → 0.443 and 0.305 → 0.425) and enter at #3 and #4. That pushes
      Saguaro (content 0.204, score 0.392), at peak in April, from #5 to #7
      and out of the top 5. Both parks do match a biome the profile lists;
      they just match the whole trip less well than Saguaro.
    - The visit data is right. The hand-set weights let the crowd term
      (0.12 per level) outweigh terrain match differences, the same pattern
      as the content-only ablation, where content alone beats the full
      model on nDCG@5. Weights are not changed here; Task 9 will fit them
      from data.
  - Protocol note: holdout was read in the same single final run as train
    (no tuning loop; rule and cutoff were approved beforehand). Holdout up
    while train is down is a finding, not a reason to keep the change.
- Version 0.6.0 in `pyproject.toml`, `ts/package.json` + lockfile, fixture
  stamps, export and contract. `ts/src/engine.ts` mirrors the rule
  (`effectiveCrowdRank`), and the export carries `peak_months`.

## 2026-10-05 — NPS monthly visits and peak-month analysis (data, no model change)

- Why: crowd levels are fixed per park, so Yosemite gets the same crowd
  penalty in January as in July. A month-aware crowd needs real visitation
  data first.
- Added `data/raw/nps_recreation_visits_by_month_{2023,2024,2025}.json`: NPS
  Visitor Use Statistics monthly recreation visits for all 63 parks, saved
  verbatim from the IRMA REST endpoint (downloaded 2026-10-05). Catalog
  `seki` maps to NPS unit `SEQU`. October–November 2025 counts are low or
  zero for some parks (federal shutdown Oct 1–Nov 12, 2025).
- Added `scripts/build_peak_months.py` (analysis only) to print peak months
  under candidate cutoffs. No catalog, engine or evaluation change; metrics
  unchanged (train 0.708 / 0.764, holdout 0.794 / 0.813).

## 2026-10-05 — catalog tag cleanup (engine_version 0.4.0 → 0.5.0)

- Why: 14 tag entries in `data/parks.csv` were not in `TAG_VOCAB`, so scoring
  silently dropped them: note tags `remote` (gaar, glba, katm, kova, lacl,
  wrst), `low_crowd` (grba, gumo, noca, thro) and `permits` (zion), and biome
  names used as tags, `coast` (npsa) and `cave` (grba, pinn).
- Note tags removed. They repeat the `remote`, `crowd` and `permit_likely`
  columns; all 11 parks agree with their column (remote=1, crowd=low,
  permit_likely=1), and no column changed. On their own they move no score:
  `src.evaluate` output byte-identical, fixtures differ only in `facts.tags`.
- Biome tags moved into `biomes`, per NPS: npsa `rainforest|coast` (27 km of
  coastline, coral reefs, Ofu beaches), grba `alpine|cave` (Lehman Caves),
  pinn `chaparral|cave` (Bear Gulch and Balconies talus caves).
- `src/catalog.py` now rejects any tag outside `TAG_VOCAB`, naming the park
  and tag (`Park npsa: unknown tag 'coast' (not in TAG_VOCAB, so scoring
  would ignore it)`).
- Hypothesis (stated before the biome change, measured on a scratch copy):
  the biome edit changes content scores only for npsa, grba and pinn; no eval
  metric moves because none of them is in a relevant list it could enter or
  leave.
- Evidence: a plain cave search (`biomes=["cave"]`, no tags) before: wica
  0.633, cave 0.524, maca 0.465, ever 0.400, redw 0.400; after: wica 0.633,
  grba 0.548, cave 0.524, maca 0.465, pinn 0.411.
- Fixture changes (28 profiles):
  - `alaska_wildlife`: `glba, kefj, katm, voya, chis` →
    `glba, kefj, katm, npsa, voya` (npsa 0.5905 at #4; chis 0.5194 drops
    out; other scores unchanged).
  - `volcano_family`: npsa score 0.39657 → 0.382975 (match 42% → 40%), still
    #5; `why` adds "coast".
  - `desert_weekend_from_sd`: pinn score 0.251226 → 0.250043, still #4;
    `why` adds "cave".
  - `facts.tags` loses the removed tokens in 20 park entries across 13
    profiles, and `facts.biomes` gains coast/cave for npsa and pinn.
- Result: metrics before / after (unedited, identical). Only the
  `alaska_wildlife` top-5 line changes in the eval output (R 0.75, nDCG 0.83
  both before and after; neither npsa nor chis is relevant there).
  - model train: R-Prec **0.708**, nDCG@5 **0.764** → **0.708** / **0.764**
  - model holdout: R-Prec **0.794**, nDCG@5 **0.813** → **0.794** / **0.813**
  - model all: **0.737** / **0.781** → **0.737** / **0.781**
  - popularity, random and content-only baselines also unchanged.
- Version 0.5.0 in `pyproject.toml`, `ts/package.json` + lockfile, fixture
  stamps, export and contract. The TS engine needs no change (it reads tags,
  biomes and version from the export).


## 2026-10-05 — states filter (engine_version 0.3.0 → 0.4.0)

- Why: a "Utah canyons" trip returned Death Valley, Black Canyon and Big Bend
  in its top 5 and left Arches and Bryce at ranks 6–7. There was no way to
  say "Utah".
- New optional profile field `states` (list of two-letter codes, default
  null): a hard filter that keeps parks whose catalog `states` shares at least
  one code. Allowed codes: an explicit list of the 50 states, DC, AS, GU, MP,
  PR and VI (`STATE_CODES`); codes are trimmed and uppercased, duplicates
  dropped; `[]` means no filter, like null; anything else raises
  `InvalidProfileError` on field `states`. The catalog now validates its own
  state codes against the same list.
- Hypothesis (stated before coding): with `states` null, scores and order are
  identical for all existing profiles; the field only removes parks outside
  the listed states. Metrics should not move because no eval profile uses
  `states`.
- Evidence (canyon + desert, hiking / photography / stargazing, moderate,
  4–7 days, October): top 5 without states `deva, blca, care, bibe, cany`;
  with `states=["UT"]` `care, cany, arch, brca, zion`, same scores as before.
- Result: all 26 existing fixture outputs identical apart from the version
  stamp and the multi-state `facts.states` strings (below); no eval profile
  changed. Metrics before / after (unedited,
  identical):
  - model train: R-Prec **0.708**, nDCG@5 **0.764** → **0.708** / **0.764**
  - model holdout: R-Prec **0.794**, nDCG@5 **0.813** → **0.794** / **0.813**
  - model all: **0.737** / **0.781** → **0.737** / **0.781**
  - popularity, random and content-only baselines also unchanged.
- TS engine mirrors validation and filter; `web/engine_data.json` adds
  `vocab.states`. The fixture generator now owns its profile list (eval
  inputs from `data/eval_profiles.json`, edge cases in code) and pins two new
  profiles, `utah_canyons_states` and `pacific_northwest_states` (28 total).
  Version 0.4.0 in `pyproject.toml`, `ts/package.json` + lockfile, fixture
  stamps, export and contract.
- App: optional "Which states?" multiselect (states with parks, by name);
  empty means no filter.
- Multi-state parks: the catalog now lists every state a park spans, checked
  against the NPS API (`developer.nps.gov/api/v1/parks`, `fields=states`):
  Yellowstone `WY,MT,ID`, Great Smoky Mountains `TN,NC`, Death Valley
  `CA,NV` (comma-separated, main state first, the format the filter, TS
  engine and export already parse). `["MT"]` and `["ID"]` now return
  Yellowstone, `["NC"]` the Smokies, `["NV"]` Death Valley. The other 60
  parks are single-state per NPS (Kings Canyon via the joint `seki` entry,
  CA). Fixture outputs change only in `facts.states` (deva in 7 profiles,
  yell in 1); no score, order or metric change. The app shows "WY, MT, ID".


## 2026-10-05 — ZIP code starting point

- Why: the app and CLI only offered 7 city presets, so most U.S. travelers
  could not set their own starting point for the drive filter.
- Added `data/zcta_centroids.csv` (`zip,lat,lon`, 33,791 rows, ~0.9 MB) from
  the U.S. Census Bureau 2026 Gazetteer ZCTA national file (public domain),
  built by `scripts/build_zcta_table.py`. ZIPs stay 5-char strings with
  leading zeros; coordinates are the ZCTA internal points as printed by the
  Census (a leading "+" on Guam / CNMI longitudes is dropped).
- `src/zipcodes.py` `lookup_zip()` returns `(lat, lon)` or raises
  `ZipNotFoundError` ("ZIP not found") for input that is not five digits
  (or ZIP+4 like `92101-1234`, which uses the first five) or is not in the
  table. Malformed input such as `2108`, `abcde` or `92101-12` is rejected.
- App: the city list is replaced by a "Starting ZIP code" box. Empty means
  Anywhere (no origin, no drive limit). The Max drive hours slider shows and
  applies only for a valid ZIP. Bad input shows "ZIP not found" and disables
  See parks.
- CLI: new `--zip`, mutually exclusive with the `--origin` presets (kept).
  A bad ZIP exits with "ZIP not found".
- README notes a known limit: `access` assumes a U.S. mainland start, so a
  traveler starting in Hawaii with a drive limit loses Hawaii parks they
  could drive to.
- No engine, scoring, fixture, export or version change; the engine still
  takes lat/lon. Metrics unchanged: train 0.708 / 0.764, holdout
  0.794 / 0.813.


## 2026-10-05 — access cleanup: catalog build script and remote toggle

- `scripts/build_parks_csv.py` had drifted from `data/parks.csv` (single
  `biome` column, tags that repeat biome names, an old Yosemite
  `best_months`, CRLF line endings), so running it would have undone the
  multi-biome and tag cleanups. Its table now mirrors the committed catalog,
  and it writes the `access` column (flight: hale, havo, npsa, viis, gaar,
  glba, katm, kova, lacl; boat: chis, drto, isro; all others: road). A new
  test checks its output matches `data/parks.csv` byte for byte. The script
  needs no network or API key.
- App: the toggle "Include remote parks (AK, HI, ferry)" is now
  "Include remote parks", with help text explaining that results say when a
  park needs a boat or a flight.
- No engine, scoring, catalog, fixture, export or version change. Metrics
  unchanged: train 0.708 / 0.764, holdout 0.794 / 0.813.


## 2026-10-05 — park access: no drive times for parks you cannot drive to

- Why: the drive filter treated every park as drivable. From Los Angeles,
  Channel Islands showed "~1.3h drive" though you need a boat, and with
  `max_drive_hours=60` Hawaii Volcanoes passed as "~47.7h drive".
- Added an `access` column to `data/parks.csv` (`road` / `boat` / `flight`:
  how a traveler from the U.S. mainland gets there, checked against NPS
  Directions). flight: hale, havo, npsa, viis, gaar, glba, katm, kova, lacl.
  boat: chis, drto, isro. All others: road. `src/catalog.py` requires it and
  rejects any other value.
- With a drive limit (origin + `max_drive_hours`), `candidates()` drops flight
  parks. Boat parks keep the drive filter on park coordinates (drive to the
  port) and `why` says "~Xh drive + boat". With no drive limit, flight and
  boat parks stay and `why` says "flight needed" / "boat needed".
- Hypothesis (stated before coding): content / days / difficulty / budget /
  crowd / month scores do not change; only hard-filter membership (flight
  parks under a drive limit) and the `why` text change. Metrics move only if
  a drive-limited eval profile had a flight park among its candidates.
- Result: no eval profile changed. All six drive-limited profiles
  (midwest_easy, sierra_weekend_from_la, desert_weekend_from_sd,
  beginner_family_east, canyon_from_phoenix, washington_alpine) set
  `allow_remote=false`, and every flight park is `remote=1`, so none was a
  candidate before. Profiles without a drive limit keep the same lists and
  scores; only their `why` gains "flight needed" / "boat needed".
- Metrics before / after (unedited, identical):
  - model train: R-Prec **0.708**, nDCG@5 **0.764** → **0.708** / **0.764**
  - model holdout: R-Prec **0.794**, nDCG@5 **0.813** → **0.794** / **0.813**
  - model all: **0.737** / **0.781** → **0.737** / **0.781**
  - popularity, random and content-only baselines also unchanged.
- The label importer marks a flight park picked under a drive limit as
  unreachable with reason `drive`.
- Breaking change, `engine_version` 0.2.0 → 0.3.0 (`pyproject.toml`,
  `ts/package.json` + lockfile, fixture stamps, `web/engine_data.json`,
  `docs/engine-contract.md`). New `scripts/generate_engine_fixtures.py`
  regenerates `data/engine_fixtures.json` (it reproduced the 0.2.0 file byte
  for byte first). Fixture diff: no park order, score, tie group or
  drive_hours changed in the 26 profiles; 7 profiles without a drive limit
  gain "flight needed" / "boat needed" in `why`, and every park gains
  `facts.access`. The TS engine mirrors the filter and labels; TS parity now
  also checks `why` and `access`. The export carries `access` per park.
- The Streamlit result card shows the same travel note next to the state:
  "~Xh drive + boat", "boat needed" or "flight needed".


## 2026-10-05 — Apps Script generator for the label form

- Added `scripts/build_form_script.py`, which writes
  `scripts/create_label_form.gs` from `import_form_labels.get_form_spec()`
  (same titles and choices the CSV importer uses), so the form and importer
  cannot drift.
- `createLabelForm()` builds the Google Form (title, description, all 12
  questions, validations, responses sheet) and logs edit / public / sheet
  links. Step-by-step Apps Script run instructions are in the file header.
- Drift test fails if the committed `.gs` file is stale.
- Metrics unchanged (docs/scripts only): train 0.708 / 0.764, holdout
  0.794 / 0.813.


## 2026-10-05 — external importer drops unreachable picks

- Importer runs `ParkRecommender.candidates()` on each form profile. Top-3 picks
  that pass stay in `relevant`; picks that fail hard filters move to
  `unreachable` as `{"park_code", "reasons": ["drive"|"remote"|"permit", ...]}`.
  Rows with no reachable pick are skipped and reported.
- `src.evaluate` prints external unreachable pick counts by reason (drive /
  remote / permit). Many drive drops are a filter finding, not a ranking miss.
- Form copy: description "Picture one trip…" and Budget helper text about total
  travel cost (not entrance fee). Sample CSV + test cover the San Diego ≤6h /
  yell+havo+zion all-unreachable case.
- Metrics unchanged (no committed external rows; train/holdout/all same):
  train 0.708 / 0.764, holdout 0.794 / 0.813.


## 2026-10-05 — external label form + importer

- Added `docs/label-form.md`: Google Form blueprint with plain-English choices
  mapped to engine biomes, tags, enums, origins (+ Anywhere), and the 63 park
  names (exactly 3 top picks).
- Added `scripts/import_form_labels.py`: reads form CSV, validates each row with
  `validate_profile`, appends `split: "external"` profiles, skips bad rows.
  Never edits existing profiles or their `relevant` lists.
- `src.evaluate` reports the external split on its own lines (model, baselines,
  content-only, with/without filter-only). ``all`` remains train + holdout only
  so legacy metrics stay comparable. External is for testing only — never tune.
- Sample CSV + tests: `tests/fixtures/form_labels_sample.csv`,
  `tests/test_import_form_labels.py`.
- Metrics before → after (model train/holdout/all unchanged; no external rows
  in the committed fixtures yet):
  - train: R-Prec **0.708 → 0.708**, nDCG@5 **0.764 → 0.764**
  - holdout: R-Prec **0.794 → 0.794**, nDCG@5 **0.813 → 0.813**


## 2026-10-05 — filter-only ablation and public candidates()

- Renamed `ParkRecommender._filtered` → `candidates()` (public hard-filter
  step). Callers updated; behavior unchanged — not a scoring/engine bump.
- Evaluation now prints per-profile candidate counts and marks **filter-only**
  profiles where the random baseline scores 1.0 on both R-Precision and
  nDCG@5 (ranking cannot change the score). Current filter-only set:
  `beginner_family_east`, `washington_alpine`.
- Report every method with and without filter-only profiles.
- Added **content-only** ablation: rank candidates by cosine similarity alone
  (shows what days / difficulty / budget / crowds / month add).
- README Metrics table expanded with content-only and excl. filter-only rows,
  plus two sentences on why holdout averages higher than train (smaller
  candidate sets; filter-only holdout profiles).
- Metrics before → after (model unchanged):
  - model train: R-Prec **0.708 → 0.708**, nDCG@5 **0.764 → 0.764**
  - model holdout: R-Prec **0.794 → 0.794**, nDCG@5 **0.813 → 0.813**
  - model holdout excl. filter-only: R-Prec **0.692**, nDCG@5 **0.720**
  - content-only train: R-Prec **0.588**, nDCG@5 **0.751**
  - content-only holdout: R-Prec **0.794**, nDCG@5 **0.869**
- **Finding (no weight change):** Excluding filter-only profiles (n=16), the
  full model scores R-Prec 0.704 / nDCG@5 0.753 versus content-only 0.614 /
  0.764. Days, difficulty, budget, crowd, and month raise R-Precision by about
  0.09 but do not improve nDCG@5. On holdout, content-only beats the full model
  on nDCG@5 (0.804 vs 0.720), but n=4 is too small to conclude anything.


## 2026-10-05 — evaluation baselines (popularity + random)

- Added popularity and random baselines to `src.evaluate` so model metrics have
  something to beat. Both reuse the model's hard-filtered candidate set
  (remote, permits, drive hours) for a fair comparison. Scoring, filters,
  catalog, and engine version are unchanged.
- **Popularity:** rank filtered parks by crowd high→low, ties by `park_code`
  ascending.
- **Random:** mean R-Precision and nDCG@5 over 100 shuffles (seeds 0–99) of the
  filtered parks (deterministic base order: `park_code` ascending).
- Printed comparison table: Model / Popularity / Random × train / holdout / all.
- README Metrics table expanded with baseline rows; `tests/test_metrics_pinned.py`
  pins model and baseline numbers against README.
- Metrics before → after (model unchanged; baselines new):
  - model train: R-Prec **0.708 → 0.708**, nDCG@5 **0.764 → 0.764**
  - model holdout: R-Prec **0.794 → 0.794**, nDCG@5 **0.813 → 0.813**
  - popularity train: R-Prec **0.124**, nDCG@5 **0.153**
  - popularity holdout: R-Prec **0.442**, nDCG@5 **0.425**
  - random train: R-Prec **0.136**, nDCG@5 **0.185**
  - random holdout: R-Prec **0.483**, nDCG@5 **0.498**


## 2026-09-26 — engine_version 0.1.0 → 0.2.0 (retroactive)

- Bumped `engine_version` to `0.2.0` in `pyproject.toml`, `ts/package.json`
  (+ lockfile root), every stamp in `data/engine_fixtures.json`, the
  regenerated `web/engine_data.json`, and `docs/engine-contract.md`.
- Why: `0.1.0` was stamped when the contract landed (PR #5) but stayed in
  place through two changes that `docs/engine-contract.md` §4 says must bump
  the version, so one version string described two different pinned
  behaviors. This bump retroactively covers:
  - PR #7 — portable `park_code` tie-break changed park order for
    `empty_content_defaults` (`havo,viis,thro` → `care,havo,lavo` in the 0.36
    tier) and its `tie_groups`.
  - PR #9 — explicit `null` on `difficulty` / `days_needed` / `crowd_pref` /
    `budget_tier` now applies the documented default instead of raising, and
    a new pinned profile `null_enum_fields_use_defaults` (25 → 26 fixtures).
- Done before any consumer pins a commit, so the first pin starts from an
  honest version number. No scoring, catalog, or fixture-content change in
  this entry; metrics unchanged: train 0.708 / 0.764, holdout 0.794 / 0.813.

## 2026-09-26 — CI enforces engine_version bump on fixture changes

- Added `scripts/check_engine_version_bump.py` and an `engine-version` CI job
  (pull requests only). It compares `data/engine_fixtures.json` between the PR
  and its base branch, ignoring only the file's own `engine_version` stamps and
  prose `notes`. If park order, scores, breakdown, facts, tie_groups, weights,
  `tie_epsilon`, `k`, or the set of pinned profiles (added/removed) differ,
  `pyproject.toml` `[project].version` must also differ, or the job fails
  pointing to `docs/engine-contract.md` §4. Identical fixtures need no bump.
  The fixture stamps must also equal the pyproject version, so a bump cannot
  leave the parity file on the old number.
- Why: §4 had no enforcement. Run retroactively, the check fails PR #7
  (`empty_content_defaults` order `havo,viis,thro` → `care,havo,lavo`) and
  PR #9 (added profile `null_enum_fields_use_defaults`), and passes #6 and #8.
- No scoring/data changes; metrics unchanged: train 0.708 / 0.764, holdout
  0.794 / 0.813.

## 2026-09-26 — enum null equals omit (parity)

- Found: `crowd_pref=None` raised in Python while `crowd_pref=null` used the
  default in TypeScript (`??`). Same gap for other enum fields with defaults.
- Decision: explicit null on `difficulty` / `days_needed` / `crowd_pref` /
  `budget_tier` means "not specified" — apply the documented default, then
  validate. Only non-null out-of-enum values raise. `month` / `max_drive_hours`
  unchanged (`null` = no constraint).
- Pinned with edge fixture `null_enum_fields_use_defaults` (26 profiles total)
  and cross-language tests. Metrics unchanged.

## 2026-09-26 — profile input validation

- Hypothesis: out-of-enum profile fields (e.g. `difficulty="hard"`) crashed with
  an unhandled `KeyError`; an LLM concierge will plausibly hallucinate values
  outside the documented vocab and needs a clear typed failure.
- Added `InvalidProfileError` + `validate_profile()` for enums, `month` (null or
  1–12), and positive `max_drive_hours`. Unknown biomes/tags stay silently
  ignored. Same validation in `ts/src/engine.ts`.
- Hard-filter property tests + invalid/silent-ignore cases. Contract §1
  documents raise vs ignore. Bumped Vitest to clear moderate npm advisories.
- Metrics unchanged (validation only; scoring path untouched for valid input).

## 2026-09-26 — TypeScript engine port with fixture parity

- Added `ts/`: pure TypeScript port of `ParkRecommender.recommend()` that loads
  all constants from `web/engine_data.json` at runtime (no hardcoded catalog,
  weights, or vocab). Output matches `docs/engine-contract.md` §2.
- Vitest parity: all 25 `data/engine_fixtures.json` profiles — park order,
  scores/breakdown within 1e-6, match_percent, drive_hours, tie_groups.
- CI: Node job runs `npm ci` + `npm test` in `ts/` alongside the Python job.
- No Python scoring/data changes; metrics unchanged.

## 2026-09-26 — portable park_code tie-break

- Hypothesis: pandas `sort_values` defaults to unstable quicksort, so exact
  score ties resolve by an undocumented algorithm detail instead of a portable
  rule (confirmed on `empty_content_defaults`: care/havo/lavo/thro/viis at
  0.36 ordered `havo,viis,thro,lavo,care` — not catalog order).
- `ParkRecommender.recommend()` now sorts by score desc, then `park_code` asc
  (`kind="stable"`). Scores, hard filters, and non-tied rankings unchanged.
- Regenerated `data/engine_fixtures.json`. `empty_content_defaults` top-5
  `havo,viis,thro` → `care,havo,lavo` among the 0.36 tier; other exact-tie
  profiles (`gaar`/`kova`) already matched alphabetical order.
- Export JSON-only test re-derives order independently (no pandas sort mirror).
- Contract §3 Determinism documents the `park_code` ascending tie-break.
- Metrics unchanged: train 0.708 / 0.764, holdout 0.794 / 0.813.

## 2026-09-26 — engine data export for non-Python consumers

- Added `scripts/export_engine_data.py` → `web/engine_data.json`: catalog,
  weights (incl. `TIE_EPSILON`, drive model), biome/tag vocab + IDF, ordinal
  maps, `engine_version`, and `content_hash` (sha256 of `parks.csv`). Every
  value is imported from the live validated engine, not hand-copied.
- `tests/test_export_engine_data.py` recomputes score / breakdown / tie_groups
  from the JSON alone for all 25 fixture profiles and matches
  `ParkRecommender.recommend()` within 1e-6.
- CI fails if a fresh export drifts from the committed `web/engine_data.json`.
- Named `EARTH_RADIUS_MILES` in `src/features.py` (same 3958.8 value) so the
  export can import the drive-model radius. No scoring change.
- Metrics unchanged: train 0.708 / 0.764, holdout 0.794 / 0.813.

## 2026-09-26 — tie_groups in ParkRecommender.recommend()

- Hypothesis: the engine contract's tie annotation (`tie_epsilon=0.001`) should
  live in `ParkRecommender.recommend()` so ports and the concierge get real
  `tie_groups` / `tied_with_neighbors`, not fixture-only labels. Annotation
  must not reorder parks or change scores.
- Added `TIE_EPSILON = 0.001` and `annotate_ties()`; `recommend()` attaches
  `tied_with_neighbors` and `attrs["tie_groups"]`. Verified exact match against
  all 25 profiles in `data/engine_fixtures.json` (fixtures unchanged).
- Metrics before → after (ranking unchanged):
  - train: R-Prec **0.708 → 0.708**, nDCG@5 **0.764 → 0.764**
  - holdout: R-Prec **0.794 → 0.794**, nDCG@5 **0.813 → 0.813**

## 2026-09-26 — engine contract and parity fixtures

- Added `docs/engine-contract.md`: trip-profile input schema, ranked output
  (score, breakdown, drive hours, quotable facts), determinism / hard-filter /
  tie guarantees, `engine_version`, planned JSON export + TypeScript port with
  CI parity, concierge tool rules, and trail-level out of scope. No scoring
  change.
- Added `data/engine_fixtures.json`: 25 profiles (18 eval + 7 edge cases) with
  the current Python `ParkRecommender` output for a future port parity test.

## 2026-09-26 — Streamlit Cloud install

- `requirements.txt` ends with `-e .` so Streamlit Cloud's
  `pip install -r requirements.txt` also installs the local package from
  `pyproject.toml` (app/ and src/ importable). No scoring change.

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
