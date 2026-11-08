"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { formatTokens, toBlocks } from "@/lib/segments";
import { useChat, type UiMessage } from "@/stores/chat";
import type { IssueKind, Segment } from "@/types/api";
import { ChiasmCard } from "./ChiasmCard";
import { ThinkerCard } from "./ThinkerCard";
import { MapCard } from "./MapCard";
import { TimelineCard } from "./TimelineCard";
import { VerseCard } from "./VerseCard";

const ISSUE_LABEL: Record<IssueKind, string> = {
  referencia_inexistente: "Referência que não existe na Bíblia",
  citacao_nao_confere: "Citação entre aspas que não confere com o texto bíblico",
  interpretacao_contradiz: "Interpretação que contradiz o versículo citado",
  teologia_prosperidade: "Possível promessa de prosperidade em troca de fé ou oferta",
  teologia_investimento: "Indicação de investimento específico",
  teologia_condenacao: "Tom de condenação em vez de chamado à graça",
  fato_nao_confere: "Fato que não confere com a base",
};

export function CrisisCard({ numero, url }: { numero: string; url: string }) {
  return (
    <aside role="alert" className="mb-5 rounded-md border-2 border-vinho bg-pergaminho-claro px-5 py-4">
      <p className="font-escritura text-lg font-bold text-vinho">Você não está sozinho. Sua vida importa.</p>
      <p className="mt-1 leading-relaxed">
        Se você está pensando em se machucar ou em não continuar, ligue agora para o CVV no{" "}
        <a href={`tel:${numero}`} className="font-bold text-vinho underline">{numero}</a> (gratuito, 24 horas) ou
        converse pelo{" "}
        <a href={url} target="_blank" rel="noreferrer" className="font-bold text-vinho underline">cvv.org.br</a>.
        Procure também seu pastor e alguém de confiança.
      </p>
    </aside>
  );
}

function Issues({ segments }: { segments: Segment[] }) {
  const issues = segments.filter((s): s is Extract<Segment, { type: "issue" }> => s.type === "issue");
  if (!issues.length) return null;
  return (
    <div className="mt-4 rounded border border-vinho/40 bg-vinho/5 px-4 py-3 text-sm text-vinho">
      <p className="font-bold">A conferência automática encontrou pontos para revisar:</p>
      <ul className="mt-1 list-disc pl-5">
        {issues.map((issue, i) => (
          <li key={i}>
            {ISSUE_LABEL[issue.kind]}
            {issue.kind !== "teologia_prosperidade" && issue.kind !== "teologia_investimento" &&
              issue.kind !== "teologia_condenacao" && <span className="text-tinta-suave">: {issue.excerpt}</span>}
            {issue.correction && <span className="block font-bold text-oliva">{issue.correction}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function AssistantBody({ segments }: { segments: Segment[] }) {
  const openPopup = useChat((s) => s.openPopup);
  const blocks = toBlocks(segments);
  return (
    <>
      {blocks.map((block, i) => {
        if (block.kind !== "markdown") {
          const segment = segments[block.index];
          if (segment.type === "verse") return <VerseCard key={i} passage={segment.passage} />;
          if (segment.type === "timeline")
            return <TimelineCard key={i} reference={segment.reference} book={segment.book} sections={segment.sections} />;
          if (segment.type === "map") return <MapCard key={i} reference={segment.reference} places={segment.places} />;
          if (segment.type === "chiasm")
            return <ChiasmCard key={i} reference={segment.reference} book={segment.book} parts={segment.parts} />;
          if (segment.type === "thinker") return <ThinkerCard key={i} thinker={segment} />;
          return null;
        }
        const first = blocks.findIndex((b) => b.kind === "markdown") === i;
        return (
          <div key={i} className={first ? "md-first" : undefined}>
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              a: ({ href, children }) => {
                const match = href?.match(/^#([vx])(\d+)$/);
                if (!match) {
                  return <a href={href} target="_blank" rel="noreferrer">{children}</a>;
                }
                const segment = segments[Number(match[2])];
                if (match[1] === "x" || segment?.type !== "verse") {
                  return <span className="font-bold text-vinho">{children}</span>;
                }
                return (
                  <button
                    type="button"
                    onClick={() => openPopup({ reference: segment.passage.reference, translation: segment.passage.translation })}
                    className="font-bold text-couro underline decoration-ouro decoration-dotted underline-offset-4 hover:decoration-solid"
                  >
                    {children}
                  </button>
                );
              },
            }}
          >
            {block.markdown}
          </ReactMarkdown>
          </div>
        );
      })}
    </>
  );
}

export function MessageView({ message }: { message: UiMessage }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <p className="max-w-[min(34rem,85%)] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-gradient-to-br from-couro to-[#3b2a1c] px-4 py-2.5 text-pergaminho-claro shadow-[0_8px_20px_-14px_rgba(46,36,24,0.8)]">
          {message.text}
        </p>
      </div>
    );
  }
  const crisis = message.segments.find((s): s is Extract<Segment, { type: "crisis" }> => s.type === "crisis");
  const memories = message.segments.filter((s): s is Extract<Segment, { type: "memory" }> => s.type === "memory");
  const study = message.segments.some((s) => s.type === "timeline");
  const errors = message.segments.filter((s): s is Extract<Segment, { type: "error" }> => s.type === "error");
  const usage = message.segments.find((s): s is Extract<Segment, { type: "usage" }> => s.type === "usage");
  return (
    <article className={study ? "resposta estudo" : "resposta"}>
      {crisis && <CrisisCard numero={crisis.numero} url={crisis.url} />}
      <AssistantBody segments={message.segments} />
      {memories.map((m, i) => (
        <p key={i} className="mt-2 text-sm text-oliva">🧠 Lembrei: {m.topic.replaceAll("-", " ")}</p>
      ))}
      {errors.map((e, i) => (
        <p key={i} role="status" className="mt-3 text-sm font-bold text-vinho">{e.message}</p>
      ))}
      {message.status === "interrompida" && (
        <p className="mt-3 text-sm text-tinta-suave italic">
          Esta resposta foi interrompida porque o servidor reiniciou. Envie a pergunta de novo para receber a resposta completa.
        </p>
      )}
      {message.error && <p className="mt-3 text-sm font-bold text-vinho">{message.error}</p>}
      <Issues segments={message.segments} />
      {usage && (
        <p className="mt-3 text-xs text-tinta-suave">
          {formatTokens(usage.total)} tokens nesta resposta ({formatTokens(usage.cached)} do cache,{" "}
          {formatTokens(usage.output)} escritos) · média de{" "}
          {formatTokens(usage.average)} por pergunta ({usage.questions} {usage.questions === 1 ? "pergunta" : "perguntas"})
        </p>
      )}
    </article>
  );
}
