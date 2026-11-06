import { WordProfileChart, type WordProfile } from "@/components/illustrations/WordProfileChart";
import { distinctWords, profileCandidates, type DeepDiveTarget } from "@/lib/print";
import { fetchApi, query } from "@/lib/server-api";
import type { CompareItem, OriginalWord } from "@/types/api";

const TRANSLATIONS = "vfl,acf,nvt";

function CompareTable({ items }: { items: CompareItem[] }) {
  const present = items.filter((i) => i.verses?.length);
  const texts = Object.fromEntries(present.map((i) => [i.translation, (i.verses ?? []).map((v) => v.text).join(" ")]));
  const distinct = distinctWords(texts);
  return (
    <div className="comparativo">
      {present.map((item) => (
        <div key={item.translation} className="comparativo-coluna">
          <p className="comparativo-nome">{item.translation.toUpperCase()} <span>{item.name}</span></p>
          <p className="comparativo-texto">
            {(item.verses ?? []).map((v) => (
              <span key={v.n}>
                <sup>{v.n}</sup>
                {v.text.split(/(\s+)/).map((piece, k) =>
                  distinct[item.translation]?.has(piece.toLocaleLowerCase("pt-BR").replace(/[^\p{L}]/gu, "")) ? (
                    <mark key={k}>{piece}</mark>
                  ) : (
                    piece
                  ),
                )}{" "}
              </span>
            ))}
          </p>
          {item.note && <p className="legenda">{item.note}</p>}
        </div>
      ))}
    </div>
  );
}

function Interlinear({ words }: { words: OriginalWord[] }) {
  const rtl = words[0]?.language !== "grc";
  return (
    <ol className="interlinear" dir={rtl ? "rtl" : "ltr"}>
      {words.map((w, i) => (
        <li key={`${w.position}-${i}`} dir="ltr">
          <span className={w.language === "grc" ? "grego" : "hebraico"} dir={rtl ? "rtl" : "ltr"}>{w.surface.replaceAll("/", "")}</span>
          <span className="translit">{w.transliteration.replaceAll("/", "")}</span>
          <span className="strong">{w.strong}</span>
          <span className="glosa">{w.lexicon_gloss ?? w.gloss_en}</span>
        </li>
      ))}
    </ol>
  );
}

async function bestProfile(words: OriginalWord[]): Promise<WordProfile | null> {
  const profiles = await Promise.all(
    profileCandidates(words, 4).map((s) => fetchApi<WordProfile>(`/bible/word-profile?${query({ strong: s })}`)),
  );
  const found = profiles.filter((p): p is WordProfile => p !== null && p.total > 1);
  return found.sort((a, b) => a.total - b.total)[0] ?? null;
}

async function Target({ target, n }: { target: DeepDiveTarget; n: number }) {
  const [compare, original] = await Promise.all([
    fetchApi<{ items: CompareItem[] }>(`/bible/compare?${query({ ref: target.compareRef, translations: TRANSLATIONS })}`),
    fetchApi<{ words: OriginalWord[] }>(`/bible/original?${query({ ref: target.firstVerse })}`),
  ]);
  const profile = original?.words.length ? await bestProfile(original.words) : null;
  if (!compare?.items.length && !original?.words.length) return null;
  return (
    <section className="aprofundamento-item" id={`ap${n}`}>
      <h3>{target.reference}</h3>
      {compare?.items.length ? (
        <>
          <h4>Três traduções lado a lado</h4>
          {target.compareRef !== target.reference && <p className="legenda">Comparação do primeiro versículo ({target.compareRef}).</p>}
          <CompareTable items={compare.items} />
          <p className="legenda">Destacadas: palavras que só aquela tradução usa.</p>
        </>
      ) : null}
      {original?.words.length ? (
        <>
          <h4>Palavra por palavra no original ({target.firstVerse})</h4>
          <Interlinear words={original.words} />
          <p className="legenda">Glosas do léxico em inglês (STEPBible, CC BY 4.0).</p>
        </>
      ) : null}
      {profile && (
        <>
          <h4>Uma palavra para guardar</h4>
          <WordProfileChart profile={profile} />
        </>
      )}
    </section>
  );
}

export async function DeepDive({ targets }: { targets: DeepDiveTarget[] }) {
  if (targets.length === 0) return null;
  return (
    <section className="secao" id="aprofundamento">
      <h2>Aprofundamento</h2>
      <p className="intro">Para cada passagem citada: as traduções lado a lado, o texto original e uma palavra-chave com onde mais ela aparece na Bíblia.</p>
      {targets.map((t, i) => <Target key={t.reference} target={t} n={i + 1} />)}
    </section>
  );
}
