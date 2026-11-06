import type { ChatEvent, Segment } from "@/types/api";

export function applyEvent(segments: Segment[], ev: ChatEvent): Segment[] {
  switch (ev.event) {
    case "text": {
      const last = segments[segments.length - 1];
      if (last?.type === "text") return [...segments.slice(0, -1), { type: "text", text: last.text + ev.data.text }];
      return [...segments, { type: "text", text: ev.data.text }];
    }
    case "verse":
      return [...segments, { type: "verse", marker: ev.data.marker, passage: ev.data.passage }];
    case "invalid_reference":
      return [...segments, { type: "invalid_reference", marker: ev.data.marker }];
    case "issues":
      return [...segments, ...ev.data.items.map((i) => ({ type: "issue" as const, ...i }))];
    case "crisis":
      return [{ type: "crisis", numero: ev.data.numero, url: ev.data.url }, ...segments];
    case "memory_saved":
      return [...segments, { type: "memory", topic: ev.data.topic }];
    default:
      return segments;
  }
}

export type Block = { kind: "markdown"; markdown: string } | { kind: "card"; index: number };

function isInline(segments: Segment[], i: number): boolean {
  const prev = segments[i - 1];
  const next = segments[i + 1];
  const prevBreaks = !prev || prev.type !== "text" || prev.text.endsWith("\n");
  const nextBreaks = !next || next.type !== "text" || next.text.startsWith("\n");
  return !(prevBreaks && nextBreaks);
}

export function toBlocks(segments: Segment[]): Block[] {
  const blocks: Block[] = [];
  let markdown = "";
  const flush = () => {
    if (markdown.trim()) blocks.push({ kind: "markdown", markdown });
    markdown = "";
  };
  segments.forEach((segment, i) => {
    if (segment.type === "text") markdown += segment.text;
    else if (segment.type === "invalid_reference") markdown += `[⚠ referência não encontrada](#x${i})`;
    else if (segment.type === "verse") {
      if (isInline(segments, i)) markdown += `[${segment.passage.reference}](#v${i})`;
      else {
        flush();
        blocks.push({ kind: "card", index: i });
      }
    }
  });
  flush();
  return blocks;
}
