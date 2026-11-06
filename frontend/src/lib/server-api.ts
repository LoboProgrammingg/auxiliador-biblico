const BASE = process.env.API_URL_INTERNAL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

/** Busca na API durante a renderização no servidor (páginas de impressão); 404 vira null. */
export async function fetchApi<T>(path: string): Promise<T | null> {
  const response = await fetch(`${BASE}/api/v1${path}`, { cache: "no-store" });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`API respondeu ${response.status} em ${path}`);
  return (await response.json()) as T;
}

export const query = (params: Record<string, string | number>) =>
  new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString();
