// Phase 0 acceptance gate (frontend half): TypeScript enums must match the canonical
// registry exactly — same names, same members, same order.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { ENUM_REGISTRY } from "./enums.js";

const here = dirname(fileURLToPath(import.meta.url));
const canonicalPath = resolve(here, "../../../docs/schemas/enums.json");
const canonical: Record<string, string[]> = JSON.parse(readFileSync(canonicalPath, "utf-8")).enums;

describe("enum parity with docs/schemas/enums.json", () => {
  it("has the same enum group names", () => {
    expect(new Set(Object.keys(ENUM_REGISTRY))).toEqual(new Set(Object.keys(canonical)));
  });

  it("matches members and order for every enum", () => {
    const mismatches: string[] = [];
    for (const [name, members] of Object.entries(ENUM_REGISTRY)) {
      const expected = canonical[name];
      if (JSON.stringify([...members]) !== JSON.stringify(expected)) {
        mismatches.push(`${name}: ts=${JSON.stringify(members)} canonical=${JSON.stringify(expected)}`);
      }
    }
    expect(mismatches).toEqual([]);
  });

  it("has no duplicate values within an enum", () => {
    for (const [name, members] of Object.entries(ENUM_REGISTRY)) {
      expect(new Set(members).size, `duplicates in ${name}`).toBe(members.length);
    }
  });
});
