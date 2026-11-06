import type { OutlineItem } from "@/lib/print";

export function Contents({ items }: { items: OutlineItem[] }) {
  if (items.length === 0) return null;
  return (
    <nav className="sumario" aria-label="Sumário">
      <h2>Sumário</h2>
      <ol>
        {items.map((item) => (
          <li key={item.id} className={item.level === 1 ? "nivel-1" : "nivel-2"}>
            <a href={`#${item.id}`}>{item.title}</a>
          </li>
        ))}
      </ol>
    </nav>
  );
}
