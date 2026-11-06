import type { Passage, Segment, StoredMessage } from "@/types/api";

export interface OutlineItem {
  id: string;
  title: string;
  level: 1 | 2;
}

const HEADING = /^(#{1,3})\s+(.+?)\s*#*\s*$/;

/** Títulos de markdown (h1–h3) fora de blocos de código, com a linha (1-based) em que aparecem. */
export function headingLines(markdown: string): { line: number; title: string; level: number }[] {
  const found: { line: number; title: string; level: number }[] = [];
  let fenced = false;
  markdown.split("\n").forEach((text, i) => {
    if (text.trim().startsWith("```")) fenced = !fenced;
    else if (!fenced) {
      const match = HEADING.exec(text);
      if (match) found.push({ line: i + 1, title: match[2], level: match[1].length });
    }
  });
  return found;
}

export function markdownHeadings(markdown: string): { title: string; level: number }[] {
  return headingLines(markdown).map(({ title, level }) => ({ title, level }));
}

const answerText = (segments: Segment[] | null) =>
  (segments ?? []).map((s) => (s.type === "text" ? s.text : "\n")).join("");

export function outline(messages: StoredMessage[]): OutlineItem[] {
  const items: OutlineItem[] = [];
  let question = 0;
  for (const m of messages) {
    if (m.role === "user") {
      question += 1;
      const title = (m.text ?? "").trim();
      items.push({ id: `q${question}`, title: title.length > 90 ? `${title.slice(0, 87)}…` : title, level: 1 });
    } else if (question > 0) {
      markdownHeadings(answerText(m.segments)).forEach(({ title, level }, k) => {
        if (level <= 2) items.push({ id: `q${question}-h${k + 1}`, title, level: 2 });
      });
    }
  }
  return items;
}

export interface DeepDiveTarget {
  reference: string;
  compareRef: string;
  firstVerse: string;
}

export function firstVerseRef(p: Passage): string {
  return `${p.reference.split(":")[0]}:${p.verses[0]?.n ?? p.verse_start ?? 1}`;
}

const MAX_COMPARE_VERSES = 4;

export function deepDiveTargets(segments: Segment[], max: number): DeepDiveTarget[] {
  const seen = new Set<string>();
  const targets: DeepDiveTarget[] = [];
  for (const s of segments) {
    if (s.type !== "verse" || seen.has(s.passage.reference) || targets.length >= max) continue;
    seen.add(s.passage.reference);
    const first = firstVerseRef(s.passage);
    const compareRef = s.passage.verses.length <= MAX_COMPARE_VERSES ? s.passage.reference : first;
    targets.push({ reference: s.passage.reference, compareRef, firstVerse: first });
  }
  return targets;
}

export function chapterTargets(segments: Segment[], max: number): string[] {
  const refs = segments.flatMap((s) =>
    s.type === "timeline" || s.type === "map" || s.type === "chiasm" ? [s.reference.split(":")[0]] : [],
  );
  return [...new Set(refs)].slice(0, max);
}

const words = (text: string) =>
  new Set(
    text
      .toLocaleLowerCase("pt-BR")
      .split(/[^\p{L}]+/u)
      .filter((w) => w.length > 2),
  );

/** Palavras que só uma das traduções usa: destacam onde as traduções escolheram termos diferentes. */
export function distinctWords(texts: Record<string, string>): Record<string, Set<string>> {
  const sets = Object.fromEntries(Object.entries(texts).map(([k, t]) => [k, words(t)]));
  return Object.fromEntries(
    Object.entries(sets).map(([k, set]) => [
      k,
      new Set([...set].filter((w) => Object.entries(sets).every(([other, s]) => other === k || !s.has(w)))),
    ]),
  );
}

export interface GenealogyPerson {
  id: string;
  name: string;
  name_is_pt: boolean;
  brief: string | null;
  in_text: boolean;
}

export interface GenealogyLink {
  from: string;
  to: string;
  kind: "pai" | "conjuge";
}

export interface PlacedPerson extends GenealogyPerson {
  generation: number;
  x: number;
  y: number;
}

export const GEN_ROW = 66;
const TOP = 30;
const LINE = 34;
const PER_LINE = 5;

function generations(people: GenealogyPerson[], links: GenealogyLink[]): Map<string, number> {
  const gen = new Map(people.map((p) => [p.id, 0]));
  for (let round = 0; round < people.length + 1; round++) {
    let changed = false;
    for (const l of links) {
      const a = gen.get(l.from) ?? 0;
      const b = gen.get(l.to) ?? 0;
      const want = l.kind === "pai" ? a + 1 : Math.max(a, b);
      if (l.kind === "pai" && b < want) {
        gen.set(l.to, want);
        changed = true;
      } else if (l.kind === "conjuge" && (a !== want || b !== want)) {
        gen.set(l.from, want);
        gen.set(l.to, want);
        changed = true;
      }
    }
    if (!changed) break;
  }
  const min = Math.min(...gen.values());
  return new Map([...gen].map(([id, g]) => [id, g - min]));
}

/** Gerações de cima para baixo; cada pessoa perto dos pais (baricentro), cônjuges ao lado. */
export function layoutGenealogy(people: GenealogyPerson[], links: GenealogyLink[], width: number): PlacedPerson[] {
  const gen = generations(people, links);
  const order = new Map(people.map((p, i) => [p.id, i]));
  const rows = new Map<number, GenealogyPerson[]>();
  for (const p of people) rows.set(gen.get(p.id) ?? 0, [...(rows.get(gen.get(p.id) ?? 0) ?? []), p]);
  const position = new Map<string, number>();
  for (const g of [...rows.keys()].sort((a, b) => a - b)) {
    const row = rows.get(g) ?? [];
    const score = (p: GenealogyPerson) => {
      const parents = links.filter((l) => l.kind === "pai" && l.to === p.id).map((l) => position.get(l.from));
      const known = parents.filter((x): x is number => x !== undefined);
      if (known.length) return known.reduce((a, b) => a + b, 0) / known.length;
      const spouse = links.find((l) => l.kind === "conjuge" && (l.from === p.id || l.to === p.id));
      const partner = spouse && position.get(spouse.from === p.id ? spouse.to : spouse.from);
      return partner !== undefined ? partner + 0.01 : (order.get(p.id) ?? 0) / people.length;
    };
    row.sort((a, b) => score(a) - score(b));
    row.forEach((p, i) => position.set(p.id, (i + 1) / (row.length + 1)));
  }
  const lineOf = new Map<string, { line: number; slot: number; count: number }>();
  const linesPerGen = new Map<number, number>();
  for (const [g, row] of rows) {
    const lines = Math.ceil(row.length / PER_LINE);
    linesPerGen.set(g, lines);
    row.forEach((p, i) => {
      const line = Math.floor(i / Math.ceil(row.length / lines));
      const perLine = Math.ceil(row.length / lines);
      const count = Math.min(perLine, row.length - line * perLine);
      lineOf.set(p.id, { line, slot: i - line * perLine, count });
    });
  }
  const tops = new Map<number, number>();
  let y = TOP;
  for (const g of [...rows.keys()].sort((a, b) => a - b)) {
    tops.set(g, y);
    y += GEN_ROW + ((linesPerGen.get(g) ?? 1) - 1) * LINE;
  }
  return people.map((p) => {
    const g = gen.get(p.id) ?? 0;
    const at = lineOf.get(p.id) ?? { line: 0, slot: 0, count: 1 };
    const single = (linesPerGen.get(g) ?? 1) === 1;
    const x = single ? (position.get(p.id) ?? 0.5) * width : ((at.slot + 1) / (at.count + 1)) * width;
    return { ...p, generation: g, x, y: (tops.get(g) ?? TOP) + at.line * LINE };
  });
}

/** Corta árvores muito altas em partes; a geração da emenda se repete no topo da parte seguinte. */
export function splitGenerations(nodes: PlacedPerson[], size: number): PlacedPerson[][] {
  const maxGen = Math.max(0, ...nodes.map((n) => n.generation));
  const parts = Math.max(1, Math.ceil(maxGen / size));
  return Array.from({ length: parts }, (_, k) =>
    nodes
      .filter((n) => n.generation >= k * size && n.generation <= (k + 1) * size)
      .sort((a, b) => a.generation - b.generation || a.x - b.x),
  );
}

/** Substantivos comuns e verbos do versículo (sem nomes próprios), candidatos a "palavra do original". */
export function profileCandidates(words: { strong: string; morphology: string }[], max: number): string[] {
  const content = words.filter(({ morphology: m }) => {
    const hebrew = /^[HA]/.test(m) && !m.includes("-");
    const code = hebrew ? m.slice(1) : m;
    return hebrew ? code.startsWith("Nc") || code.startsWith("V") : (code.startsWith("N-") && !code.startsWith("N-PRI")) || code.startsWith("V-");
  });
  return [...new Set(content.map((w) => w.strong))].slice(0, max);
}
