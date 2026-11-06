import { create } from "zustand";
import { applyEvent } from "@/lib/segments";
import { api, sendMessage } from "@/services/api";
import type { Segment, StoredMessage } from "@/types/api";

export interface UiMessage {
  key: string;
  role: "user" | "assistant";
  text?: string;
  segments: Segment[];
  error?: string;
}

export interface PopupTarget {
  reference: string;
  translation: string;
}

interface ChatState {
  conversationId: string | null;
  messages: UiMessage[];
  loading: boolean;
  streaming: boolean;
  status: string | null;
  popup: PopupTarget | null;
  select: (id: string | null) => Promise<void>;
  send: (text: string) => Promise<void>;
  openPopup: (target: PopupTarget | null) => void;
}

let counter = 0;
const key = () => `m${++counter}`;

function fromStored(m: StoredMessage): UiMessage {
  return { key: key(), role: m.role, text: m.text ?? undefined, segments: m.segments ?? [] };
}

export const useChat = create<ChatState>((set, get) => ({
  conversationId: null,
  messages: [],
  loading: false,
  streaming: false,
  status: null,
  popup: null,

  select: async (id) => {
    if (get().streaming) return;
    set({ conversationId: id, messages: [], status: null, loading: id !== null });
    if (!id) return;
    try {
      const stored = await api.messages(id);
      if (get().conversationId === id) set({ messages: stored.map(fromStored), loading: false });
    } catch {
      set({ loading: false, messages: [], conversationId: null });
    }
  },

  send: async (text) => {
    if (get().streaming || !text.trim()) return;
    let id = get().conversationId;
    if (!id) {
      id = (await api.createConversation()).id;
      set({ conversationId: id });
    }
    const reply: UiMessage = { key: key(), role: "assistant", segments: [] };
    set((s) => ({
      messages: [...s.messages, { key: key(), role: "user", text, segments: [] }, reply],
      streaming: true,
      status: "Pensando…",
    }));
    const update = (fn: (m: UiMessage) => UiMessage) =>
      set((s) => ({ messages: s.messages.map((m) => (m.key === reply.key ? fn(m) : m)) }));
    try {
      for await (const ev of sendMessage(id, text, new AbortController().signal)) {
        if (ev.event === "status") set({ status: ev.data.label });
        else if (ev.event === "error") update((m) => ({ ...m, error: ev.data.message }));
        else update((m) => ({ ...m, segments: applyEvent(m.segments, ev) }));
        if (ev.event === "text" || ev.event === "verse") set({ status: null });
      }
    } catch {
      update((m) => ({ ...m, error: "A conexão com o servidor caiu. Confira se a API está rodando (scripts/api.sh)." }));
    } finally {
      set({ streaming: false, status: null });
    }
  },

  openPopup: (target) => set({ popup: target }),
}));
