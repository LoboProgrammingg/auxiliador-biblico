import { parseSSE } from "@/lib/sse";
import type {
  ChatEvent,
  DailyWord,
  CompareItem,
  ConversationSummary,
  CrossRef,
  MemoryItem,
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
  memories: () => request<{ items: MemoryItem[] }>("/memories").then((r) => r.items),
  saveMemory: (topic: string, content: string) =>
    request<{ topic: string }>(`/memories/${encodeURIComponent(topic)}`, {
      method: "PUT",
      body: JSON.stringify({ content }),
    }),
  deleteMemory: (topic: string) => request<void>(`/memories/${encodeURIComponent(topic)}`, { method: "DELETE" }),
};

export async function* sendMessage(conversationId: string, text: string, signal: AbortSignal): AsyncGenerator<ChatEvent> {
  const response = await fetch(`${API_URL}/api/v1/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
    signal,
  });
  if (!response.ok || !response.body) throw new ApiError(response.status, "Não foi possível enviar a mensagem.");
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
