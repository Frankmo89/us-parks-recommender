/**
 * Park access (road / boat / flight): drive filter and travel labels.
 * Mirrors tests/test_access.py on the Python side.
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, test } from "vitest";

import { accessLabel, recommend, type EngineData } from "./engine.js";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "../..");
const engineData: EngineData = JSON.parse(
  readFileSync(join(ROOT, "web/engine_data.json"), "utf8"),
);
const LA = { origin_lat: 34.05, origin_lon: -118.24 };
const ALL = engineData.catalog.length;
const FLIGHT = ["hale", "havo", "npsa", "viis", "gaar", "glba", "katm", "kova", "lacl"];
const BOAT = ["chis", "drto", "isro"];

function byCode(result: ReturnType<typeof recommend>) {
  return new Map(result.parks.map((p) => [p.facts.park_code, p]));
}

describe("park access", () => {
  test("catalog access values match the approved list", () => {
    const flight = engineData.catalog.filter((p) => p.access === "flight").map((p) => p.park_code);
    const boat = engineData.catalog.filter((p) => p.access === "boat").map((p) => p.park_code);
    expect(flight.sort()).toEqual([...FLIGHT].sort());
    expect(boat.sort()).toEqual([...BOAT].sort());
  });

  test("LA + 8h drive limit keeps chis with a drive + boat label", () => {
    const got = recommend(
      engineData,
      { biomes: ["island", "coast"], tags: ["kayaking", "wildlife"], ...LA, max_drive_hours: 8 },
      5,
    );
    const chis = byCode(got).get("chis");
    expect(chis).toBeDefined();
    const hours = chis!.facts.drive_hours!;
    expect(hours).toBeGreaterThan(0);
    expect(hours).toBeLessThanOrEqual(8);
    expect(chis!.facts.access).toBe("boat");
    expect(chis!.facts.why).toContain(`~${hours.toFixed(1)}h drive + boat`);
  });

  test("havo is excluded with max_drive_hours=60 from LA", () => {
    const got = recommend(
      engineData,
      { biomes: ["volcano"], tags: ["hiking"], ...LA, max_drive_hours: 60 },
      ALL,
    );
    expect(byCode(got).has("havo")).toBe(false);
  });

  test("no flight park passes any drive limit; boat parks can", () => {
    const got = recommend(engineData, { biomes: [], tags: [], ...LA, max_drive_hours: 10000 }, ALL);
    const codes = byCode(got);
    for (const code of FLIGHT) expect(codes.has(code), code).toBe(false);
    for (const code of BOAT) expect(codes.has(code), code).toBe(true);
    expect(got.n_returned).toBe(ALL - FLIGHT.length);
  });

  test("no drive limit: havo stays and says flight needed", () => {
    const got = recommend(engineData, { biomes: ["volcano"], tags: ["hiking"] }, ALL);
    const havo = byCode(got).get("havo");
    expect(havo).toBeDefined();
    expect(havo!.facts.drive_hours).toBeNull();
    expect(havo!.facts.why).toContain("flight needed");
  });

  test("no drive limit: chis says boat needed", () => {
    const got = recommend(engineData, { biomes: ["island", "coast"], tags: ["kayaking"] }, ALL);
    const chis = byCode(got).get("chis");
    expect(chis!.facts.why).toContain("boat needed");
    expect(chis!.facts.why).not.toContain("h drive");
  });

  test("accessLabel cases", () => {
    expect(accessLabel("road", 2.345)).toBe("~2.3h drive");
    expect(accessLabel("boat", 1.3)).toBe("~1.3h drive + boat");
    expect(accessLabel("boat", null)).toBe("boat needed");
    expect(accessLabel("flight", null)).toBe("flight needed");
    expect(accessLabel("road", null)).toBe("");
  });
});
