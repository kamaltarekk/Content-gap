"""PII detection + redaction preview (spec §25.4).

MVP scope: detect emails and phone numbers in CSV/manual text and offer a redaction preview before
upload. Arabic-Indic digits are handled alongside Latin digits. This is a heuristic preview to warn
users — not a guarantee — and it never sends unnecessary fields to the AI provider.
"""

from __future__ import annotations

import re

UPLOAD_WARNING = (
    "This text may contain customer PII (names, phone numbers, emails, conversation text). "
    "Review the redaction preview before uploading, and only upload data you are authorized to use."
)

_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# Phone: 7+ digits, allowing +, spaces, dashes, parentheses, and Arabic-Indic digits.
_ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d\s\-()]{6,}\d|[" + _ARABIC_DIGITS + r"][" + _ARABIC_DIGITS + r"\s\-()]{6,})")

EMAIL_MASK = "[REDACTED_EMAIL]"
PHONE_MASK = "[REDACTED_PHONE]"


def redact(text: str) -> tuple[str, dict[str, int]]:
    """Return (redacted_text, counts). Emails first, then phone numbers."""
    emails = _EMAIL.findall(text)
    redacted = _EMAIL.sub(EMAIL_MASK, text)
    phones = _PHONE.findall(redacted)
    redacted = _PHONE.sub(PHONE_MASK, redacted)
    return redacted, {"emails": len(emails), "phones": len(phones)}


def redaction_preview(text: str, max_chars: int = 5000) -> dict:
    sample = text[:max_chars]
    redacted, counts = redact(sample)
    return {
        "found": counts,
        "has_pii": counts["emails"] > 0 or counts["phones"] > 0,
        "warning": UPLOAD_WARNING,
        "preview": redacted,
        "truncated": len(text) > max_chars,
    }
