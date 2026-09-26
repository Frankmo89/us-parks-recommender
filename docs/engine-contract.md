# Ranking engine contract

This repository is the **ranking engine** for other apps (starting with
Nomaderia's quiz and AI concierge). The concierge is an LLM that calls this
engine as a **tool**. It must **never** invent a park ranking on its own.

This document is the API contract. It does not change scoring. A future
TypeScript (or other) port must match the Python behavior pinned in
`data/engine_fixtures.json`.

Current `engine_version`: **`0.1.0`** (same as `pyproject.toml`).

---

## 1. Input: trip profile

POST body / tool argument: a single JSON object. Unknown keys are ignored by
Python today; consumers should not send them.

### JSON Schema (logical)

| Field | Type | Allowed values | Default | Required | Notes |
|---|---|---|---|---|---|
| `biomes` | `string[]` | See biome vocab below | _(required)_ | **yes** | Multi-hot; empty `[]` is allowed (content match then relies on tags only). |
| `tags` | `string[]` | See tag vocab below | _(required)_ | **yes** | Multi-hot; empty `[]` allowed. Unknown tags are ignored in scoring. |
| `difficulty` | `string` | `easy`, `moderate`, `challenging` | `"easy"` | no | Ordinal closeness vs park difficulty. |
| `days_needed` | `string` | `1`, `2-3`, `4-7`, `7+` | `"2-3"` | no | Trip length bin. |
| `crowd_pref` | `string` | `low`, `medium`, `high` | `"medium"` | no | Parks busier than this pay a crowd penalty. |
| `budget_tier` | `string` | `low`, `mid`, `high` | `"mid"` | no | Travel cost to reach + stay (not entrance fee). |
| `month` | `integer` \| `null` | `1`–`12`, or omit/`null` | `null` | no | Soft season penalty vs park `best_months`. `null` → no season penalty. |
| `origin_lat` | `number` \| `null` | WGS84 latitude | `null` | no | With `origin_lon` + `max_drive_hours`, enables drive hard filter. |
| `origin_lon` | `number` \| `null` | WGS84 longitude | `null` | no | |
| `max_drive_hours` | `number` \| `null` | positive hours | `null` | no | Hard filter. Drive model: great-circle miles × 1.25 / 65 mph. |
| `allow_remote` | `boolean` | `true` / `false` | `true` | no | `false` drops parks with `remote=1` (AK, HI, ferry, etc.). |
| `allow_permits` | `boolean` | `true` / `false` | `true` | no | `false` drops parks with `permit_likely=1`. |

**Required** means the field must be present for a well-formed profile.
`biomes` and `tags` may be empty arrays. Ordinal / filter fields may be omitted;
the engine applies the defaults above.

### Validation: raise vs ignore

Before scoring, the engine validates enum and numeric constraints. Bad values
raise `InvalidProfileError` (Python) / `InvalidProfileError` (TypeScript) with
the field name, the bad value, and the allowed set — never a bare `KeyError`
or a silent `NaN` deep in the math.

**Null vs omitted:** For fields with a documented default (`difficulty`,
`days_needed`, `crowd_pref`, `budget_tier`), an explicit `null` / `None` is
equivalent to omitting the field — the default is applied, then validation
runs. Only a **non-null** value outside the enum (e.g. `"hard"`) raises.
`month` and `max_drive_hours` already treat `null` as a valid "no constraint"
value; that is unchanged.

| Field | On bad input |
|---|---|
| `difficulty`, `days_needed`, `crowd_pref`, `budget_tier` | **Raise** if non-null and not in the allowed enum list; `null` → default |
| `month` | **Raise** if not `null` and not an integer `1`–`12` |
| `max_drive_hours` | **Raise** if set and not a positive number |
| `biomes` entries outside biome vocab | **Silently ignored** in scoring (multi-hot miss) |
| `tags` entries outside tag vocab | **Silently ignored** in scoring (multi-hot miss) |
| Unknown top-level keys | **Ignored** by Python today; do not send them |

Example raise message:

```text
Invalid difficulty='hard'; allowed: ['easy', 'moderate', 'challenging']
```

The concierge must get enums / month / drive hours right when it sends a
concrete value. It may send unknown activity tags or biomes; the engine will
simply not match them. Sending `null` on an enum field is fine (uses default).

Optional top-level request fields (not part of the score input):

| Field | Type | Default | Notes |
|---|---|---|---|
| `k` | `integer` | `5` | Max parks to return after ranking. |

### Biome vocabulary

`alpine`, `canyon`, `cave`, `chaparral`, `coast`, `desert`, `forest`, `island`,
`prairie`, `rainforest`, `tundra`, `urban`, `volcano`, `wetland`

### Tag vocabulary (scored)

`4x4`, `archaeology`, `backpacking`, `beach`, `bears`, `biking`, `birding`,
`boardwalk`, `boat`, `camping`, `climbing`, `easy_walk`, `family`, `fishing`,
`geothermal`, `giant_trees`, `glacier`, `hiking`, `history`, `hot_springs`,
`kayak`, `paleontology`, `photography`, `sand`, `scenic_drive`, `snorkeling`,
`stargazing`, `sunrise`, `water`, `waterfalls`, `wilderness`, `wildflowers`,
`wildlife`, `winter`

Catalog rows may also carry annotation tokens (`low_crowd`, `permits`, `remote`,
or biome names used as tags elsewhere). Those are **not** in the scored tag
vocab; do not put them in the profile.

### How an LLM should fill the profile from a vague request

The concierge maps natural language → this schema. It does **not** pick parks
while filling the profile.

1. **Terrain (`biomes`)** — Only set when the user names a place type
   (desert, coast, mountains → `alpine`, rainforest, caves, …). If they only
   say activities, leave `biomes` as `[]`.
2. **Activities (`tags`)** — Map phrases to vocab tokens. Prefer 2–4 tags.
   Examples:
   - "easy hikes with my parents" → `difficulty: "easy"`,
     `tags: ["hiking", "family", "easy_walk"]`
   - "stargazing in the desert" → `biomes: ["desert"]`,
     `tags: ["stargazing", "hiking", "photography"]`
   - "wildlife and scenic drives, week-long" →
     `tags: ["wildlife", "scenic_drive"]`, `days_needed: "4-7"` or `"7+"`
3. **Difficulty** — "with kids / parents / beginners / boardwalks" → `easy`;
   "moderate trails" → `moderate`; "backpacking / strenuous / remote wilderness"
   → `challenging`.
4. **Days** — day trip → `"1"`; weekend → `"2-3"`; week → `"4-7"`; longer /
   expedition → `"7+"`.
5. **Crowds** — "quiet / avoid crowds / solitude" → `low`; otherwise leave
   default `medium` unless they say busy/popular is fine (`high`).
6. **Budget** — only set when stated; otherwise `mid`.
7. **Month** — parse "November", "next July", "fall" (pick a representative
   month). If timing is unknown, omit (`null`) so season does not penalize.
8. **Origin / drive** — only when the user gives a city or "within N hours of
   …". Resolve to lat/lon (named origins in `src/origins.py` are fine). If they
   say "fly anywhere", leave origin fields null.
9. **Remote / permits** — "no flights / lower 48 only" → `allow_remote: false`.
   "no timed entry / no permits" → `allow_permits: false`. Default both `true`.
10. **Do not invent constraints** the user did not imply. Prefer defaults over
    guesses that hard-filter the catalog to empty.

---

## 2. Output: ranked parks

Every successful response includes `engine_version` and a `parks` array
(possibly empty). Shape:

```json
{
  "engine_version": "0.1.0",
  "k": 5,
  "n_returned": 5,
  "empty": false,
  "tie_epsilon": 0.001,
  "tie_groups": [["gaar", "kova"]],
  "parks": [
    {
      "rank": 1,
      "score": 0.612345,
      "match_percent": 64,
      "tied_with_neighbors": false,
      "breakdown": {
        "content": 0.85,
        "days": 1.0,
        "difficulty": 1.0,
        "budget": 1.0,
        "crowd_penalty": 0.0,
        "month_penalty": 0.0,
        "weighted": {
          "content": 0.4675,
          "days": 0.18,
          "difficulty": 0.14,
          "budget": 0.08,
          "crowd_penalty": 0.0,
          "month_penalty": 0.0
        }
      },
      "facts": {
        "park_code": "deva",
        "name": "Death Valley National Park",
        "states": "CA,NV",
        "biomes": ["desert"],
        "tags": ["hiking", "stargazing", "..."],
        "difficulty": "easy",
        "days_needed": "2-3",
        "crowd": "low",
        "budget_tier": "low",
        "best_months": ["11", "12", "1", "2", "3"],
        "remote": false,
        "permit_likely": false,
        "nps_url": "https://www.nps.gov/deva/",
        "why": "desert · hiking · stargazing · 2-3 day trip · low crowds",
        "drive_hours": 4.2
      }
    }
  ]
}
```

### Score and breakdown

```
score = 0.55 * content
      + 0.18 * days
      + 0.14 * difficulty
      + 0.08 * budget
      − crowd_penalty
      − month_penalty
```

| Breakdown field | Meaning | Units |
|---|---|---|
| `content` | Cosine on biome + IDF-weighted tags | `[0, 1]` (fit) |
| `days` | Closeness on days bin | `[0, 1]` (fit) |
| `difficulty` | Closeness on difficulty | `[0, 1]` (fit) |
| `budget` | Closeness on budget | `[0, 1]` (fit) |
| `crowd_penalty` | `max(0, park_crowd − wanted) * 0.12` | ≥ 0 (subtracted) |
| `month_penalty` | `(month_distance / 6) * 0.35` | ≥ 0 (subtracted); 0 if `month` is null |
| `weighted.*` | Same parts in **score units** (weights applied; penalties negated) | Sum equals `score` |

`match_percent` is display-only: `round(score / (0.55+0.18+0.14+0.08) * 100)`,
clamped to 0–100. It does not change order.

`drive_hours` appears on each park when origin + `max_drive_hours` were set;
otherwise `null`. It is the same highway sketch used for the hard filter.

### Safe to show users vs internal

| Field | Audience |
|---|---|
| `facts.name`, `facts.park_code`, `facts.states`, `facts.nps_url` | **Safe** — primary identity |
| `facts.biomes`, `facts.tags`, `facts.difficulty`, `facts.days_needed`, `facts.crowd`, `facts.budget_tier`, `facts.best_months` | **Safe** — catalog attributes the user can understand (label plainly; note budget is travel cost, not entrance fee) |
| `facts.why` | **Safe** — short human blurb already used in the CLI/UI |
| `facts.drive_hours` | **Safe** when present — say it is an estimate, not Google Maps |
| `facts.remote`, `facts.permit_likely` | **Safe with care** — explain in plain language; `permit_likely` is a coarse snapshot and may be stale |
| `match_percent` | **Safe** — always caption as a fit score, not a probability |
| `rank`, `score` | **Internal / optional** — rank order is fine to imply ("top pick"); raw score is for debugging and the concierge's citations, not a user-facing grade |
| `breakdown` (fit floats + penalties + `weighted`) | **Internal to the tool, citable by the concierge** — use when explaining a pick; do not dump raw floats at users without translation |
| `engine_version`, `tie_epsilon`, `tie_groups`, `tied_with_neighbors` | **Internal** — for clients and the concierge ("these two are essentially tied") |
| `lat` / `lon` | Not required in the public response; catalog-only. Do not surface as "facts to quote" unless the product needs a map pin |

---

## 3. Guarantees

1. **Determinism** — Same profile JSON (same catalog + weights + `engine_version`)
   produces the same ordered list, scores, and breakdown. No randomness, no
   live NPS fetch, no time-of-day effects. Exact score ties are broken by
   `park_code` ascending — a portable, documented rule any client can
   replicate, not left to sort-algorithm internals.
2. **Hard filters** — A returned park always satisfies:
   - `allow_remote=false` ⇒ `remote=0`
   - `allow_permits=false` ⇒ `permit_likely=0`
   - origin + `max_drive_hours` set ⇒ `drive_hours ≤ max_drive_hours`
   Soft signals (month, crowds) never remove a park; they only change score.
3. **Ties** — Parks whose scores differ by at most `tie_epsilon` (**0.001**
   absolute) are reported in `tie_groups` (on the result attrs) with
   `tied_with_neighbors=True` on each member. Ranking among exact ties follows
   `park_code` ascending (see Determinism). Consumers and the concierge must
   treat tied parks as effectively equal (do not oversell tiny rank gaps).

Empty `parks` is a valid outcome when filters leave no candidates. Clients
should ask the user to loosen drive radius, remote/permit flags, or constraints.

---

## 4. Versioning

- Every output includes `engine_version` (semver string).
- **Breaking** (bump major, or minor before 1.0 per project policy — today bump
  the leading component of `0.x` and refresh fixtures):
  - Changing weights, hard-filter rules, drive model constants, IDF formula,
    vocab, or score formula so scores/order change for existing profiles
  - Renaming/removing profile fields or breakdown keys
  - Changing `tie_epsilon` semantics
  - Catalog edits that change which parks pass filters or their scored features
    for the same codes
- **Non-breaking**:
  - New optional profile fields with defaults that preserve old scores when omitted
  - New output fields that old clients can ignore
  - Docs-only / UI-only changes
  - Adding parks only if fixture regeneration and version bump are intentional
    product releases

Any breaking change regenerates `data/engine_fixtures.json` and records
before/after metrics in `CHANGELOG.md` per `CLAUDE.md`.

CI enforces this: the `engine-version` job runs
`scripts/check_engine_version_bump.py`, which compares
`data/engine_fixtures.json` (everything except its own `engine_version`
stamps and `notes`) against the PR's base branch. If the fixtures differ,
`pyproject.toml`'s version must differ too. The fixture stamps must equal the
`pyproject.toml` version.

---

## 5. How other apps consume the engine (planned)

1. **JSON export** — `python scripts/export_engine_data.py` writes
   `web/engine_data.json` with catalog rows, weight / drive constants,
   biome + tag vocab and IDF, ordinal maps, `engine_version`, and a
   `content_hash` of `data/parks.csv`. CI regenerates the file and fails on
   drift. Values come from the live Python engine, not a hand copy.
2. **TypeScript port** — `ts/` loads `web/engine_data.json` at runtime and
   exposes `recommend(data, profile, k)`. Pure functions; no framework.
   Vitest asserts all 26 fixture profiles against the Python snapshot.
3. **CI parity** — The `typescript` CI job runs `npm ci && npm test` in `ts/`.
   Fixture checks cover park order, scores, breakdown, drive hours, and
   `tie_groups`.

Python `ParkRecommender.recommend` remains the source of truth for regenerating
exports and fixtures.

---

## 6. Rules for the concierge tool

1. **Engine-only ranking** — Recommend only parks returned in this response.
   Never promote a park that was filtered out or absent from `parks`.
2. **Cite the breakdown** — When explaining a pick, name the parts that matter
   (terrain/activities, days, effort, budget, crowds, season) using the
   breakdown / weighted values, in plain language.
3. **Respect ties** — If `tie_groups` lists two codes, say they are a close call;
   do not invent a strong preference from a 0.0001 score gap.
4. **Live facts → NPS** — For closures, fees, alerts, weather, road status,
   timed-entry availability, or anything that changes day to day, say
   **check nps.gov** (use `facts.nps_url`). The engine catalog is not live.
5. **Drive times** — Quote as approximate highway estimates only.
6. **No trail picks** — Stay at park level (see below).

---

## 7. Out of scope (for now): trails

This engine ranks **parks**, not trails or itineraries inside a park.

Trail-level recommendations would need per-trail data the catalog does not
have, at least:

- Distance
- Elevation gain
- Difficulty (trail-grade, not park-level)
- Season / accessibility window per trail
- Optionally: permits, exposure, water, crowd level, trailhead location

Until that exists, the concierge may describe park-level tags (e.g. `easy_walk`)
but must not invent specific trail names or rankings as if the engine produced
them.
