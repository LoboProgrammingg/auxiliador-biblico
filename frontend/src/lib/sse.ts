import type { ChatEvent } from "@/types/api";

const EVENT_NAMES = new Set([
  "text", "verse", "invalid_reference", "timeline", "map", "chiasm", "thinker", "status", "memory_saved", "crisis", "triage", "issues", "usage", "done", "error",
]);

export function parseSSE(chunk: string, carry: string): { events: ChatEvent[]; carry: string } {
  const buffer = carry + chunk;
  const blocks = buffer.split("\n\n");
  const rest = blocks.pop() ?? "";
  const events: ChatEvent[] = [];
  for (const block of blocks) {
    let name = "";
    let data = "";
    for (const line of block.split("\n")) {
      if (line.startsWith("event: ")) name = line.slice(7).trim();
      else if (line.startsWith("data: ")) data += line.slice(6);
    }
    if (!EVENT_NAMES.has(name) || !data) continue;
    try {
      events.push({ event: name, data: JSON.parse(data) } as ChatEvent);
    } catch {
      continue;
    }
  }
  return { events, carry: rest };
}
