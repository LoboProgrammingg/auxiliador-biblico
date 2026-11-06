import { describe, expect, test } from "vitest";
import { progressPercent, studyPrompt, visibleDays } from "./plans";

describe("plans", () => {
  test("study prompt names plan, day and readings", () => {
    expect(studyPrompt("Evangelhos em 30 dias", 3, ["Mt 7–9"])).toBe(
      "Estudo do dia 3 do plano «Evangelhos em 30 dias»: Mt 7–9. Leia comigo e me conduza: um panorama do trecho, " +
        "as cenas em ordem, o que aprendo sobre Deus e uma aplicação para hoje.",
    );
    expect(studyPrompt("Família", 1, ["Gn 2:18-25", "Ef 5:21-33"])).toContain("Gn 2:18-25 e Ef 5:21-33.");
  });

  test("progress percent is rounded and safe", () => {
    expect(progressPercent(1, 3)).toBe(33);
    expect(progressPercent(0, 0)).toBe(0);
  });

  test("visible days show a window around today unless expanded", () => {
    const days = Array.from({ length: 365 }, (_, i) => ({ day: i + 1, readings: [], done: false }));
    expect(visibleDays(days, 100, false).map((d) => d.day)).toEqual([98, 99, 100, 101, 102, 103, 104, 105, 106]);
    expect(visibleDays(days, 1, false)[0].day).toBe(1);
    expect(visibleDays(days, 100, true)).toHaveLength(365);
  });
});
