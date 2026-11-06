import { describe, expect, test } from "vitest";
import { parseSSE } from "./sse";

describe("parseSSE", () => {
  test("handles event split across chunks", () => {
    const a = parseSSE('event: text\ndata: {"te', "");
    expect(a.events).toEqual([]);
    const b = parseSSE('xt":"Oi"}\n\n', a.carry);
    expect(b.events).toEqual([{ event: "text", data: { text: "Oi" } }]);
    expect(b.carry).toBe("");
  });

  test("parses several events in one chunk", () => {
    const r = parseSSE('event: status\ndata: {"label":"Lendo…"}\n\nevent: done\ndata: {"message_id":3}\n\n', "");
    expect(r.events.map((e) => e.event)).toEqual(["status", "done"]);
  });

  test("ignores malformed blocks", () => {
    expect(parseSSE("lixo\n\n", "").events).toEqual([]);
  });
});
