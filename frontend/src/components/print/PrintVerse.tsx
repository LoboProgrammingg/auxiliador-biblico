import type { Passage } from "@/types/api";

export function PrintVerse({ passage }: { passage: Passage }) {
  const cited = passage.verses.filter((v) => v.cited);
  return (
    <figure className="versiculo">
      <blockquote>
        {cited.map((v) => (
          <span key={v.n}>
            {cited.length > 1 && <sup>{v.n}</sup>}
            {v.text}{" "}
          </span>
        ))}
      </blockquote>
      <figcaption>
        {passage.book} {passage.reference.split(" ").slice(1).join(" ")} <span className="traducao">{passage.translation.toUpperCase()}</span>
        {passage.fallback_label && <span className="aviso"> · {passage.fallback_label}</span>}
      </figcaption>
    </figure>
  );
}
