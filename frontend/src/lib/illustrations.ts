export interface ChiasmRow {
  label: string;
  depth: number;
  pair: number | null;
}

export function chiasmRows(labels: string[]): ChiasmRow[] {
  const n = labels.length;
  return labels.map((label, i) => {
    const mirror = n - 1 - i;
    return { label, depth: Math.min(i, mirror), pair: mirror === i ? null : mirror };
  });
}
