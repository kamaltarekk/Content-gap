from __future__ import annotations

import io

from app.parsers.base import ParsedDocument


def parse_pdf(data: bytes, filename: str | None = None) -> ParsedDocument:
    """Embedded-text-first PDF extraction. OCR is NOT performed (spec §6.15): pages with no
    embedded text are reported as image-only rather than silently returning empty text.
    Partial extraction is surfaced as `completed_with_warnings` via `partial` quality + notes.
    """
    from pypdf import PdfReader

    warnings: list[str] = []
    page_texts: list[str] = []
    image_only_pages: list[int] = []
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001
        return ParsedDocument(
            text="",
            extraction_quality="unreadable",
            warnings=[f"pdf_open_failed:{type(exc).__name__}"],
            parser_name="pypdf",
            parser_version="1",
            title=filename,
        )

    for i, page in enumerate(reader.pages):
        try:
            txt = page.extract_text() or ""
        except Exception:  # noqa: BLE001
            txt = ""
        if txt.strip():
            page_texts.append(txt)
        else:
            image_only_pages.append(i + 1)

    page_count = len(reader.pages)
    if image_only_pages:
        warnings.append(f"image_only_or_empty_pages:{image_only_pages}")
    full = "\n\n".join(page_texts)

    if not full.strip():
        quality = "unreadable"  # nothing extractable — must NOT be reported as complete success
    elif image_only_pages:
        quality = "partial"
    else:
        quality = "complete"

    return ParsedDocument(
        text=full,
        title=filename,
        extraction_quality=quality,
        warnings=warnings,
        metadata={"page_count": page_count, "text_pages": len(page_texts), "image_only_pages": image_only_pages},
        parser_name="pypdf",
        parser_version="1",
    )
