/** Parse a comma- or newline-separated string into a trimmed, non-empty list. */
export function parseList(raw: string): string[] {
  return raw
    .split(/[\n,]/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

export function formatUsd(n: number | undefined): string {
  if (n === undefined || Number.isNaN(n)) return "—";
  return `$${n.toFixed(4)}`;
}

export function pct(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  // Accept either a 0-1 ratio or already a percentage.
  const value = n <= 1 ? n * 100 : n;
  return `${value.toFixed(1)}%`;
}
