import { describe, expect, test } from "vitest";
import { NO_MODES, effortFor, placeholderFor, requestModes } from "./modes";

describe("modes", () => {
  test("modes are independent and all can be on together", () => {
    expect(requestModes({ plan: true, video: true, complex: true })).toEqual({ plan: true, video: true, complex: true });
    expect(requestModes(NO_MODES)).toEqual({ plan: false, video: false, complex: false });
  });

  test("complex raises effort to extra high and video to high, never lowering a higher choice", () => {
    expect(effortFor("medium", NO_MODES)).toBe("medium");
    expect(effortFor("medium", { ...NO_MODES, video: true })).toBe("high");
    expect(effortFor("medium", { ...NO_MODES, complex: true })).toBe("xhigh");
    expect(effortFor("xhigh", { ...NO_MODES, video: true })).toBe("xhigh");
    expect(effortFor("high", { plan: true, video: true, complex: true })).toBe("xhigh");
  });

  test("placeholder follows the active modes", () => {
    expect(placeholderFor(NO_MODES)).toBe("Escreva o que está no seu coração...");
    expect(placeholderFor({ ...NO_MODES, video: true })).toMatch(/vídeo/i);
    expect(placeholderFor({ ...NO_MODES, plan: true })).toMatch(/estudar/i);
    expect(placeholderFor({ ...NO_MODES, complex: true })).toMatch(/destrinch/i);
  });
});
