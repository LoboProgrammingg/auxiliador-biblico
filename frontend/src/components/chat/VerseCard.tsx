"use client";

import type { Passage } from "@/types/api";
import { useChat } from "@/stores/chat";

export function VerseCard({ passage }: { passage: Passage }) {
  const openPopup = useChat((s) => s.openPopup);
  const cited = passage.verses.filter((v) => v.cited);
  return (
    <figure className="my-5 max-w-[68ch] border-l-[3px] border-ouro bg-pergaminho-claro/80 py-3 pr-4 pl-5">
      <blockquote className="font-escritura text-[1.16rem] leading-[1.75] text-tinta">
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
