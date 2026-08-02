// Deterministic evidence verification. A quote is valid iff it is an exact substring of the
// chunk, OR a whitespace-normalized equivalent that still maps to real offsets in the chunk.
// No model involvement. Independently testable.

export interface QuoteVerification {
  verified: boolean;
  startOffset: number;
  endOffset: number;
  normalized: boolean;
}

export function verifyQuote(chunkText: string, quote: string): QuoteVerification {
  const trimmed = quote.trim();
  if (!trimmed) return { verified: false, startOffset: -1, endOffset: -1, normalized: false };

  const exact = chunkText.indexOf(trimmed);
  if (exact >= 0) {
    return { verified: true, startOffset: exact, endOffset: exact + trimmed.length, normalized: false };
  }

  // Whitespace-insensitive match with real offsets into the original chunk.
  const pattern = escapeRegex(trimmed).replace(/\s+/g, "\\s+");
  const re = new RegExp(pattern);
  const m = re.exec(chunkText);
  if (m && m.index >= 0) {
    return { verified: true, startOffset: m.index, endOffset: m.index + m[0].length, normalized: true };
  }
  return { verified: false, startOffset: -1, endOffset: -1, normalized: false };
}

export function offsetsValid(chunkText: string, start: number, end: number): boolean {
  return start >= 0 && end > start && end <= chunkText.length;
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
