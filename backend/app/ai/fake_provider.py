"""Deterministic offline AI provider. Same input -> same output. It pattern-matches text and
NEVER follows instructions embedded in source content (those are only reported). Used for the
local demo and all tests, so the pipeline runs with no API key."""

from __future__ import annotations

import re
from typing import Any

from app.ai.provider import AIRequest, AIResponse, TokenCount
from app.core.text import detect_language

name = "fake"

# Bilingual keyword lexicons (Arabic + English). Value -> substrings.
_JOURNEY = {
    "evaluation": ["compare", "vs", "worth it", "pricing", "مقارنة", "يستاهل", "السعر", "أفضل"],
    "decision": ["buy now", "order", "purchase", "اطلب", "اشترِ", "احجز"],
    "exploration": ["what is", "how", "guide", "ما هو", "كيف", "دليل", "لماذا"],
    "experience": ["setup", "install", "onboarding", "الإعداد", "التركيب"],
}
_BOTTLENECK = {
    "persuasion": ["proof", "guarantee", "case study", "results", "دليل", "ضمان", "نتائج", "دراسة حالة"],
    "friction": ["installation", "delivery", "return", "التركيب", "التوصيل", "الاسترجاع"],
    "desire": ["want", "need", "dream", "عايز", "نحتاج", "أتمنى"],
    "attention": ["watch", "see", "new", "شاهد", "جديد"],
}
_SALES_ELEMENT = {
    "claim_proof": ["case study", "results", "proof", "دراسة حالة", "نتائج", "دليل"],
    "logistics": ["installation", "delivery", "included", "التركيب", "التوصيل", "يشمل"],
    "social_proof": ["testimonial", "review", "customers", "شهادة", "تقييم", "عملاء"],
    "offer": ["order", "buy", "subscribe", "اطلب", "اشترك", "احجز"],
    "comparison": ["vs", "compared", "cheaper than", "مقارنة", "أرخص من"],
    "fear_free": ["guarantee", "refund", "risk free", "ضمان", "استرجاع"],
    "claim": ["best", "number one", "الأفضل", "الأول"],
}

_INJECTION = [
    re.compile(r"ignore (all |the )?(previous|prior|above) instructions", re.I),
    re.compile(r"reveal (your|the) (prompt|instructions|api key)", re.I),
    re.compile(r"you are now", re.I),
    re.compile(r"system prompt", re.I),
    re.compile(r"تجاهل (كل )?التعليمات", re.I),
    re.compile(r"أنت الآن", re.I),
]


def _detect_injection(text: str) -> list[str]:
    return [m.group(0)[:120] for rx in _INJECTION if (m := rx.search(text))]


def _match(text: str, lexicon: dict[str, list[str]]) -> tuple[str | None, str]:
    lower = text.lower()
    for value, terms in lexicon.items():
        for t in terms:
            if t.lower() in lower:
                return value, "high"
    return None, "low"


class FakeAIProvider:
    name = "fake"
    model = "fake-deterministic-v0"

    def count_tokens(self, request: AIRequest) -> TokenCount:
        text = str(request.payload.get("text", ""))
        return TokenCount(input_tokens=max(1, len(text) // 4 + 200), output_tokens=120)

    async def structured_generate(self, request: AIRequest, idempotency_key: str) -> AIResponse:
        payload = request.payload
        text: str = payload["text"]
        evidence_ids: list[str] = payload["evidence_ids"]
        cpid: str = payload["content_piece_id"]
        suspicious = _detect_injection(text)  # reported, never obeyed

        def dim(lexicon: dict[str, list[str]], fallback: str) -> dict[str, Any]:
            value, conf = _match(text, lexicon)
            return {
                "value": value or fallback,
                "confidence": "high" if value else "low",
                "evidence_ids": evidence_ids[:1],
                "reasoning": "keyword match" if value else "no strong signal",
            }

        classifications = {
            "journey_stage": dim(_JOURNEY, "unknown"),
            "primary_bottleneck": dim(_BOTTLENECK, "unknown"),
            "primary_sales_element": dim(_SALES_ELEMENT, "claim"),
        }
        # A weak/low-confidence dimension flags the piece for human review.
        needs_review = any(c["confidence"] != "high" for c in classifications.values())

        raw = {
            "schema_name": "ContentPieceClassificationResult",
            "content_piece_id": cpid,
            "language": payload.get("language") or detect_language(text),
            "classifications": classifications,
            "customer_question": None,
            "claims": [],
            "cta": None,
            "target_decision_alignment": None,
            "needs_review": needs_review,
            "review_reasons": ["low_confidence_dimension"] if needs_review else [],
        }
        return AIResponse(raw=raw, usage=self.count_tokens(request), suspicious_instructions=suspicious)
