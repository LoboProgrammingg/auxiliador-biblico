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

export interface TimelineSection {
  start: number;
  end: number;
  title: string;
}

export interface MapPlace {
  name: string;
  kind: string;
  lon: number;
  lat: number;
  verses: number[];
}

export interface ChiasmPart {
  label: string;
  start: number;
  end: number;
  title: string;
}

export type Segment =
  | { type: "text"; text: string }
  | { type: "timeline"; marker: string; reference: string; book: string; sections: TimelineSection[] }
  | { type: "map"; marker: string; reference: string; places: MapPlace[] }
  | { type: "chiasm"; marker: string; reference: string; book: string; parts: ChiasmPart[] }
  | { type: "verse"; marker: string; passage: Passage }
  | { type: "invalid_reference"; marker: string }
  | { type: "issue"; kind: IssueKind; excerpt: string; marker?: string }
  | { type: "crisis"; numero: string; url: string }
  | { type: "memory"; topic: string }
  | { type: "error"; code: string; message: string };

export type ChatEvent =
  | { event: "text"; data: { text: string } }
  | { event: "verse"; data: { marker: string; passage: Passage } }
  | { event: "invalid_reference"; data: { marker: string } }
  | { event: "timeline"; data: { marker: string; reference: string; book: string; sections: TimelineSection[] } }
  | { event: "map"; data: { marker: string; reference: string; places: MapPlace[] } }
  | { event: "chiasm"; data: { marker: string; reference: string; book: string; parts: ChiasmPart[] } }
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

export type MessageStatus = "ok" | "gerando" | "erro" | "interrompida";

export interface StoredMessage {
  role: "user" | "assistant";
  text: string | null;
  segments: Segment[] | null;
  status: MessageStatus;
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

export interface DailyWord {
  day: string;
  reference: string | null;
  segments: Segment[];
}

export interface Prayer {
  id: string;
  title: string;
  details: string | null;
  status: "aberto" | "respondido";
  answer_note: string | null;
  created_at: string;
  answered_at: string | null;
}

export interface VerseNote {
  id: number;
  reference: string;
  content: string;
  updated_at: string;
}

export interface DailyWordItem {
  day: string;
  reference: string | null;
  conversation_id: string;
}

export interface PlanCatalogItem {
  code: string;
  name: string;
  description: string;
  days: number;
}

export interface PlanSummary {
  id: string;
  code: string;
  name: string;
  description: string;
  started_on: string;
  today_day: number;
  total: number;
  done: number;
}

export interface PlanDay {
  day: number;
  readings: string[];
  done: boolean;
}

export interface PlanDetail extends PlanSummary {
  days: PlanDay[];
}
