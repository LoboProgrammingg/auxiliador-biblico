import { describe, expect, test } from "vitest";
import type { Passage, Segment } from "@/types/api";
import { applyEvent, toBlocks } from "./segments";

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
