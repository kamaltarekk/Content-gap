"""Deterministic text helpers: hashing, normalization (for dedup/search), language detection.

The ORIGINAL text is never mutated (spec §6.13). Normalization produces a SEPARATE form used only
for hashing and duplicate grouping — it does not replace Arabic letters, and the verbatim quote is
always preserved elsewhere.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

_WS = re.compile(r"\s+")


def normalize_for_hash(text: str) -> str:
    """NFKC + collapse whitespace + strip. Preserves letters/digits/punctuation (incl. Arabic)."""
    norm = unicodedata.normalize("NFKC", text)
    norm = norm.replace("‏", "").replace("‎", "").replace("﻿", "")  # bidi/BOM marks
    norm = _WS.sub(" ", norm).strip()
    return norm


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_hash(text: str) -> str:
    """Hash of the normalized text — two reposts with only whitespace differences match."""
    return sha256_text(normalize_for_hash(text))


def detect_language(text: str) -> str:
    arabic = len(re.findall(r"[؀-ۿ]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if arabic == 0 and latin == 0:
        return "unknown"
    if arabic > 0 and latin > 0:
        ratio = arabic / (arabic + latin)
        if 0.15 < ratio < 0.85:
            return "ar_en_mixed"
        return "ar" if ratio >= 0.85 else "en"
    return "ar" if arabic > 0 else "en"
