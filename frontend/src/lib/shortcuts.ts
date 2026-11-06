export type Shortcut = "nova" | "buscar" | "compor" | "foco";

interface KeyLike {
  key: string;
  ctrlKey: boolean;
  metaKey: boolean;
  altKey: boolean;
  shiftKey: boolean;
  target: unknown;
}

const typing = (target: unknown) => {
  const t = target as { tagName?: string; isContentEditable?: boolean } | null;
  return !!t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable === true);
};

/** Ctrl/⌘+K nova conversa · Ctrl/⌘+J ir para versículo · Alt+F modo foco · / escrever (fora de campos). */
export function matchShortcut(e: KeyLike): Shortcut | null {
  const mod = e.ctrlKey || e.metaKey;
  const k = e.key.toLowerCase();
  if (mod && !e.altKey && k === "k") return "nova";
  if (mod && !e.altKey && k === "j") return "buscar";
  if (e.altKey && !mod && k === "f") return "foco";
  if (!mod && !e.altKey && e.key === "/" && !typing(e.target)) return "compor";
  return null;
}

export const SHORTCUT_HELP: [string, string][] = [
  ["Ctrl+K", "nova conversa"],
  ["Ctrl+J", "ir para um versículo"],
  ["/", "escrever mensagem"],
  ["Alt+F", "modo foco"],
  ["Esc", "fechar a passagem aberta"],
];
