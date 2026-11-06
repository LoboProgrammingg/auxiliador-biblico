export interface WordProfile {
  strong: string;
  lemma: string;
  transliteration: string;
  gloss: string;
  total: number;
  by_book: { book: string; count: number }[];
}

const W = 720;
const ROW = 22;
const MAX_BOOKS = 10;

/** Onde a palavra do original mais aparece (contagem no texto hebraico/grego do STEPBible). */
export function WordProfileChart({ profile }: { profile: WordProfile }) {
  const top = [...profile.by_book].sort((a, b) => b.count - a.count).slice(0, MAX_BOOKS);
  const max = Math.max(...top.map((b) => b.count));
  const hebrew = profile.strong.startsWith("H");
  return (
    <div className="perfil">
      <p className="perfil-lema">
        <span className={hebrew ? "hebraico" : "grego"} dir={hebrew ? "rtl" : "ltr"}>{profile.lemma}</span>{" "}
        <em>{profile.transliteration}</em> <span className="strong">{profile.strong}</span>
      </p>
      <p className="legenda">{profile.gloss} (léxico em inglês) · {profile.total} ocorrências no original</p>
      <svg viewBox={`0 0 ${W} ${top.length * ROW + 6}`} className="w-full" role="img" aria-label={`Ocorrências de ${profile.strong} por livro`}>
        {top.map((b, i) => (
          <g key={b.book}>
            <text x={150} y={i * ROW + 15} textAnchor="end" fontSize="12" fill="#2e2418">{b.book}</text>
            <rect x={158} y={i * ROW + 4} width={Math.max(2, ((W - 220) * b.count) / max)} height={14} rx={2} fill="#a0802f" opacity={0.35 + (0.65 * b.count) / max} />
            <text x={162 + ((W - 220) * b.count) / max} y={i * ROW + 15} fontSize="11" fill="#5a4a37">{b.count}</text>
          </g>
        ))}
      </svg>
    </div>
  );
}
