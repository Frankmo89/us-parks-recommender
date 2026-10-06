/**
 * Month-aware crowd. Mirrors tests/test_peak_months.py on the Python side.
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, test } from "vitest";

import { effectiveCrowdRank, recommend, type EngineData, type TripProfile } from "./engine.js";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "../..");
const engineData: EngineData = JSON.parse(
  readFileSync(join(ROOT, "web/engine_data.json"), "utf8"),
);

const PHOENIX = { origin_lat: 33.45, origin_lon: -112.07, max_drive_hours: 8 };
const LOS_ANGELES = { origin_lat: 34.05, origin_lon: -118.24, max_drive_hours: 8 };
const YOSE_TRIP: TripProfile = {
  biomes: ["alpine", "forest"],
  tags: ["hiking", "waterfalls", "photography"],
  difficulty: "moderate",
  days_needed: "2-3",
  crowd_pref: "low",
};
const CANYON_TRIP: TripProfile = {
  biomes: ["canyon", "desert"],
  tags: ["hiking", "photography"],
  difficulty: "moderate",
  days_needed: "2-3",
  crowd_pref: "low",
};

const ranked = (profile: TripProfile) => recommend(engineData, profile, 63).parks;
const park = (profile: TripProfile, code: string) =>
  ranked(profile).find((p) => p.facts.park_code === code)!;

describe("month-aware crowd", () => {
  test.each([
    ["high", null, 2],
    ["high", 7, 2],
    ["high", 1, 1],
    ["medium", 1, 0],
    ["low", 1, 0],
  ] as const)("crowd %s in month %s counts as rank %d", (crowd, month, expected) => {
    const rec = { crowd, peak_months: ["6", "7", "8", "9", "10"] };
    expect(effectiveCrowdRank(rec, month, engineData)).toBe(expected);
  });

  test("export carries peak_months; Yosemite peaks June-October", () => {
    const yose = engineData.catalog.find((p) => p.park_code === "yose")!;
    expect(yose.peak_months).toEqual(["6", "7", "8", "9", "10"]);
    expect(engineData.catalog.every((p) => p.peak_months.length > 0)).toBe(true);
  });

  test("no month keeps the catalog crowd penalty", () => {
    expect(park(YOSE_TRIP, "yose").breakdown.crowd_penalty).toBeCloseTo(0.24, 6);
  });

  test("Yosemite: January 0.12, July 0.24 crowd penalty", () => {
    expect(park({ ...YOSE_TRIP, month: 1 }, "yose").breakdown.crowd_penalty).toBeCloseTo(0.12, 6);
    expect(park({ ...YOSE_TRIP, month: 7 }, "yose").breakdown.crowd_penalty).toBeCloseTo(0.24, 6);
  });

  test("crossover: climbing trip from LA in April puts Yosemite ahead of Pinnacles", () => {
    const top = ranked({
      biomes: ["alpine", "forest"],
      tags: ["climbing", "hiking"],
      difficulty: "moderate",
      days_needed: "2-3",
      crowd_pref: "low",
      month: 4,
      ...LOS_ANGELES,
    }).slice(0, 2);
    expect(top.map((p) => p.facts.park_code)).toEqual(["yose", "pinn"]);
  });

  test.each([3, 11])("crossover: Zion in month %d beats Death Valley from Phoenix", (month) => {
    const top = ranked({ ...CANYON_TRIP, month, ...PHOENIX }).slice(0, 2);
    expect(top.map((p) => p.facts.park_code)).toEqual(["zion", "deva"]);
  });

  test("Zion in a peak month keeps the full crowd penalty", () => {
    expect(park({ ...CANYON_TRIP, month: 5 }, "zion").breakdown.crowd_penalty).toBeCloseTo(0.24, 6);
  });
});
