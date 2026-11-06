export interface VerseText {
  n: number;
  text: string;
  cited: boolean;
}

export interface Passage {
  reference: string;
  book: string;
  book_id: number;
  chapter: number;
  verse_start: number | null;
  verse_end: number | null;
  requested_translation: string;
  translation: string;
  fallback_label: string | null;
  verses: VerseText[];
}

export type IssueKind =
  | "referencia_inexistente"
  | "citacao_nao_confere"
  | "interpretacao_contradiz"
  | "teologia_prosperidade"
  | "teologia_investimento"
  | "teologia_condenacao";

export type Segment =
  | { type: "text"; text: string }
  | { type: "verse"; marker: string; passage: Passage }
  | { type: "invalid_reference"; marker: string }
  | { type: "issue"; kind: IssueKind; excerpt: string; marker?: string }
  | { type: "crisis"; numero: string; url: string }
  | { type: "memory"; topic: string };

export type ChatEvent =
  | { event: "text"; data: { text: string } }
  | { event: "verse"; data: { marker: string; passage: Passage } }
  | { event: "invalid_reference"; data: { marker: string } }
  | { event: "status"; data: { label: string } }
  | { event: "memory_saved"; data: { topic: string } }
  | { event: "crisis"; data: { numero: string; url: string } }
  | { event: "triage"; data: { moment: string; distress: number } }
  | { event: "issues"; data: { items: { kind: IssueKind; excerpt: string; marker?: string }[] } }
  | { event: "done"; data: { message_id: number } }
  | { event: "error"; data: { code: string; message: string } };

export interface ConversationSummary {
  id: string;
  title: string;
  updated_at: string;
}

export interface StoredMessage {
  role: "user" | "assistant";
  text: string | null;
  segments: Segment[] | null;
  created_at: string;
}

export interface MemoryItem {
  topic: string;
  content: string;
  updated_at: string;
}

export interface CompareItem {
  translation: string;
  name: string;
  verses: VerseText[] | null;
  note: string | null;
}

export interface OriginalWord {
  verse: number;
  position: number;
  surface: string;
  transliteration: string;
  gloss_en: string;
  strong: string;
  morphology: string;
  language: "heb" | "arc" | "grc";
  lemma: string | null;
  lexicon_gloss: string | null;
}

export interface CrossRef {
  reference: string;
  votes: number;
}
