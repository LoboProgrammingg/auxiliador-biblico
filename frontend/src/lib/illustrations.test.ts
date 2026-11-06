import { describe, expect, test } from "vitest";
import { chiasmRows } from "./illustrations";

describe("chiasmRows", () => {
  test("depth mirrors and pairs connect first with last", () => {
    const rows = chiasmRows(["A", "B", "C", "B'", "A'"]);
    expect(rows.map((r) => r.depth)).toEqual([0, 1, 2, 1, 0]);
    expect(rows.map((r) => r.pair)).toEqual([4, 3, null, 1, 0]);
  });

  test("even count has no center", () => {
    expect(chiasmRows(["A", "B", "B'", "A'"]).map((r) => r.pair)).toEqual([3, 2, 1, 0]);
  });
});
