import { describe, expect, test } from "vitest";
import type { Prayer } from "@/types/api";
import { groupPrayers } from "./diary";

const p = (id: string, status: "aberto" | "respondido", created: string, answered: string | null = null): Prayer => ({
  id, title: id, details: null, status, answer_note: null, created_at: created, answered_at: answered,
});

describe("groupPrayers", () => {
  test("open first (newest first), answered by answer date (newest first)", () => {
    const g = groupPrayers([
      p("a", "aberto", "2026-11-01T10:00:00Z"),
      p("b", "respondido", "2026-10-01T10:00:00Z", "2026-11-02T10:00:00Z"),
      p("c", "aberto", "2026-11-05T10:00:00Z"),
      p("d", "respondido", "2026-10-03T10:00:00Z", "2026-11-04T10:00:00Z"),
    ]);
    expect(g.open.map((x) => x.id)).toEqual(["c", "a"]);
    expect(g.answered.map((x) => x.id)).toEqual(["d", "b"]);
  });
});
