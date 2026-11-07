import { describe, expect, test } from "vitest";
import type { Passage, Segment } from "@/types/api";
import { applyEvent, formatTokens, needsReattach, toBlocks } from "./segments";

const passage: Passage = {
  reference: "Fp 4:6",
  book: "Filipenses",
  book_id: 50,
  chapter: 4,
  verse_start: 6,
  verse_end: 6,
  requested_translation: "vfl",
  translation: "vfl",
  fallback_label: null,
  verses: [{ n: 6, text: "texto", cited: true }],
};

describe("applyEvent", () => {
  test("concatenates text and inserts verse between texts", () => {
    let s: Segment[] = [];
    s = applyEvent(s, { event: "text", data: { text: "Leia " } });
    s = applyEvent(s, { event: "text", data: { text: "isto:\n" } });
    s = applyEvent(s, { event: "verse", data: { marker: "[[Fp 4:6]]", passage } });
    s = applyEvent(s, { event: "text", data: { text: "\nOre." } });
    expect(s.map((x) => x.type)).toEqual(["text", "verse", "text"]);
    expect(s[0]).toEqual({ type: "text", text: "Leia isto:\n" });
  });

  test("turns invalid_reference into warning segment and issues into issue segments", () => {
    let s: Segment[] = applyEvent([], { event: "invalid_reference", data: { marker: "[[Jo 3:99]]" } });
    s = applyEvent(s, { event: "issues", data: { items: [{ kind: "citacao_nao_confere", excerpt: "x" }] } });
    expect(s).toEqual([
      { type: "invalid_reference", marker: "[[Jo 3:99]]" },
      { type: "issue", kind: "citacao_nao_confere", excerpt: "x" },
    ]);
  });

  test("ignores status events", () => {
    expect(applyEvent([], { event: "status", data: { label: "x" } })).toEqual([]);
  });
});

describe("toBlocks", () => {
  test("verse alone on its line becomes a card; inline verse becomes a link in markdown", () => {
    const segments: Segment[] = [
      { type: "text", text: "Jesus disse a Marta em " },
      { type: "verse", marker: "[[Lc 10:41]]", passage: { ...passage, reference: "Lc 10:41" } },
      { type: "text", text: " algo forte.\n\n" },
      { type: "verse", marker: "[[Fp 4:6]]", passage },
      { type: "text", text: "\nNa prática..." },
    ];
    const blocks = toBlocks(segments);
    expect(blocks.map((b) => b.kind)).toEqual(["markdown", "card", "markdown"]);
    expect(blocks[0]).toMatchObject({ kind: "markdown", markdown: "Jesus disse a Marta em [Lc 10:41](#v1) algo forte.\n\n" });
    expect(blocks[1]).toMatchObject({ kind: "card", index: 3 });
  });

  test("invalid reference becomes inline warning link", () => {
    const blocks = toBlocks([
      { type: "text", text: "Veja " },
      { type: "invalid_reference", marker: "[[Jo 3:99]]" },
      { type: "text", text: " hoje." },
    ]);
    expect(blocks).toEqual([{ kind: "markdown", markdown: "Veja [⚠ referência não encontrada](#x1) hoje." }]);
  });
});

describe("visual blocks", () => {
  test("timeline and map events become block segments rendered as their own cards", () => {
    let s: Segment[] = applyEvent([], { event: "text", data: { text: "Estrutura:\n" } });
    s = applyEvent(s, {
      event: "timeline",
      data: { marker: "[[linha:Jo 1|1-18=A]]", reference: "Jo 1", book: "João", sections: [{ start: 1, end: 18, title: "A" }] },
    });
    s = applyEvent(s, { event: "map", data: { marker: "[[mapa:Jo 1]]", reference: "Jo 1", places: [] } });
    s = applyEvent(s, { event: "text", data: { text: "\nCena 1" } });
    expect(toBlocks(s).map((b) => b.kind)).toEqual(["markdown", "timeline", "map", "markdown"]);
  });
});

describe("robustness", () => {
  test("error event becomes a stored-like error segment", () => {
    const out = applyEvent([], { event: "error", data: { code: "tempo_esgotado", message: "Demorou." } });
    expect(out).toEqual([{ type: "error", code: "tempo_esgotado", message: "Demorou." }]);
  });

  test("needsReattach only when last assistant message is still generating", () => {
    const base = { text: null, segments: [], created_at: "" };
    expect(needsReattach([{ ...base, role: "user", status: "ok" }, { ...base, role: "assistant", status: "gerando" }])).toBe(true);
    expect(needsReattach([{ ...base, role: "assistant", status: "ok" }])).toBe(false);
    expect(needsReattach([{ ...base, role: "assistant", status: "interrompida" }])).toBe(false);
    expect(needsReattach([])).toBe(false);
  });
});

describe("token usage", () => {
  test("usage event becomes a usage segment", () => {
    const data = { total: 48200, output: 1200, cached: 40000, average: 41000, questions: 23 };
    expect(applyEvent([], { event: "usage", data })).toEqual([{ type: "usage", ...data }]);
  });

  test("formats token counts in Portuguese", () => {
    expect(formatTokens(850)).toBe("850");
    expect(formatTokens(48230)).toBe("48,2 mil");
    expect(formatTokens(1250000)).toBe("1,3 mi");
  });
});
