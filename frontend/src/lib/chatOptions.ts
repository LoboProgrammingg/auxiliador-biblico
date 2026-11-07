export const MODELS = [
  { id: "claude-sonnet-5-5", label: "Sonnet 5.5" },
  { id: "claude-opus-5-5", label: "Opus 5.5" },
] as const;

export const EFFORTS = [
  { id: "medium", label: "Médio" },
  { id: "high", label: "Alto" },
  { id: "xhigh", label: "Extra alto" },
] as const;

export type ModelId = (typeof MODELS)[number]["id"];
export type EffortId = (typeof EFFORTS)[number]["id"];

export interface ChatOptions {
  model: ModelId;
  effort: EffortId;
  brief: boolean;
}

export const DEFAULT_OPTIONS: ChatOptions = { model: "claude-sonnet-5-5", effort: "medium", brief: false };
const STORAGE_KEY = "auxiliador.opcoes";

const isModel = (v: unknown): v is ModelId => MODELS.some((m) => m.id === v);
const isEffort = (v: unknown): v is EffortId => EFFORTS.some((e) => e.id === v);

/** Lê a escolha salva; qualquer valor desconhecido volta ao padrão. */
export function parseOptions(raw: string | null): ChatOptions {
  try {
    const data: unknown = raw ? JSON.parse(raw) : null;
    if (typeof data !== "object" || data === null) return DEFAULT_OPTIONS;
    const { model, effort, brief } = data as Record<string, unknown>;
    if (!isModel(model) || !isEffort(effort) || typeof brief !== "boolean") return DEFAULT_OPTIONS;
    return { model, effort, brief };
  } catch {
    return DEFAULT_OPTIONS;
  }
}

export function loadOptions(): ChatOptions {
  try {
    return parseOptions(window.localStorage.getItem(STORAGE_KEY));
  } catch {
    return DEFAULT_OPTIONS;
  }
}

export function saveOptions(options: ChatOptions): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(options));
  } catch {
    // sem armazenamento (aba privada): a escolha vale só nesta tela
  }
}
