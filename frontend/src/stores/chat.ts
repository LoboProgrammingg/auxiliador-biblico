import { create } from "zustand";
import { effortFor, requestModes } from "@/lib/modes";
import { type ChatOptions, DEFAULT_OPTIONS, loadOptions, saveOptions } from "@/lib/chatOptions";
import { applyEvent, needsReattach } from "@/lib/segments";
import { api, attachStream, sendMessage } from "@/services/api";
import type { ChatEvent, DailyWord, MessageStatus, Segment, StoredMessage } from "@/types/api";

export interface UiMessage {
  key: string;
  role: "user" | "assistant";
  text?: string;
  segments: Segment[];
  status?: MessageStatus;
  error?: string;
}

export interface PopupTarget {
  reference: string;
  translation: string;
}

export type DailyState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; word: DailyWord }
  | { status: "error"; message: string };

interface ChatState {
  daily: DailyState;
  loadDailyWord: () => Promise<void>;
  closeDailyWord: () => void;
  conversationId: string | null;
  messages: UiMessage[];
  loading: boolean;
  streaming: boolean;
  status: string | null;
  popup: PopupTarget | null;
  select: (id: string | null) => Promise<void>;
  send: (text: string) => Promise<void>;
  openPopup: (target: PopupTarget | null) => void;
  focus: boolean;
  toggleFocus: () => void;
  options: ChatOptions;
  restoreOptions: () => void;
  setOptions: (patch: Partial<ChatOptions>) => void;
  studyPlan: boolean;
  setStudyPlan: (on: boolean) => void;
  tiktokVideo: boolean;
  setTiktokVideo: (on: boolean) => void;
  complexMode: boolean;
  setComplexMode: (on: boolean) => void;
}

let counter = 0;
const key = () => `m${++counter}`;

function fromStored(m: StoredMessage): UiMessage {
  return { key: key(), role: m.role, text: m.text ?? undefined, segments: m.segments ?? [], status: m.status };
}

let controller: AbortController | null = null;
const DROPPED = "A conexão com o servidor caiu. Confira se a API está rodando (scripts/api.sh).";

export const useChat = create<ChatState>((set, get) => ({
  conversationId: null,
  messages: [],
  loading: false,
  streaming: false,
  status: null,
  popup: null,
  daily: { status: "idle" },

  loadDailyWord: async () => {
    if (get().daily.status === "loading") return;
    set({ daily: { status: "loading" } });
    try {
      set({ daily: { status: "ready", word: await api.dailyWord() } });
    } catch (e) {
      const message = e instanceof Error && e.message ? e.message : "Não consegui preparar a palavra de hoje.";
      set({ daily: { status: "error", message } });
    }
  },

  closeDailyWord: () => set({ daily: { status: "idle" } }),

  select: async (id) => {
    controller?.abort();
    set({ conversationId: id, messages: [], status: null, streaming: false, loading: id !== null });
    if (!id) return;
    try {
      const stored = await api.messages(id);
      if (get().conversationId !== id) return;
      if (!needsReattach(stored)) {
        set({ messages: stored.map(fromStored), loading: false });
        return;
      }
      set({ messages: stored.slice(0, -1).map(fromStored), loading: false });
      await follow(id, (signal) => attachStream(id, signal));
      if (get().conversationId === id && !get().streaming) {
        const fresh = await api.messages(id);
        if (get().conversationId === id) set({ messages: fresh.map(fromStored) });
      }
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
    set((s) => ({ messages: [...s.messages, { key: key(), role: "user", text, segments: [] }] }));
    const target = id;
    const modes = requestModes({ plan: get().studyPlan, video: get().tiktokVideo, complex: get().complexMode });
    const options = { ...get().options, ...modes, effort: effortFor(get().options.effort, modes) };
    set({ studyPlan: false, tiktokVideo: false, complexMode: false });
    await follow(target, (signal) => sendMessage(target, text, options, signal));
  },

  openPopup: (target) => set({ popup: target }),
  focus: false,
  toggleFocus: () => set((s) => ({ focus: !s.focus })),
  options: DEFAULT_OPTIONS,
  restoreOptions: () => set({ options: loadOptions() }),
  setOptions: (patch) => {
    const options = { ...get().options, ...patch };
    saveOptions(options);
    set({ options });
  },
  studyPlan: false,
  setStudyPlan: (on) => set({ studyPlan: on }),
  tiktokVideo: false,
  setTiktokVideo: (on) => set({ tiktokVideo: on }),
  complexMode: false,
  setComplexMode: (on) => set({ complexMode: on }),
}));

/** Acompanha uma resposta (nova ou retomada); se a tela trocar de conversa, só para de assistir. */
async function follow(id: string, open: (signal: AbortSignal) => AsyncGenerator<ChatEvent>): Promise<void> {
  const own = new AbortController();
  controller = own;
  const reply: UiMessage = { key: key(), role: "assistant", segments: [], status: "gerando" };
  useChat.setState((s) => ({ messages: [...s.messages, reply], streaming: true, status: "Pensando…" }));
  const update = (fn: (m: UiMessage) => UiMessage) =>
    useChat.setState((s) => ({ messages: s.messages.map((m) => (m.key === reply.key ? fn(m) : m)) }));
  let received = 0;
  try {
    for await (const ev of open(own.signal)) {
      received += 1;
      if (ev.event === "status") useChat.setState({ status: ev.data.label });
      else update((m) => ({ ...m, segments: applyEvent(m.segments, ev) }));
      if (ev.event === "text" || ev.event === "verse" || ev.event === "error") useChat.setState({ status: null });
      if (ev.event === "done") update((m) => ({ ...m, status: "ok" }));
    }
    if (received === 0) useChat.setState((s) => ({ messages: s.messages.filter((m) => m.key !== reply.key) }));
  } catch {
    if (!own.signal.aborted) update((m) => ({ ...m, error: DROPPED }));
  } finally {
    if (controller === own) {
      controller = null;
      if (useChat.getState().conversationId === id) useChat.setState({ streaming: false, status: null });
    }
  }
}
