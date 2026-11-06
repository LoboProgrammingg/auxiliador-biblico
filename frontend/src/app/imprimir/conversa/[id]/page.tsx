import { notFound } from "next/navigation";
import { Contents } from "@/components/print/Contents";
import { Cover } from "@/components/print/Cover";
import { DeepDive } from "@/components/print/DeepDive";
import { PeoplePlaces } from "@/components/print/PeoplePlaces";
import { PrintAnswer } from "@/components/print/PrintAnswer";
import { PrintDocument } from "@/components/print/PrintDocument";
import { Sources } from "@/components/print/Sources";
import { longDay } from "@/lib/diary";
import { chapterTargets, deepDiveTargets, outline } from "@/lib/print";
import { fetchApi } from "@/lib/server-api";
import type { ConversationSummary, Segment, StoredMessage } from "@/types/api";

export default async function PrintConversation({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [meta, list] = await Promise.all([
    fetchApi<ConversationSummary>(`/conversations/${id}`),
    fetchApi<{ items: StoredMessage[] }>(`/conversations/${id}/messages`),
  ]);
  if (!meta || !list) notFound();
  const messages = list.items;
  const segments: Segment[] = messages.flatMap((m) => (m.role === "assistant" ? (m.segments ?? []) : []));
  const study = segments.some((s) => s.type === "timeline");
  const numbers = messages.map((_, i) => messages.slice(0, i + 1).filter((m) => m.role === "user").length);
  return (
    <PrintDocument pdfPath={`conversa/${id}`}>
      <Cover eyebrow={study ? "Estudo bíblico" : "Conversa"} title={meta.title} date={longDay(meta.updated_at)} />
      <Contents
        items={[
          ...outline(messages),
          ...(chapterTargets(segments, 3).length ? [{ id: "pessoas-lugares", title: "Pessoas e lugares", level: 1 as const }] : []),
          ...(deepDiveTargets(segments, 6).length ? [{ id: "aprofundamento", title: "Aprofundamento", level: 1 as const }] : []),
          { id: "fontes", title: "Fontes e licenças", level: 1 },
        ]}
      />
      <section className="secao corpo">
        {messages.map((m, i) => {
          if (m.role === "user") return <h2 key={i} id={`q${numbers[i]}`} className="pergunta">{m.text}</h2>;
          return <PrintAnswer key={i} segments={m.segments ?? []} prefix={`q${Math.max(numbers[i], 1)}`} />;
        })}
      </section>
      <PeoplePlaces chapters={chapterTargets(segments, 3)} />
      <DeepDive targets={deepDiveTargets(segments, 6)} />
      <Sources />
    </PrintDocument>
  );
}
