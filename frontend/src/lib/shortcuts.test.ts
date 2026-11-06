import { describe, expect, test } from "vitest";
import { matchShortcut } from "./shortcuts";

const key = (k: string, mods: Partial<{ ctrlKey: boolean; metaKey: boolean; altKey: boolean; shiftKey: boolean }> = {}, tag = "BODY") => ({
  key: k, ctrlKey: false, metaKey: false, altKey: false, shiftKey: false, ...mods, target: { tagName: tag, isContentEditable: false },
});

describe("matchShortcut", () => {
  test("maps the documented shortcuts", () => {
    expect(matchShortcut(key("k", { ctrlKey: true }))).toBe("nova");
    expect(matchShortcut(key("K", { metaKey: true }))).toBe("nova");
    expect(matchShortcut(key("j", { ctrlKey: true }))).toBe("buscar");
    expect(matchShortcut(key("f", { altKey: true }))).toBe("foco");
    expect(matchShortcut(key("/"))).toBe("compor");
  });

  test("slash while typing is just a character", () => {
    expect(matchShortcut(key("/", {}, "TEXTAREA"))).toBeNull();
    expect(matchShortcut(key("/", {}, "INPUT"))).toBeNull();
    expect(matchShortcut(key("k", { ctrlKey: true }, "TEXTAREA"))).toBe("nova");
  });

  test("ignores everything else", () => {
    expect(matchShortcut(key("k"))).toBeNull();
    expect(matchShortcut(key("f", { ctrlKey: true }))).toBeNull();
  });
});
