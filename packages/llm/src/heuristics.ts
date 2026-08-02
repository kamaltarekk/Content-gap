import type { JourneyStage, Language, SignalType } from "@cgi/shared";

// Deterministic, language-agnostic heuristics. Bilingual (Arabic + English) lexicons.
// These power the FAKE provider and some real-provider pre-checks. They only READ text —
// they never interpret it as an instruction.

export function detectLanguage(text: string): Language {
  const arabic = (text.match(/[؀-ۿ]/g) ?? []).length;
  const latin = (text.match(/[A-Za-z]/g) ?? []).length;
  if (arabic === 0 && latin === 0) return "unknown";
  if (arabic > 0 && latin > 0) {
    const ratio = arabic / (arabic + latin);
    if (ratio > 0.15 && ratio < 0.85) return "mixed";
    return ratio >= 0.85 ? "ar" : "en";
  }
  return arabic > 0 ? "ar" : "en";
}

interface Lexicon {
  type: SignalType;
  terms: string[];
}

// Ordered so more specific types win. Terms are lowercased substrings (Arabic + English).
const SIGNAL_LEXICONS: Lexicon[] = [
  {
    type: "OBJECTION",
    terms: [
      "too expensive",
      "expensive",
      "price",
      "cost too much",
      "afford",
      "غالي",
      "غالية",
      "سعر",
      "التكلفة",
      "مش قادر",
      "complicated",
      "too complex",
      "hard to",
      "معقد",
      "صعب",
      "risky",
      "risk",
      "مخاطرة",
    ],
  },
  {
    type: "PROOF",
    terms: [
      "case study",
      "results",
      "we helped",
      "increased by",
      "roi",
      "testimonial",
      "before and after",
      "دراسة حالة",
      "نتائج",
      "زادت",
      "حققنا",
      "دليل",
      "step by step",
      "خطوة بخطوة",
    ],
  },
  {
    type: "DESIRED_OUTCOME",
    terms: ["i want", "we need", "goal is", "hoping to", "نريد", "عايز", "نحتاج", "هدفنا", "أتمنى"],
  },
  {
    type: "DECISION_CRITERION",
    terms: ["must have", "requirement", "we need it to", "criteria", "لازم", "شرط", "متطلب", "معيار"],
  },
  {
    type: "PAIN",
    terms: ["struggle", "frustrat", "waste", "problem", "pain", "مشكلة", "معاناة", "بنضيع", "تعب"],
  },
  {
    type: "CTA",
    terms: ["book a call", "sign up", "get started", "contact us", "احجز", "سجل", "تواصل", "ابدأ الآن"],
  },
  {
    type: "CLAIM",
    terms: ["the best", "guaranteed", "#1", "number one", "الأفضل", "مضمون", "الأول"],
  },
  {
    type: "ALTERNATIVE",
    terms: ["instead of", "compared to", "vs", "alternative", "بدلا من", "مقارنة", "البديل"],
  },
];

export function detectSignals(text: string): { type: SignalType; term: string }[] {
  const lower = text.toLowerCase();
  const hits: { type: SignalType; term: string }[] = [];
  for (const lex of SIGNAL_LEXICONS) {
    for (const term of lex.terms) {
      if (lower.includes(term)) {
        hits.push({ type: lex.type, term });
        break; // one hit per type per chunk keeps output bounded
      }
    }
  }
  // A question mark (either script) implies a QUESTION signal.
  if (/[?؟]/.test(text)) hits.push({ type: "QUESTION", term: "?" });
  return hits;
}

const STAGE_LEXICON: { stage: JourneyStage; terms: string[] }[] = [
  { stage: "TRIGGER", terms: ["just realized", "suddenly", "started noticing", "بدأت ألاحظ", "فجأة"] },
  { stage: "EXPLORE", terms: ["how do i", "what is", "learn about", "guide", "ما هو", "كيف", "دليل"] },
  { stage: "EVALUATE", terms: ["compare", "vs", "review", "is it worth", "pricing", "مقارنة", "تقييم", "يستاهل"] },
  { stage: "DECIDE", terms: ["ready to buy", "sign the", "purchase", "book", "جاهز", "أشتري", "احجز"] },
  { stage: "EXPERIENCE", terms: ["onboarding", "getting started", "setup", "التفعيل", "البداية"] },
  { stage: "REPEAT", terms: ["renew", "again", "loyal", "التجديد", "مرة أخرى"] },
];

export function detectJourneyStage(text: string): JourneyStage {
  const lower = text.toLowerCase();
  for (const s of STAGE_LEXICON) {
    for (const term of s.terms) if (lower.includes(term)) return s.stage;
  }
  if (/[?؟]/.test(text)) return "EXPLORE";
  return "UNKNOWN";
}

/** Best-matching cohort id for a text, by counting keyword hits. Ties broken by input order. */
export function matchCohort(text: string, cohorts: { id: string; keywords: string[] }[]): string | null {
  const lower = text.toLowerCase();
  let best: { id: string; score: number } | null = null;
  for (const c of cohorts) {
    let score = 0;
    for (const kw of c.keywords) {
      if (kw && lower.includes(kw.toLowerCase())) score++;
    }
    if (score > 0 && (!best || score > best.score)) best = { id: c.id, score };
  }
  return best?.id ?? null;
}

// Phrases that look like attempts to instruct the model, embedded in source content.
const INJECTION_PATTERNS: RegExp[] = [
  /ignore (all |the )?(previous|prior|above) instructions/i,
  /disregard (your|the) (system|previous) prompt/i,
  /you are now/i,
  /system prompt/i,
  /reveal (your|the) (prompt|instructions|api key)/i,
  /assistant\s*:/i,
  /<\/?(system|instruction|admin)>/i,
  /act as (?:an?|the) /i,
  /تجاهل (كل )?التعليمات/i,
  /أنت الآن/i,
];

export function detectInjection(text: string): string[] {
  const found: string[] = [];
  for (const re of INJECTION_PATTERNS) {
    const m = re.exec(text);
    if (m) found.push(m[0].slice(0, 120));
  }
  return found;
}
