"use client";

import { API_URL } from "@/services/api";
import { useChat } from "@/stores/chat";
import { AssistantBody } from "./MessageView";
import { Divider } from "./Ornament";
import { BlockSkeleton } from "./Skeletons";

function longDate(day: string): string {
  return new Date(`${day}T12:00:00`).toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" });
}

export function DailyWordCard() {
  const daily = useChat((s) => s.daily);
  const close = useChat((s) => s.closeDailyWord);
  if (daily.status === "idle") return null;
  return (
    <section aria-label="Palavra de hoje"
      className="relative rounded-xl border border-ouro/40 bg-gradient-to-b from-[#fbf5e4] to-pergaminho-claro px-6 pt-5 pb-6 shadow-[0_1px_0_#e7dcc3,0_20px_40px_-28px_rgba(74,53,36,0.7)]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-escritura text-2xl font-bold text-couro">Palavra de hoje</h2>
          {daily.status === "ready" && <p className="text-sm text-tinta-suave first-letter:uppercase">{longDate(daily.word.day)}</p>}
        </div>
        <div className="flex items-center gap-1">
          {daily.status === "ready" && (
            <a href={`${API_URL}/api/v1/export/palavra/${daily.word.day}.pdf`} className="rounded px-2 py-1 text-sm font-bold text-couro hover:bg-borda/60">
              PDF
            </a>
          )}
          <button type="button" onClick={close} className="rounded px-2 py-1 text-sm text-tinta-suave hover:bg-borda/60">
            Fechar
          </button>
        </div>
      </div>
      <Divider className="mt-2" />
      <div className="resposta mt-1">
        {daily.status === "loading" && (
          <div className="pt-3">
            <p className="mb-3 text-sm text-tinta-suave">Preparando sua palavra de hoje…</p>
            <BlockSkeleton lines={4} />
          </div>
        )}
        {daily.status === "error" && <p className="pt-3 font-bold text-vinho">{daily.message}</p>}
        {daily.status === "ready" && (
          <AssistantBody segments={daily.word.segments} />
        )}
      </div>
    </section>
  );
}
