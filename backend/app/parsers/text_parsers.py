from __future__ import annotations

import re

from app.parsers.base import ParsedDocument


def parse_txt(data: bytes, filename: str | None = None) -> ParsedDocument:
    # utf-8-sig strips a BOM if present without corrupting content.
    text = data.decode("utf-8-sig", errors="replace")
    quality = "complete" if text.strip() else "unreadable"
    warnings = [] if text.strip() else ["empty_file"]
    return ParsedDocument(
        text=text, title=filename, extraction_quality=quality, warnings=warnings, parser_name="txt", parser_version="1"
    )


def parse_markdown(data: bytes, filename: str | None = None) -> ParsedDocument:
    text = data.decode("utf-8-sig", errors="replace")
    heading = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    title = heading.group(1).strip() if heading else filename
    quality = "complete" if text.strip() else "unreadable"
    return ParsedDocument(
        text=text, title=title, extraction_quality=quality, parser_name="markdown", parser_version="1"
    )
