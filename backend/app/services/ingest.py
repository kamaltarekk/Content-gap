"""Ingestion orchestration (spec §9.2): source → immutable snapshot → content pieces →
verbatim evidence spans → duplicate grouping. Deterministic; no AI. Small files are parsed
inline here; Phase 4 moves long parsing/crawling to Celery jobs.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.storage import Storage
from app.core.text import content_hash, detect_language, normalize_for_hash, sha256_bytes, sha256_text
from app.db.models.content_piece import ContentPiece, EvidenceSpan
from app.db.models.source import Source, SourceSnapshot
from app.parsers import ParsedDocument, parse_file
from app.parsers.base import ParsedDocument as _PD  # noqa: F401


@dataclass
class IngestResult:
    source_id: uuid.UUID
    snapshot_id: uuid.UUID
    content_piece_ids: list[uuid.UUID]
    extraction_quality: str
    warnings: list[str]


_QUALITY_TO_STATUS = {
    "complete": "completed",
    "partial": "completed_with_warnings",
    "low_quality": "completed_with_warnings",
    "unreadable": "completed_with_warnings",
    "blocked": "completed_with_warnings",
    "unknown": "completed_with_warnings",
}


async def _create_source(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    entity_id: uuid.UUID | None,
    source_type: str,
    source_category: str,
    display_name: str,
    original_url: str | None,
    original_filename: str | None,
    user_id: uuid.UUID | None,
) -> Source:
    source = Source(
        project_id=project_id,
        entity_id=entity_id,
        source_type=source_type,
        source_category=source_category,
        display_name=display_name,
        original_url=original_url,
        original_filename=original_filename,
        created_by=user_id,
    )
    session.add(source)
    await session.flush()
    return source


async def _create_snapshot(
    session: AsyncSession,
    storage: Storage,
    *,
    source: Source,
    raw_bytes: bytes,
    parsed: ParsedDocument,
    mime: str | None,
) -> SourceSnapshot:
    raw_hash = sha256_bytes(raw_bytes)
    raw_key = f"{source.project_id}/{source.id}/raw-{raw_hash[:16]}"
    text_key = f"{source.project_id}/{source.id}/text-{raw_hash[:16]}.txt"
    storage.put(raw_key, raw_bytes)
    storage.put(text_key, parsed.text.encode("utf-8"))

    snap = SourceSnapshot(
        source_id=source.id,
        snapshot_number=1,
        mime_type=mime,
        byte_size=len(raw_bytes),
        raw_sha256=raw_hash,
        normalized_text_sha256=sha256_text(normalize_for_hash(parsed.text)),
        raw_object_key=raw_key,
        extracted_text_object_key=text_key,
        parser_name=parsed.parser_name,
        parser_version=parsed.parser_version,
        extraction_quality=parsed.extraction_quality,
        status=_QUALITY_TO_STATUS.get(parsed.extraction_quality, "completed_with_warnings"),
        warnings=parsed.warnings,
        snapshot_metadata=parsed.metadata,
    )
    session.add(snap)
    await session.flush()
    return snap


async def _assign_duplicate(session: AsyncSession, project_id: uuid.UUID, piece: ContentPiece) -> None:
    existing = (
        await session.execute(
            select(ContentPiece)
            .where(
                ContentPiece.project_id == project_id,
                ContentPiece.content_hash == piece.content_hash,
                ContentPiece.is_canonical.is_(True),
            )
            .order_by(ContentPiece.created_at)
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing is not None and existing.id != piece.id:
        group = existing.duplicate_group_id or existing.id
        existing.duplicate_group_id = group
        existing.duplicate_count += 1
        piece.duplicate_group_id = group
        piece.is_canonical = False


async def _create_piece(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    entity_id: uuid.UUID | None,
    snapshot_id: uuid.UUID,
    content_format: str,
    text: str,
    title: str | None,
    location: dict,
    external_id: str | None = None,
) -> ContentPiece:
    piece = ContentPiece(
        project_id=project_id,
        entity_id=entity_id,
        source_snapshot_id=snapshot_id,
        external_id=external_id,
        content_format=content_format,
        title=title,
        original_text=text,
        normalized_text=normalize_for_hash(text),
        language_code=detect_language(text),
        original_location=location,
        content_hash=content_hash(text),
    )
    session.add(piece)
    await session.flush()
    await _assign_duplicate(session, project_id, piece)
    # A verbatim full-text evidence span so every piece is traceable to its snapshot/location.
    session.add(
        EvidenceSpan(
            content_piece_id=piece.id,
            span_type="full_text",
            start_offset=0,
            end_offset=len(text),
            quoted_text=text,
            source_location={"source_snapshot_id": str(snapshot_id), **location},
            language_code=piece.language_code,
            created_by_origin="deterministic",
        )
    )
    return piece


async def ingest_manual_text(
    session: AsyncSession,
    storage: Storage,
    *,
    project_id: uuid.UUID,
    entity_id: uuid.UUID | None,
    source_category: str,
    display_name: str,
    text: str,
    content_format: str,
    user_id: uuid.UUID | None,
) -> IngestResult:
    parsed = ParsedDocument(text=text, title=display_name, parser_name="manual", parser_version="1")
    source = await _create_source(
        session,
        project_id=project_id,
        entity_id=entity_id,
        source_type="manual_text",
        source_category=source_category,
        display_name=display_name,
        original_url=None,
        original_filename=None,
        user_id=user_id,
    )
    snap = await _create_snapshot(
        session, storage, source=source, raw_bytes=text.encode("utf-8"), parsed=parsed, mime="text/plain"
    )
    piece = await _create_piece(
        session,
        project_id=project_id,
        entity_id=entity_id,
        snapshot_id=snap.id,
        content_format=content_format,
        text=text,
        title=display_name,
        location={"kind": "manual_text"},
    )
    return IngestResult(source.id, snap.id, [piece.id], parsed.extraction_quality, parsed.warnings)


async def ingest_file(
    session: AsyncSession,
    storage: Storage,
    *,
    project_id: uuid.UUID,
    entity_id: uuid.UUID | None,
    source_category: str,
    filename: str,
    mime: str | None,
    data: bytes,
    content_format: str,
    user_id: uuid.UUID | None,
) -> IngestResult:
    parsed = parse_file(data, filename=filename, mime=mime)
    source = await _create_source(
        session,
        project_id=project_id,
        entity_id=entity_id,
        source_type="file",
        source_category=source_category,
        display_name=filename,
        original_url=None,
        original_filename=filename,
        user_id=user_id,
    )
    snap = await _create_snapshot(session, storage, source=source, raw_bytes=data, parsed=parsed, mime=mime)
    piece_ids: list[uuid.UUID] = []
    if parsed.text.strip():
        piece = await _create_piece(
            session,
            project_id=project_id,
            entity_id=entity_id,
            snapshot_id=snap.id,
            content_format=content_format,
            text=parsed.text,
            title=parsed.title,
            location={"kind": "file", "filename": filename},
        )
        piece_ids.append(piece.id)
    return IngestResult(source.id, snap.id, piece_ids, parsed.extraction_quality, parsed.warnings)


async def ingest_csv(
    session: AsyncSession,
    storage: Storage,
    *,
    project_id: uuid.UUID,
    entity_id: uuid.UUID | None,
    source_category: str,
    filename: str,
    data: bytes,
    text_column: str,
    content_format: str,
    user_id: uuid.UUID | None,
    external_id_column: str | None = None,
) -> IngestResult:
    from app.parsers import parse_csv

    parsed = parse_csv(data, filename)
    source = await _create_source(
        session,
        project_id=project_id,
        entity_id=entity_id,
        source_type="csv_import",
        source_category=source_category,
        display_name=filename,
        original_url=None,
        original_filename=filename,
        user_id=user_id,
    )
    snap = await _create_snapshot(session, storage, source=source, raw_bytes=data, parsed=parsed, mime="text/csv")
    piece_ids: list[uuid.UUID] = []
    for i, row in enumerate(parsed.records or []):
        text = row.get(text_column, "")
        if not text.strip():
            continue
        piece = await _create_piece(
            session,
            project_id=project_id,
            entity_id=entity_id,
            snapshot_id=snap.id,
            content_format=content_format,
            text=text,
            title=None,
            location={"kind": "csv_row", "row": i},
            external_id=row.get(external_id_column) if external_id_column else None,
        )
        piece_ids.append(piece.id)
    return IngestResult(source.id, snap.id, piece_ids, parsed.extraction_quality, parsed.warnings)
