# External trip label form

Use this as the blueprint for a Google Form (or any form that can export CSV).
Each response is one trip profile for the ranking engine, plus the person's
**top 3 national parks** for that trip. Imported rows become `split: "external"`
in `data/eval_profiles.json` and are **for testing only — never tune on them**.

Engine field names and allowed values match `docs/engine-contract.md`.
Import with `scripts/import_form_labels.py`.

### Form description (paste at the top of the Google Form)

```text
Picture one trip you would really take. Answer for that trip, then pick the 3 parks that fit it best.
```

## Form questions (exact choices)

Copy the question text as the form field title so CSV column headers match.
Where a mapping is shown, the left side is what the respondent sees; the right
side is the engine token the importer stores.

### 1. Terrains you want (multi-select)

**Question:** `Terrains you want`

Select all that apply. Empty is allowed (activities alone can drive content match).

   - Mountains / alpine  → `alpine`
   - Canyon  → `canyon`
   - Cave  → `cave`
   - Chaparral / scrub  → `chaparral`
   - Coast  → `coast`
   - Desert  → `desert`
   - Forest  → `forest`
   - Island  → `island`
   - Prairie / grassland  → `prairie`
   - Rainforest  → `rainforest`
   - Tundra  → `tundra`
   - Urban  → `urban`
   - Volcano  → `volcano`
   - Wetland  → `wetland`

### 2. Activities you want (multi-select)

**Question:** `Activities you want`

Prefer 2–4. Empty is allowed.

   - 4x4 / off-road  → `4x4`
   - Archaeology  → `archaeology`
   - Backpacking  → `backpacking`
   - Beach  → `beach`
   - Bears  → `bears`
   - Biking  → `biking`
   - Birding  → `birding`
   - Boardwalk  → `boardwalk`
   - Boat  → `boat`
   - Camping  → `camping`
   - Climbing  → `climbing`
   - Easy walk  → `easy_walk`
   - Family-friendly  → `family`
   - Fishing  → `fishing`
   - Geothermal  → `geothermal`
   - Giant trees  → `giant_trees`
   - Glacier  → `glacier`
   - Hiking  → `hiking`
   - History  → `history`
   - Hot springs  → `hot_springs`
   - Kayak  → `kayak`
   - Paleontology  → `paleontology`
   - Photography  → `photography`
   - Sand dunes  → `sand`
   - Scenic drive  → `scenic_drive`
   - Snorkeling  → `snorkeling`
   - Stargazing  → `stargazing`
   - Sunrise / sunset views  → `sunrise`
   - Water / lakes  → `water`
   - Waterfalls  → `waterfalls`
   - Wilderness  → `wilderness`
   - Wildflowers  → `wildflowers`
   - Wildlife  → `wildlife`
   - Winter activities  → `winter`

### 3. Difficulty

**Question:** `Difficulty`

Single choice:

   - Easy  → `easy`
   - Moderate  → `moderate`
   - Challenging  → `challenging`

### 4. Trip length

**Question:** `Trip length`

Single choice:

   - Day trip  → `1`
   - Weekend (2–3 days)  → `2-3`
   - About a week (4–7 days)  → `4-7`
   - Longer than a week  → `7+`

### 5. Crowd preference

**Question:** `Crowd preference`

Single choice:

   - Prefer quiet / low crowds  → `low`
   - Medium is fine  → `medium`
   - Busy / popular is fine  → `high`

### 6. Budget (travel cost to reach and stay, not entrance fee)

**Question:** `Budget`

**Helper text (paste under the question):** Your total travel cost: gas or flights, lodging and food. Not the entrance fee.

Single choice:

   - Low  → `low`
   - Mid  → `mid`
   - High  → `high`

### 7. Month you want to go (optional)

**Question:** `Month you want to go`

Single choice, or leave blank for no season preference:

   - January … December  → `1` … `12`
   - No preference / not sure  → *(empty → `month: null`)*

### 8. Starting city

**Question:** `Starting city`

Single choice:

   - San Diego  → `san_diego`
   - Los Angeles  → `los_angeles`
   - Phoenix  → `phoenix`
   - Denver  → `denver`
   - Seattle  → `seattle`
   - Salt Lake City  → `salt_lake`
   - New York City  → `nyc`
   - Anywhere  → *(no drive filter; leave origin and max hours empty)*

### 9. Max drive hours from that city

**Question:** `Max drive hours`

Short answer, positive number (e.g. `8`).

- Required when Starting city is **not** Anywhere.
- Leave blank when Starting city is Anywhere (no drive hard filter).

### 10. Allow remote parks? (Alaska, Hawaii, ferry-only, etc.)

**Question:** `Allow remote parks`

Single choice:

   - Yes  → `allow_remote: true`
   - No  → `allow_remote: false`

### 11. Allow parks that likely need timed entry or a permit?

**Question:** `Allow parks that need permits`

Single choice:

   - Yes  → `allow_permits: true`
   - No  → `allow_permits: false`

### 12. Your top 3 parks for this trip

**Question:** `Top 3 parks`

Checkbox list of all 63 U.S. National Parks. **Require exactly 3 selections.**
Use these exact names (catalog `name` column):

   - Acadia National Park
   - National Park of American Samoa
   - Arches National Park
   - Badlands National Park
   - Big Bend National Park
   - Biscayne National Park
   - Black Canyon of the Gunnison National Park
   - Bryce Canyon National Park
   - Canyonlands National Park
   - Capitol Reef National Park
   - Carlsbad Caverns National Park
   - Channel Islands National Park
   - Congaree National Park
   - Crater Lake National Park
   - Cuyahoga Valley National Park
   - Death Valley National Park
   - Denali National Park
   - Dry Tortugas National Park
   - Everglades National Park
   - Gates of the Arctic National Park
   - Gateway Arch National Park
   - Glacier National Park
   - Glacier Bay National Park
   - Grand Canyon National Park
   - Grand Teton National Park
   - Great Basin National Park
   - Great Sand Dunes National Park
   - Great Smoky Mountains National Park
   - Guadalupe Mountains National Park
   - Haleakala National Park
   - Hawaii Volcanoes National Park
   - Hot Springs National Park
   - Indiana Dunes National Park
   - Isle Royale National Park
   - Joshua Tree National Park
   - Katmai National Park
   - Kenai Fjords National Park
   - Kings Canyon National Park
   - Kobuk Valley National Park
   - Lake Clark National Park
   - Lassen Volcanic National Park
   - Mammoth Cave National Park
   - Mesa Verde National Park
   - Mount Rainier National Park
   - New River Gorge National Park
   - North Cascades National Park
   - Olympic National Park
   - Petrified Forest National Park
   - Pinnacles National Park
   - Redwood National Park
   - Rocky Mountain National Park
   - Saguaro National Park
   - Sequoia National Park
   - Shenandoah National Park
   - Theodore Roosevelt National Park
   - Virgin Islands National Park
   - Voyageurs National Park
   - White Sands National Park
   - Wind Cave National Park
   - Wrangell-St. Elias National Park
   - Yellowstone National Park
   - Yosemite National Park
   - Zion National Park

## CSV columns expected by the importer

Google Forms exports one column per question title, plus `Timestamp`.

| CSV column | Engine field(s) | Notes |
|---|---|---|
| `Timestamp` | *(id seed)* | Used to build a stable `external_…` id |
| `Terrains you want` | `biomes` | Multi-select; labels mapped to tokens |
| `Activities you want` | `tags` | Multi-select; labels mapped to tokens |
| `Difficulty` | `difficulty` | |
| `Trip length` | `days_needed` | |
| `Crowd preference` | `crowd_pref` | |
| `Budget` | `budget_tier` | |
| `Month you want to go` | `month` | Blank / "No preference" → null |
| `Starting city` | `origin_lat`, `origin_lon` | "Anywhere" → both null |
| `Max drive hours` | `max_drive_hours` | Blank when Anywhere |
| `Allow remote parks` | `allow_remote` | Yes/No |
| `Allow parks that need permits` | `allow_permits` | Yes/No |
| `Top 3 parks` | `relevant` | Exactly 3 park names → `park_code`s |

Multi-select cells may use `, ` or `; ` between choices (Google Forms either way).

## Import

```bash
python scripts/import_form_labels.py path/to/form_export.csv
python scripts/import_form_labels.py path/to/form_export.csv --dry-run
```

Bad rows are skipped and printed. Existing profiles are never modified; only new
`split: "external"` profiles are appended. `python -m src.evaluate` reports the
external split on its own lines and keeps `all` = train + holdout only.

After validation, the importer runs `ParkRecommender.candidates()` on the
profile. Top-3 picks that pass stay in `relevant`. Picks that fail hard filters
move to `unreachable` as
`{"park_code": "...", "reasons": ["drive"|"remote"|"permit", ...]}`
(every reason that applies). If no pick passes, the row is skipped. Many
unreachable drive drops are a finding about the filters, not the ranking.
