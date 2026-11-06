"use client";

import type { Passage } from "@/types/api";
import { useChat } from "@/stores/chat";

export function VerseCard({ passage }: { passage: Passage }) {
  const openPopup = useChat((s) => s.openPopup);
  const cited = passage.verses.filter((v) => v.cited);
  return (
    <figure className="relative my-6 max-w-[68ch] rounded-r-lg border-l-[3px] border-ouro bg-gradient-to-br from-pergaminho-claro to-[#f6edd6] py-4 pr-5 pl-7 shadow-[0_1px_0_#e7dcc3,0_14px_30px_-24px_rgba(74,53,36,0.6)]">
      <span aria-hidden className="pointer-events-none absolute top-0 left-2 font-escritura text-5xl leading-none text-ouro/35">“</span>
      <blockquote className="font-escritura text-[1.18rem] leading-[1.8] text-tinta">
        {cited.map((v) => (
          <span key={v.n}>
            {cited.length > 1 && <sup className="mr-1 text-xs font-bold text-ouro">{v.n}</sup>}
            {v.text}{" "}
          </span>
        ))}
      </blockquote>
      <figcaption className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm">
        <button
          type="button"
          onClick={() => openPopup({ reference: passage.reference, translation: passage.translation })}
          className="font-bold text-couro underline decoration-ouro decoration-dotted underline-offset-4 hover:decoration-solid"
        >
          {passage.book} {passage.reference.split(" ").slice(1).join(" ")}
        </button>
        <span className="text-tinta-suave">{passage.translation.toUpperCase()}</span>
        {passage.fallback_label && <span className="text-xs italic text-tinta-suave">{passage.fallback_label}</span>}
      </figcaption>
    </figure>
  );
}
