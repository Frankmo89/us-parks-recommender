import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, test } from "vitest";

import {
  InvalidProfileError,
  recommend,
  type EngineData,
} from "./engine.js";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "../..");
const engineData: EngineData = JSON.parse(
  readFileSync(join(ROOT, "web/engine_data.json"), "utf8"),
);

const base = { biomes: ["desert"], tags: ["hiking"] };

describe("InvalidProfileError", () => {
  test("invalid difficulty raises typed error with field name", () => {
    expect(() =>
      recommend(engineData, { ...base, difficulty: "hard" }),
    ).toThrow(InvalidProfileError);
    try {
      recommend(engineData, { ...base, difficulty: "hard" });
    } catch (err) {
      expect(err).toBeInstanceOf(InvalidProfileError);
      const e = err as InvalidProfileError;
      expect(e.field).toBe("difficulty");
      expect(e.value).toBe("hard");
      expect(e.message).toContain("Invalid difficulty=");
      expect(e.message).toContain("challenging");
    }
  });

  test.each([
    [{ days_needed: "weekend" }, "days_needed"],
    [{ crowd_pref: "quiet" }, "crowd_pref"],
    [{ budget_tier: "cheap" }, "budget_tier"],
    [{ month: 0 }, "month"],
    [{ month: 13 }, "month"],
    [{ month: 1.5 }, "month"],
    [{ max_drive_hours: 0 }, "max_drive_hours"],
    [{ max_drive_hours: -2 }, "max_drive_hours"],
  ] as const)("rejects %j on field %s", (extra, field) => {
    expect(() => recommend(engineData, { ...base, ...extra })).toThrow(
      InvalidProfileError,
    );
    try {
      recommend(engineData, { ...base, ...extra });
    } catch (err) {
      expect((err as InvalidProfileError).field).toBe(field);
    }
  });

  test("unknown biome and tag do not raise", () => {
    const result = recommend(engineData, {
      biomes: ["atlantis", "desert"],
      tags: ["hoverboarding", "hiking"],
    });
    expect(result.n_returned).toBeGreaterThan(0);
  });

  test("hard filters never return violating parks", () => {
    const result = recommend(
      engineData,
      {
        biomes: ["desert"],
        tags: ["hiking"],
        allow_remote: false,
        allow_permits: false,
        origin_lat: 32.72,
        origin_lon: -117.16,
        max_drive_hours: 8,
        month: 11,
      },
      63,
    );
    for (const park of result.parks) {
      expect(park.facts.remote).toBe(false);
      expect(park.facts.permit_likely).toBe(false);
      expect(park.facts.drive_hours).not.toBeNull();
      expect(park.facts.drive_hours!).toBeLessThanOrEqual(8 + 1e-9);
    }
  });
});
