import type { Prayer } from "@/types/api";

const time = (iso: string | null) => (iso ? new Date(iso).getTime() : 0);

export function groupPrayers(prayers: Prayer[]): { open: Prayer[]; answered: Prayer[] } {
  return {
    open: prayers.filter((p) => p.status === "aberto").sort((a, b) => time(b.created_at) - time(a.created_at)),
    answered: prayers.filter((p) => p.status === "respondido").sort((a, b) => time(b.answered_at) - time(a.answered_at)),
  };
}

export function longDay(iso: string): string {
  const date = iso.length === 10 ? new Date(`${iso}T12:00:00`) : new Date(iso);
  return date.toLocaleDateString("pt-BR", { day: "numeric", month: "long", year: "numeric" });
}
