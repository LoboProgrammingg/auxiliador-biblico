import type { PlanDay } from "@/types/api";

export function studyPrompt(planName: string, day: number, readings: string[]): string {
  const list = readings.length > 1 ? `${readings.slice(0, -1).join(", ")} e ${readings[readings.length - 1]}` : readings[0];
  return (
    `Estudo do dia ${day} do plano «${planName}»: ${list}. Leia comigo e me conduza: um panorama do trecho, ` +
    "as cenas em ordem, o que aprendo sobre Deus e uma aplicação para hoje."
  );
}

export function progressPercent(done: number, total: number): number {
  return total > 0 ? Math.round((done / total) * 100) : 0;
}

const BEFORE = 2;
const AFTER = 6;

export function visibleDays(days: PlanDay[], today: number, expanded: boolean): PlanDay[] {
  if (expanded) return days;
  const start = Math.max(0, today - 1 - BEFORE);
  return days.slice(start, start + BEFORE + AFTER + 1);
}
