import { describe, expect, test } from "vitest";
import { DEFAULT_OPTIONS, EFFORTS, MODELS, parseOptions } from "./chatOptions";

describe("chat options", () => {
  test("only Sonnet 5.5 and Opus 5.5, and medium, high and extra high", () => {
    expect(MODELS.map((m) => m.id)).toEqual(["claude-sonnet-5-5", "claude-opus-5-5"]);
    expect(EFFORTS.map((e) => e.id)).toEqual(["medium", "high", "xhigh"]);
  });

  test("restores a saved choice", () => {
    const saved = JSON.stringify({ model: "claude-opus-5-5", effort: "xhigh", brief: true });
    expect(parseOptions(saved)).toEqual({ model: "claude-opus-5-5", effort: "xhigh", brief: true });
  });

  test("falls back to defaults on missing, broken or unknown values", () => {
    expect(parseOptions(null)).toEqual(DEFAULT_OPTIONS);
    expect(parseOptions("{oops")).toEqual(DEFAULT_OPTIONS);
    expect(parseOptions(JSON.stringify({ model: "claude-haiku-5-5", effort: "max", brief: "sim" }))).toEqual(
      DEFAULT_OPTIONS,
    );
  });
});
