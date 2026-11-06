"use client";

import { ChiasmDiagram } from "@/components/illustrations/ChiasmDiagram";
import { useChat } from "@/stores/chat";
import type { ChiasmPart } from "@/types/api";

export function ChiasmCard({ reference, book, parts }: { reference: string; book: string; parts: ChiasmPart[] }) {
  const openPopup = useChat((s) => s.openPopup);
  const chapter = reference.split(" ").slice(1).join(" ");
  return (
    <figure className="my-6 rounded-lg border border-borda bg-pergaminho-claro/90 px-5 pt-4 pb-4 shadow-[0_1px_0_#e7dcc3,0_12px_30px_-22px_rgba(74,53,36,0.55)]">
      <figcaption className="font-escritura text-lg font-bold text-couro">{book} {chapter}: estrutura em espelho</figcaption>
      <div className="mt-3">
        <ChiasmDiagram parts={parts} onOpen={(p) => openPopup({ reference: `${reference}:${p.start}-${p.end}`, translation: "vfl" })} />
      </div>
      <p className="mt-2 text-xs text-tinta-suave">
        Estrutura proposta (quiasmo): as partes com a mesma letra se correspondem. Os versículos foram conferidos no banco;
        a divisão é uma leitura de estudo, não parte do texto bíblico.
      </p>
    </figure>
  );
}
