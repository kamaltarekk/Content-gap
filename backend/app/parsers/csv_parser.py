from __future__ import annotations

import csv
import io

from app.parsers.base import ParsedDocument


def parse_csv(data: bytes, filename: str | None = None) -> ParsedDocument:
    """Parse CSV into records. Handles UTF-8 and UTF-8-BOM and Arabic headers. Does not guess
    semantic columns — the import endpoint maps columns explicitly (spec §6.18)."""
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    headers = [h.strip() for h in (reader.fieldnames or [])]
    records: list[dict[str, str]] = []
    for row in reader:
        records.append({(k.strip() if k else k): (v or "").strip() for k, v in row.items()})
    quality = "complete" if records else "low_quality"
    warnings = [] if records else ["no_rows"]
    return ParsedDocument(
        text=text,
        title=filename,
        extraction_quality=quality,
        warnings=warnings,
        metadata={"headers": headers, "row_count": len(records)},
        parser_name="csv",
        parser_version="1",
        records=records,
    )
