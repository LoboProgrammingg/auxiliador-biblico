import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChiasmDiagram } from "@/components/illustrations/ChiasmDiagram";
import { PlacesDiagram } from "@/components/illustrations/PlacesDiagram";
import { TimelineDiagram } from "@/components/illustrations/TimelineDiagram";
import { headingLines } from "@/lib/print";
import { toBlocks } from "@/lib/segments";
import type { Segment } from "@/types/api";
import { PrintVerse } from "./PrintVerse";

function Figure({ title, note, children }: { title: string; note?: string; children: React.ReactNode }) {
  return (
    <figure className="ilustracao">
      <figcaption>{title}</figcaption>
      {children}
      {note && <p className="legenda">{note}</p>}
    </figure>
  );
}

/** Resposta do auxiliador pronta para o papel; os títulos ganham âncoras para o sumário. */
export function PrintAnswer({ segments, prefix }: { segments: Segment[]; prefix: string }) {
  const blocks = toBlocks(segments);
  const lines = blocks.map((b) => (b.kind === "markdown" ? headingLines(b.markdown).map((h) => h.line) : []));
  const offsets = lines.map((_, i) => lines.slice(0, i).reduce((n, l) => n + l.length, 0));
  type HeadingProps = { children?: React.ReactNode; node?: { position?: { start: { line: number } } } };
  const anchored = (Tag: "h2" | "h3" | "h4", block: number) =>
    function Heading({ children, node }: HeadingProps) {
      const index = lines[block].indexOf(node?.position?.start.line ?? -1);
      return <Tag id={index >= 0 ? `${prefix}-h${offsets[block] + index + 1}` : undefined}>{children}</Tag>;
    };
  const crisis = segments.find((s) => s.type === "crisis");
  const errors = segments.filter((s): s is Extract<Segment, { type: "error" }> => s.type === "error");
  const issues = segments.filter((s) => s.type === "issue").length;
  return (
    <div className="resposta-impressa">
      {crisis && (
        <aside className="cvv">
          Se você está pensando em se machucar, ligue para o CVV: 188 (gratuito, 24 horas) ou acesse cvv.org.br.
        </aside>
      )}
      {blocks.map((block, i) => {
        if (block.kind === "markdown")
          return (
            <ReactMarkdown
              key={i}
              remarkPlugins={[remarkGfm]}
              components={{
                h1: anchored("h2", i),
                h2: anchored("h3", i),
                h3: anchored("h4", i),
                a: ({ children }) => <strong className="ref">{children}</strong>,
              }}
            >
              {block.markdown}
            </ReactMarkdown>
          );
        const s = segments[block.index];
        if (s.type === "verse") return <PrintVerse key={i} passage={s.passage} />;
        if (s.type === "timeline")
          return (
            <Figure key={i} title={`${s.book} ${s.reference.split(" ").slice(1).join(" ")}: as cenas em ordem`}>
              <TimelineDiagram reference={s.reference} sections={s.sections} />
            </Figure>
          );
        if (s.type === "map")
          return (
            <Figure key={i} title="Onde acontece" note="Posições aproximadas. Dados de OpenBible.info, CC BY 4.0.">
              <PlacesDiagram places={s.places} label={`Mapa de ${s.reference}`} />
              <p className="legenda">{s.places.map((p) => `${p.name} (v. ${p.verses.join(", ")})`).join(" · ")}</p>
            </Figure>
          );
        if (s.type === "chiasm")
          return (
            <Figure key={i} title={`${s.book} ${s.reference.split(" ").slice(1).join(" ")}: estrutura em espelho`}
              note="Estrutura proposta (quiasmo): uma leitura de estudo; os versículos foram conferidos no banco.">
              <ChiasmDiagram parts={s.parts} />
            </Figure>
          );
        return null;
      })}
      {errors.map((e, i) => <p key={`e${i}`} className="aviso">{e.message}</p>)}
      {issues > 0 && (
        <p className="aviso">A conferência automática marcou {issues} ponto(s) desta resposta para revisar.</p>
      )}
    </div>
  );
}
