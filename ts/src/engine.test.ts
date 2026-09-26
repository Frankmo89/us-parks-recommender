/**
 * Parity: TypeScript recommend() vs pinned Python output in
 * data/engine_fixtures.json. Do not edit the fixture to make this pass.
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, test } from "vitest";

import {
  recommend,
  type EngineData,
  type TripProfile,
} from "./engine.js";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "../..");
const TOL = 1e-6;

type FixturePark = {
  rank: number;
  score: number;
  match_percent: number;
  tied_with_neighbors: boolean;
  breakdown: {
    content: number;
    days: number;
    difficulty: number;
    budget: number;
    crowd_penalty: number;
    month_penalty: number;
    weighted: {
      content: number;
      days: number;
      difficulty: number;
      budget: number;
      crowd_penalty: number;
      month_penalty: number;
    };
  };
  facts: {
    park_code: string;
    drive_hours: number | null;
  };
};

type FixtureProfile = {
  id: string;
  profile: TripProfile;
  output: {
    k: number;
    n_returned: number;
    empty: boolean;
    tie_groups: string[][];
    parks: FixturePark[];
  };
};

type FixtureBundle = {
  k: number;
  profiles: FixtureProfile[];
};

const engineData: EngineData = JSON.parse(
  readFileSync(join(ROOT, "web/engine_data.json"), "utf8"),
);
const fixtures: FixtureBundle = JSON.parse(
  readFileSync(join(ROOT, "data/engine_fixtures.json"), "utf8"),
);

function nearly(a: number, b: number, tol = TOL): boolean {
  return Math.abs(a - b) <= tol;
}

describe("TS engine parity with Python fixtures", () => {
  test("fixture bundle has 25 profiles", () => {
    expect(fixtures.profiles).toHaveLength(25);
  });

  for (const item of fixtures.profiles) {
    test(`profile ${item.id}`, () => {
      const got = recommend(engineData, item.profile, item.output.k ?? fixtures.k);
      const expected = item.output;

      expect(got.n_returned).toBe(expected.n_returned);
      expect(got.empty).toBe(expected.empty);
      expect(got.tie_groups).toEqual(expected.tie_groups);

      const gotCodes = got.parks.map((p) => p.facts.park_code);
      const expCodes = expected.parks.map((p) => p.facts.park_code);
      expect(gotCodes).toEqual(expCodes);

      for (let i = 0; i < expected.parks.length; i++) {
        const g = got.parks[i]!;
        const e = expected.parks[i]!;
        expect(g.rank).toBe(e.rank);
        expect(g.match_percent).toBe(e.match_percent);
        expect(g.tied_with_neighbors).toBe(e.tied_with_neighbors);
        expect(nearly(g.score, e.score), `score ${g.facts.park_code}`).toBe(
          true,
        );

        for (const key of [
          "content",
          "days",
          "difficulty",
          "budget",
          "crowd_penalty",
          "month_penalty",
        ] as const) {
          expect(
            nearly(g.breakdown[key], e.breakdown[key]),
            `breakdown.${key} ${g.facts.park_code}`,
          ).toBe(true);
          expect(
            nearly(g.breakdown.weighted[key], e.breakdown.weighted[key]),
            `weighted.${key} ${g.facts.park_code}`,
          ).toBe(true);
        }

        if (e.facts.drive_hours === null) {
          expect(g.facts.drive_hours).toBeNull();
        } else {
          expect(g.facts.drive_hours).not.toBeNull();
          // Fixtures store drive_hours rounded to 4 decimals (generator artifact);
          // engine returns full float. Compare at that stored precision.
          const rounded = Math.round(g.facts.drive_hours! * 1e4) / 1e4;
          expect(
            nearly(rounded, e.facts.drive_hours),
            `drive_hours ${g.facts.park_code} ts=${g.facts.drive_hours} fixture=${e.facts.drive_hours}`,
          ).toBe(true);
        }
      }
    });
  }
});
