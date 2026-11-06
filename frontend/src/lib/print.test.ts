import { describe, expect, test } from "vitest";
import type { Passage, Segment, StoredMessage } from "@/types/api";
import { chapterTargets, deepDiveTargets, distinctWords, firstVerseRef, layoutGenealogy, outline, splitGenerations } from "./print";

const passage = (reference: string, ns: number[]): Passage => ({
  reference, book: "Filipenses", book_id: 50, chapter: 4, verse_start: ns[0], verse_end: ns[ns.length - 1],
  requested_translation: "vfl", translation: "vfl", fallback_label: null,
  verses: ns.map((n) => ({ n, text: "t", cited: true })),
});
const msg = (role: "user" | "assistant", text: string | null, segments: Segment[] | null = null): StoredMessage => ({
  role, text, segments, status: "ok", created_at: "",
});

describe("outline", () => {
  test("questions are sections and markdown headings are subsections", () => {
    const items = outline([
      msg("user", "Interprete João 1"),
      msg("assistant", null, [{ type: "text", text: "Intro\n## 1. O Verbo (v. 1-18)\ntexto\n### Detalhe\n```\n## não é título\n```\n" }]),
      msg("user", "E o versículo 14?"),
      msg("assistant", null, [{ type: "text", text: "sem títulos" }]),
    ]);
    expect(items).toEqual([
      { id: "q1", title: "Interprete João 1", level: 1 },
      { id: "q1-h1", title: "1. O Verbo (v. 1-18)", level: 2 },
      { id: "q1-h2", title: "Detalhe", level: 2 },
      { id: "q2", title: "E o versículo 14?", level: 1 },
    ]);
  });
});

describe("deep dive", () => {
  test("dedupes passages, caps at max, uses first verse for long passages", () => {
    const segs: Segment[] = [
      { type: "verse", marker: "m", passage: passage("Fp 4:6-7", [6, 7]) },
      { type: "verse", marker: "m", passage: passage("Fp 4:6-7", [6, 7]) },
      { type: "verse", marker: "m", passage: passage("Fp 4:1-9", [1, 2, 3, 4, 5, 6, 7, 8, 9]) },
      { type: "text", text: "x" },
    ];
    expect(deepDiveTargets(segs, 6)).toEqual([
      { reference: "Fp 4:6-7", compareRef: "Fp 4:6-7", firstVerse: "Fp 4:6" },
      { reference: "Fp 4:1-9", compareRef: "Fp 4:1", firstVerse: "Fp 4:1" },
    ]);
    expect(deepDiveTargets(segs, 1)).toHaveLength(1);
    expect(firstVerseRef(passage("Fp 4:13", [13]))).toBe("Fp 4:13");
  });

  test("chapter targets come from timeline, map and chiasm", () => {
    const segs: Segment[] = [
      { type: "timeline", marker: "m", reference: "Jo 1", book: "João", sections: [] },
      { type: "map", marker: "m", reference: "Jo 1", places: [] },
      { type: "chiasm", marker: "m", reference: "Sl 2", book: "Salmos", parts: [] },
    ];
    expect(chapterTargets(segs, 3)).toEqual(["Jo 1", "Sl 2"]);
  });
});

describe("distinctWords", () => {
  test("marks words only one translation uses", () => {
    const d = distinctWords({ vfl: "Não fiquem preocupados com nada", acf: "Não estejais inquietos por coisa alguma" });
    expect(d.vfl.has("preocupados")).toBe(true);
    expect(d.vfl.has("não")).toBe(false);
    expect(d.acf.has("inquietos")).toBe(true);
  });
});

describe("genealogy layout", () => {
  const people = ["avo", "pai", "mae", "filho", "filha"].map((id) => ({ id, name: id, name_is_pt: true, brief: null, in_text: true }));
  const links = [
    { from: "avo", to: "pai", kind: "pai" as const },
    { from: "pai", to: "filho", kind: "pai" as const },
    { from: "mae", to: "filho", kind: "pai" as const },
    { from: "pai", to: "filha", kind: "pai" as const },
    { from: "mae", to: "pai", kind: "conjuge" as const },
  ];

  test("parents sit one generation above children and spouses share a row", () => {
    const nodes = layoutGenealogy(people, links, 720);
    const gen = Object.fromEntries(nodes.map((n) => [n.id, n.generation]));
    expect(gen).toEqual({ avo: 0, pai: 1, mae: 1, filho: 2, filha: 2 });
    const x = Object.fromEntries(nodes.map((n) => [n.id, n.x]));
    expect(new Set(nodes.map((n) => `${n.x},${n.y}`)).size).toBe(5);
    expect(Math.min(x.filho, x.filha)).toBeGreaterThanOrEqual(0);
  });

  test("long chains split into chunks that repeat the boundary generation", () => {
    const chain = Array.from({ length: 30 }, (_, i) => ({ id: `p${i}`, name: `p${i}`, name_is_pt: true, brief: null, in_text: true }));
    const chainLinks = chain.slice(1).map((p, i) => ({ from: `p${i}`, to: p.id, kind: "pai" as const }));
    const chunks = splitGenerations(layoutGenealogy(chain, chainLinks, 720), 12);
    expect(chunks.map((c) => [c[0].generation, c[c.length - 1].generation])).toEqual([[0, 12], [12, 24], [24, 29]]);
  });
});

describe("profileCandidates", () => {
  test("keeps common nouns and verbs, drops names and particles", async () => {
    const { profileCandidates } = await import("./print");
    const words = [
      { strong: "G3367", morphology: "A-ASN-N" },
      { strong: "G3309", morphology: "V-PAM-2P" },
      { strong: "G4335", morphology: "N-DSF" },
      { strong: "G2424", morphology: "N-PRI" },
      { strong: "H3068G", morphology: "HNpt" },
      { strong: "H7462B", morphology: "HVqrmsc/Sp1bs" },
      { strong: "H4325", morphology: "HNcmpa" },
      { strong: "H3808", morphology: "HTn" },
    ];
    expect(profileCandidates(words, 10)).toEqual(["G3309", "G4335", "H7462B", "H4325"]);
    expect(profileCandidates(words, 2)).toEqual(["G3309", "G4335"]);
  });
});

describe("crowded generations", () => {
  test("a generation with many people wraps into lines that never overlap", async () => {
    const { layoutGenealogy } = await import("./print");
    const kids = Array.from({ length: 14 }, (_, i) => ({ id: `k${i}`, name: `Filho ${i}`, name_is_pt: true, brief: null, in_text: true }));
    const parent = { id: "p", name: "Pai", name_is_pt: true, brief: null, in_text: true };
    const nodes = layoutGenealogy([parent, ...kids], kids.map((k) => ({ from: "p", to: k.id, kind: "pai" as const })), 720);
    const children = nodes.filter((n) => n.id !== "p");
    const lines = new Set(children.map((n) => n.y));
    expect(lines.size).toBe(3);
    for (const y of lines) {
      const xs = children.filter((n) => n.y === y).map((n) => n.x).sort((a, b) => a - b);
      xs.slice(1).forEach((x, i) => expect(x - xs[i]).toBeGreaterThanOrEqual(110));
    }
    expect(Math.min(...children.map((n) => n.y))).toBeGreaterThan(nodes.find((n) => n.id === "p")!.y);
  });
});
