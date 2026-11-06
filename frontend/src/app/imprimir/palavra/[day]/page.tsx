import { notFound } from "next/navigation";
import { Cover } from "@/components/print/Cover";
import { DeepDive } from "@/components/print/DeepDive";
import { PrintAnswer } from "@/components/print/PrintAnswer";
import { PrintDocument } from "@/components/print/PrintDocument";
import { Sources } from "@/components/print/Sources";
import { longDay } from "@/lib/diary";
import { deepDiveTargets } from "@/lib/print";
import { fetchApi } from "@/lib/server-api";
import type { DailyWordItem, StoredMessage } from "@/types/api";

export default async function PrintDailyWord({ params }: { params: Promise<{ day: string }> }) {
  const { day } = await params;
  const history = await fetchApi<{ items: DailyWordItem[] }>("/daily-words");
  const word = history?.items.find((w) => w.day === day);
  if (!word) notFound();
  const list = await fetchApi<{ items: StoredMessage[] }>(`/conversations/${word.conversation_id}/messages`);
  const answer = [...(list?.items ?? [])].reverse().find((m) => m.role === "assistant" && m.segments?.length);
  if (!answer) notFound();
  const segments = answer.segments ?? [];
  return (
    <PrintDocument pdfPath={`palavra/${day}`}>
      <Cover eyebrow="Palavra de hoje" title={word.reference ?? "Uma palavra pra mim"} date={longDay(day)} />
      <section className="secao corpo palavra">
        <PrintAnswer segments={segments} prefix="p" />
      </section>
      <DeepDive targets={deepDiveTargets(segments, 2)} />
      <Sources />
    </PrintDocument>
  );
}
