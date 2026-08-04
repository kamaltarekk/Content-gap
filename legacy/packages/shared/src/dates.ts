// Deterministic date parsing. Returns an ISO date (yyyy-mm-dd) or null. No locale guessing
// beyond a small set of explicit, unambiguous formats.

export function parseDateOrNull(input: string | null | undefined): string | null {
  if (!input) return null;
  const raw = input.trim();
  if (!raw) return null;

  // ISO 8601 (date or datetime).
  const iso = /^(\d{4})-(\d{2})-(\d{2})(?:[T ].*)?$/.exec(raw);
  if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`;

  // yyyy/mm/dd
  const slash = /^(\d{4})\/(\d{1,2})\/(\d{1,2})$/.exec(raw);
  if (slash) return pad(slash[1]!, slash[2]!, slash[3]!);

  // dd-mm-yyyy or dd/mm/yyyy (day first, unambiguous only when day > 12 or explicit)
  const dmy = /^(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})$/.exec(raw);
  if (dmy) {
    const a = Number(dmy[1]);
    const b = Number(dmy[2]);
    // If first > 12 it must be the day; otherwise assume ISO-ish is unavailable and treat as dd-mm.
    if (a > 12 && b <= 12) return pad(dmy[3]!, String(b), String(a));
    if (b > 12 && a <= 12) return pad(dmy[3]!, String(a), String(b)); // mm-dd
    return pad(dmy[3]!, String(b), String(a)); // default day-first
  }

  return null;
}

function pad(y: string, m: string, d: string): string | null {
  const mm = m.padStart(2, "0");
  const dd = d.padStart(2, "0");
  const monthNum = Number(mm);
  const dayNum = Number(dd);
  if (monthNum < 1 || monthNum > 12 || dayNum < 1 || dayNum > 31) return null;
  return `${y}-${mm}-${dd}`;
}

/** Whether an ISO date is older than `days` relative to a supplied reference (deterministic; no Date.now()). */
export function isOlderThan(isoDate: string | null, days: number, referenceIso: string): boolean {
  if (!isoDate) return false;
  const then = Date.parse(`${isoDate}T00:00:00Z`);
  const ref = Date.parse(`${referenceIso}T00:00:00Z`);
  if (Number.isNaN(then) || Number.isNaN(ref)) return false;
  return ref - then > days * 86_400_000;
}
