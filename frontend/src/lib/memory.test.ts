import { describe, expect, test } from "vitest";
import { sortMemories, topicTitle } from "./memory";

describe("memory display", () => {
  test("topicTitle turns slug into readable title", () => {
    expect(topicTitle("situacao-financeira")).toBe("Situacao financeira");
    expect(topicTitle("oracao")).toBe("Oracao");
  });

  test("sortMemories puts most recent first", () => {
    const items = [
      { topic: "a", content: "", updated_at: "2026-11-01T10:00:00Z" },
      { topic: "b", content: "", updated_at: "2026-11-05T10:00:00Z" },
    ];
    expect(sortMemories(items).map((i) => i.topic)).toEqual(["b", "a"]);
  });
});
