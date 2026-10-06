/**
 * Optional `states` filter. Mirrors tests/test_states.py on the Python side.
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, test } from "vitest";

import { InvalidProfileError, recommend, type EngineData, type TripProfile } from "./engine.js";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "../..");
const engineData: EngineData = JSON.parse(
  readFileSync(join(ROOT, "web/engine_data.json"), "utf8"),
);

const UTAH_CANYONS: TripProfile = {
  biomes: ["canyon", "desert"],
  tags: ["hiking", "photography", "stargazing"],
  difficulty: "moderate",
  days_needed: "4-7",
  month: 10,
};

const codes = (profile: TripProfile, k = 5) =>
  recommend(engineData, profile, k).parks.map((p) => p.facts.park_code);

describe("states filter", () => {
  test("exports 56 state codes", () => {
    expect(engineData.vocab.states).toHaveLength(56);
  });

  test("Utah canyons with states [UT] returns only Utah parks", () => {
    expect(new Set(codes({ ...UTAH_CANYONS, states: ["UT"] }))).toEqual(
      new Set(["arch", "cany", "brca", "zion", "care"]),
    );
  });

  test("null and [] mean no filter", () => {
    const base = codes(UTAH_CANYONS);
    expect(base).toEqual(["deva", "blca", "care", "bibe", "cany"]);
    expect(codes({ ...UTAH_CANYONS, states: null })).toEqual(base);
    expect(codes({ ...UTAH_CANYONS, states: [] })).toEqual(base);
  });

  test("codes are trimmed, uppercased and de-duplicated", () => {
    expect(codes({ ...UTAH_CANYONS, states: [" ut", "UT"] })).toEqual(
      codes({ ...UTAH_CANYONS, states: ["UT"] }),
    );
  });

  test("multi-state list matches any listed state", () => {
    const got = codes({ biomes: ["alpine", "forest"], tags: ["hiking"], states: ["WA", "OR"] }, 10);
    expect(new Set(got)).toEqual(new Set(["mora", "noca", "olym", "crla"]));
  });

  test("valid code without parks returns empty", () => {
    const got = recommend(engineData, { ...UTAH_CANYONS, states: ["DE"] });
    expect(got.empty).toBe(true);
  });

  test.each([[["XX"]], [["Utah"]], [[7]], ["UT"]])(
    "invalid states %j raise InvalidProfileError on field states",
    (bad) => {
      try {
        recommend(engineData, { ...UTAH_CANYONS, states: bad as unknown as string[] });
        throw new Error("expected InvalidProfileError");
      } catch (err) {
        expect(err).toBeInstanceOf(InvalidProfileError);
        expect((err as InvalidProfileError).field).toBe("states");
      }
    },
  );
});
