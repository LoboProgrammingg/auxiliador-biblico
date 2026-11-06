import { describe, expect, test } from "vitest";
import { project } from "./geo";

describe("project", () => {
  test("fits points inside the viewport with padding, north up", () => {
    const pts = project([{ lon: 35, lat: 32 }, { lon: 36, lat: 33 }], 400, 300, 30);
    for (const p of pts) {
      expect(p.x).toBeGreaterThanOrEqual(30);
      expect(p.x).toBeLessThanOrEqual(370);
      expect(p.y).toBeGreaterThanOrEqual(30);
      expect(p.y).toBeLessThanOrEqual(270);
    }
    expect(pts[1].y).toBeLessThan(pts[0].y);
    expect(pts[1].x).toBeGreaterThan(pts[0].x);
  });

  test("single point is centered", () => {
    expect(project([{ lon: 35, lat: 32 }], 400, 300, 30)).toEqual([{ x: 200, y: 150 }]);
  });
});

import { layoutLabels } from "./geo";

function box(l: { x: number; y: number; anchor: "start" | "end" }, name: string) {
  const w = name.length * 8.5;
  const x0 = l.anchor === "start" ? l.x : l.x - w;
  return { x0, x1: x0 + w, y0: l.y - 13, y1: l.y + 3 };
}

describe("layoutLabels", () => {
  test("labels of nearby points do not overlap", () => {
    const pts = [{ x: 300, y: 330 }, { x: 366, y: 316 }, { x: 368, y: 334 }];
    const names = ["Jerusalém", "Betânia", "Jordão"];
    const labels = layoutLabels(pts, names, 640, 380);
    const boxes = labels.map((l, i) => box(l, names[i]));
    for (let i = 0; i < boxes.length; i++)
      for (let j = i + 1; j < boxes.length; j++) {
        const a = boxes[i];
        const b = boxes[j];
        const overlap = a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1;
        expect(overlap).toBe(false);
      }
  });

  test("labels stay inside the frame", () => {
    const labels = layoutLabels([{ x: 630, y: 10 }], ["Cesareia de Filipe"], 640, 380);
    const b = box(labels[0], "Cesareia de Filipe");
    expect(b.x0).toBeGreaterThanOrEqual(0);
    expect(b.x1).toBeLessThanOrEqual(640);
    expect(b.y0).toBeGreaterThanOrEqual(0);
  });
});
