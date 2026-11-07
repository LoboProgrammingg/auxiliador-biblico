import type { ChatOptions } from "@/lib/chatOptions";
import { parseSSE } from "@/lib/sse";
import type {
  ChatEvent,
  DailyWord,
  CompareItem,
  ConversationSummary,
  CrossRef,
  DailyWordItem,
  MemoryItem,
  PlanCatalogItem,
  PlanDetail,
  PlanSummary,
  Prayer,
  VerseNote,
  OriginalWord,
  Passage,
  StoredMessage,
} from "@/types/api";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}/api/v1${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!response.ok) {
    const detail = await response.json().then((b: { detail?: unknown }) => b.detail).catch(() => undefined);
    throw new ApiError(response.status, typeof detail === "string" ? detail : `Erro ${response.status} em ${path}`);
  }
  return (response.status === 204 ? undefined : await response.json()) as T;
}

const q = (params: Record<string, string | number>) =>
  new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString();

export const api = {
  health: () => request<{ status: string; agente: string; embeddings: string }>("/health"),
  createConversation: () => request<{ id: string }>("/conversations", { method: "POST" }),
  conversations: () => request<{ items: ConversationSummary[] }>("/conversations").then((r) => r.items),
  messages: (id: string) => request<{ items: StoredMessage[] }>(`/conversations/${id}/messages`).then((r) => r.items),
  deleteConversation: (id: string) => request<void>(`/conversations/${id}`, { method: "DELETE" }),
  passage: (ref: string, translation: string, context = 3) =>
    request<Passage>(`/bible/passage?${q({ ref, translation, context })}`),
  compare: (ref: string, translations = "vfl,acf,nvt") =>
    request<{ reference: string; items: CompareItem[] }>(`/bible/compare?${q({ ref, translations })}`),
  original: (ref: string) => request<{ reference: string; words: OriginalWord[] }>(`/bible/original?${q({ ref })}`),
  crossReferences: (ref: string) =>
    request<{ reference: string; items: CrossRef[] }>(`/bible/cross-references?${q({ ref, limit: 10 })}`),
  dailyWord: () => request<DailyWord>("/daily-word", { method: "POST" }),
  dailyWords: () => request<{ items: DailyWordItem[] }>("/daily-words").then((r) => r.items),
  prayers: () => request<{ items: Prayer[] }>("/prayers").then((r) => r.items),
  createPrayer: (title: string, details: string | null) =>
    request<Prayer>("/prayers", { method: "POST", body: JSON.stringify({ title, details }) }),
  updatePrayer: (p: Pick<Prayer, "id" | "title" | "details" | "status" | "answer_note">) =>
    request<Prayer>(`/prayers/${p.id}`, {
      method: "PUT",
      body: JSON.stringify({ title: p.title, details: p.details, status: p.status, answer_note: p.answer_note }),
    }),
  deletePrayer: (id: string) => request<void>(`/prayers/${id}`, { method: "DELETE" }),
  verseNotes: () => request<{ items: VerseNote[] }>("/verse-notes").then((r) => r.items),
  verseNote: (ref: string) =>
    request<VerseNote>(`/verse-notes/by-ref?${q({ ref })}`).catch((e: unknown) => {
      if (e instanceof ApiError && e.status === 404) return null;
      throw e;
    }),
  saveVerseNote: (ref: string, content: string) =>
    request<VerseNote>(`/verse-notes?${q({ ref })}`, { method: "PUT", body: JSON.stringify({ content }) }),
  deleteVerseNote: (id: number) => request<void>(`/verse-notes/${id}`, { method: "DELETE" }),
  planCatalog: () => request<{ items: PlanCatalogItem[] }>("/plans/catalog").then((r) => r.items),
  plans: () => request<{ items: PlanSummary[] }>("/plans").then((r) => r.items),
  plan: (id: string) => request<PlanDetail>(`/plans/${id}`),
  startPlan: (code: string) => request<{ id: string }>("/plans", { method: "POST", body: JSON.stringify({ code }) }),
  markPlanDay: (id: string, day: number, done: boolean) =>
    request<void>(`/plans/${id}/days/${day}`, { method: "PUT", body: JSON.stringify({ done }) }),
  deletePlan: (id: string) => request<void>(`/plans/${id}`, { method: "DELETE" }),
  memories: () => request<{ items: MemoryItem[] }>("/memories").then((r) => r.items),
  saveMemory: (topic: string, content: string) =>
    request<{ topic: string }>(`/memories/${encodeURIComponent(topic)}`, {
      method: "PUT",
      body: JSON.stringify({ content }),
    }),
  deleteMemory: (topic: string) => request<void>(`/memories/${encodeURIComponent(topic)}`, { method: "DELETE" }),
};

async function* readEvents(response: Response): AsyncGenerator<ChatEvent> {
  if (!response.body) return;
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let carry = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    const parsed = parseSSE(value, carry);
    carry = parsed.carry;
    yield* parsed.events;
  }
}

export async function* sendMessage(
  conversationId: string,
  text: string,
  options: ChatOptions & { plan: boolean },
  signal: AbortSignal,
): AsyncGenerator<ChatEvent> {
  const response = await fetch(`${API_URL}/api/v1/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, ...options }),
    signal,
  });
  if (!response.ok || !response.body) throw new ApiError(response.status, "Não foi possível enviar a mensagem.");
  yield* readEvents(response);
}

/** Reassina uma resposta que continua sendo gerada no servidor; termina sem eventos se não houver nenhuma. */
export async function* attachStream(conversationId: string, signal: AbortSignal): AsyncGenerator<ChatEvent> {
  const response = await fetch(`${API_URL}/api/v1/conversations/${conversationId}/stream`, { signal });
  if (response.status === 204) return;
  if (!response.ok) throw new ApiError(response.status, "Não foi possível retomar a resposta.");
  yield* readEvents(response);
}
