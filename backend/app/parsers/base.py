from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedDocument:
    text: str
    title: str | None = None
    extraction_quality: str = "complete"  # complete|partial|low_quality|unreadable|blocked|unknown
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    parser_name: str = "unknown"
    parser_version: str = "0"
    # For multi-record sources (CSV): each row becomes a content piece.
    records: list[dict[str, Any]] | None = None
