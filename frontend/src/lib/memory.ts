import type { MemoryItem } from "@/types/api";

export function topicTitle(topic: string): string {
  const words = topic.replaceAll("-", " ").trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function sortMemories(items: MemoryItem[]): MemoryItem[] {
  return [...items].sort((a, b) => b.updated_at.localeCompare(a.updated_at));
}
