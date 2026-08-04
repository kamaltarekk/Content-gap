from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.clients.storage import Storage, get_storage
from app.core.audit import write_audit
from app.core.config import Settings, get_settings
from app.core.enums import ContentFormat, SourceCategory
from app.db.models.content_piece import ContentPiece, EvidenceSpan
from app.db.models.project import Project
from app.db.models.source import Source, SourceSnapshot
from app.db.models.user import User
from app.db.session import get_session
from app.parsers import UnsupportedFileType, parse_csv, resolve_extension
from app.services import ingest

router = APIRouter(tags=["sources"])


def storage_dep(settings: Settings = Depends(get_settings)) -> Storage:
    return get_storage(settings)


async def _require_project(session: AsyncSession, project_id: uuid.UUID) -> Project:
    p = await session.get(Project, project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="project_not_found")
    return p


def _result(r: ingest.IngestResult) -> dict:
    return {
        "source_id": str(r.source_id),
        "snapshot_id": str(r.snapshot_id),
        "content_piece_ids": [str(i) for i in r.content_piece_ids],
        "content_piece_count": len(r.content_piece_ids),
        "extraction_quality": r.extraction_quality,
        "warnings": r.warnings,
    }


class ManualSourceIn(BaseModel):
    entity_id: uuid.UUID | None = None
    source_category: SourceCategory
    display_name: str = Field(min_length=1, max_length=500)
    text: str = Field(min_length=1)
    content_format: ContentFormat = ContentFormat.other


@router.post("/api/v1/projects/{project_id}/sources/manual", status_code=201)
async def create_manual_source(
    project_id: uuid.UUID,
    body: ManualSourceIn,
    session: AsyncSession = Depends(get_session),
    storage: Storage = Depends(storage_dep),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> dict:
    await _require_project(session, project_id)
    if len(body.text) > settings.max_manual_text_chars:
        raise HTTPException(status_code=422, detail="manual_text_too_long")
    r = await ingest.ingest_manual_text(
        session,
        storage,
        project_id=project_id,
        entity_id=body.entity_id,
        source_category=body.source_category.value,
        display_name=body.display_name,
        text=body.text,
        content_format=body.content_format.value,
        user_id=user.id,
    )
    await write_audit(
        session,
        action="ingest_manual",
        object_type="source",
        object_id=str(r.source_id),
        project_id=project_id,
        user_id=user.id,
    )
    await session.commit()
    return _result(r)


@router.post("/api/v1/projects/{project_id}/sources/upload", status_code=201)
async def upload_source(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    source_category: str = Form(...),
    content_format: str = Form("article"),
    entity_id: str | None = Form(None),
    session: AsyncSession = Depends(get_session),
    storage: Storage = Depends(storage_dep),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> dict:
    await _require_project(session, project_id)
    if source_category not in {c.value for c in SourceCategory}:
        raise HTTPException(status_code=422, detail="invalid_source_category")
    data = await file.read()
    if len(data) > settings.max_file_bytes:
        raise HTTPException(status_code=422, detail="file_too_large")
    try:
        resolve_extension(file.filename, file.content_type)
    except UnsupportedFileType as exc:
        raise HTTPException(status_code=422, detail="unsupported_file_type") from exc
    r = await ingest.ingest_file(
        session,
        storage,
        project_id=project_id,
        entity_id=uuid.UUID(entity_id) if entity_id else None,
        source_category=source_category,
        filename=file.filename or "upload",
        mime=file.content_type,
        data=data,
        content_format=content_format,
        user_id=user.id,
    )
    await write_audit(
        session,
        action="ingest_file",
        object_type="source",
        object_id=str(r.source_id),
        project_id=project_id,
        user_id=user.id,
    )
    await session.commit()
    return _result(r)


@router.post("/api/v1/projects/{project_id}/sources/csv/preview")
async def csv_preview(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    await _require_project(session, project_id)
    data = await file.read()
    parsed = parse_csv(data, file.filename)
    return {
        "headers": parsed.metadata.get("headers", []),
        "row_count": parsed.metadata.get("row_count", 0),
        "sample": (parsed.records or [])[:5],
    }


@router.post("/api/v1/projects/{project_id}/sources/csv/import", status_code=201)
async def csv_import(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    text_column: str = Form(...),
    source_category: str = Form(...),
    content_format: str = Form("social_post"),
    entity_id: str | None = Form(None),
    external_id_column: str | None = Form(None),
    session: AsyncSession = Depends(get_session),
    storage: Storage = Depends(storage_dep),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> dict:
    await _require_project(session, project_id)
    data = await file.read()
    if len(data) > settings.max_file_bytes:
        raise HTTPException(status_code=422, detail="file_too_large")
    r = await ingest.ingest_csv(
        session,
        storage,
        project_id=project_id,
        entity_id=uuid.UUID(entity_id) if entity_id else None,
        source_category=source_category,
        filename=file.filename or "import.csv",
        data=data,
        text_column=text_column,
        content_format=content_format,
        user_id=user.id,
        external_id_column=external_id_column,
    )
    await write_audit(
        session,
        action="ingest_csv",
        object_type="source",
        object_id=str(r.source_id),
        project_id=project_id,
        user_id=user.id,
        metadata={"pieces": len(r.content_piece_ids)},
    )
    await session.commit()
    return _result(r)


@router.get("/api/v1/projects/{project_id}/sources")
async def list_sources(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (
        (
            await session.execute(
                select(Source)
                .where(Source.project_id == project_id, Source.deleted_at.is_(None))
                .order_by(Source.created_at)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": str(s.id),
            "source_type": s.source_type,
            "source_category": s.source_category,
            "display_name": s.display_name,
            "original_url": s.original_url,
        }
        for s in rows
    ]


@router.get("/api/v1/sources/{source_id}")
async def get_source(source_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    s = await session.get(Source, source_id)
    if s is None:
        raise HTTPException(status_code=404, detail="source_not_found")
    snaps = (await session.execute(select(SourceSnapshot).where(SourceSnapshot.source_id == source_id))).scalars().all()
    return {
        "id": str(s.id),
        "source_type": s.source_type,
        "source_category": s.source_category,
        "display_name": s.display_name,
        "snapshots": [
            {
                "id": str(sn.id),
                "snapshot_number": sn.snapshot_number,
                "extraction_quality": sn.extraction_quality,
                "status": sn.status,
                "warnings": sn.warnings,
                "raw_sha256": sn.raw_sha256,
                "raw_object_key": sn.raw_object_key,
                "extracted_text_object_key": sn.extracted_text_object_key,
                "metadata": sn.snapshot_metadata,
            }
            for sn in snaps
        ],
    }


def _piece_out(p: ContentPiece) -> dict:
    return {
        "id": str(p.id),
        "project_id": str(p.project_id),
        "entity_id": str(p.entity_id) if p.entity_id else None,
        "source_snapshot_id": str(p.source_snapshot_id),
        "content_format": p.content_format,
        "language_code": p.language_code,
        "title": p.title,
        "original_text": p.original_text,
        "normalized_text": p.normalized_text,
        "content_hash": p.content_hash,
        "duplicate_group_id": str(p.duplicate_group_id) if p.duplicate_group_id else None,
        "is_canonical": p.is_canonical,
        "include_in_analysis": p.include_in_analysis,
    }


@router.get("/api/v1/projects/{project_id}/content")
async def list_content(
    project_id: uuid.UUID,
    duplicate_status: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    stmt = select(ContentPiece).where(ContentPiece.project_id == project_id).order_by(ContentPiece.created_at)
    rows = (await session.execute(stmt)).scalars().all()
    if duplicate_status == "canonical":
        rows = [r for r in rows if r.is_canonical]
    elif duplicate_status == "duplicate":
        rows = [r for r in rows if not r.is_canonical]
    return [_piece_out(p) for p in rows]


@router.get("/api/v1/content/{content_piece_id}")
async def get_content(content_piece_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    p = await session.get(ContentPiece, content_piece_id)
    if p is None:
        raise HTTPException(status_code=404, detail="content_piece_not_found")
    return _piece_out(p)


@router.get("/api/v1/content/{content_piece_id}/evidence")
async def list_evidence(content_piece_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (
        (await session.execute(select(EvidenceSpan).where(EvidenceSpan.content_piece_id == content_piece_id)))
        .scalars()
        .all()
    )
    return [
        {
            "id": str(e.id),
            "span_type": e.span_type,
            "quoted_text": e.quoted_text,
            "start_offset": e.start_offset,
            "end_offset": e.end_offset,
            "language_code": e.language_code,
            "created_by_origin": e.created_by_origin,
            "source_location": e.source_location,
        }
        for e in rows
    ]


@router.get("/api/v1/evidence/{evidence_id}/source-context")
async def evidence_source_context(evidence_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    e = await session.get(EvidenceSpan, evidence_id)
    if e is None:
        raise HTTPException(status_code=404, detail="evidence_not_found")
    piece = await session.get(ContentPiece, e.content_piece_id)
    if piece is None:
        raise HTTPException(status_code=404, detail="content_piece_not_found")
    snap = await session.get(SourceSnapshot, piece.source_snapshot_id)
    start = max(0, (e.start_offset or 0) - 80)
    end = min(len(piece.original_text), (e.end_offset or len(piece.original_text)) + 80)
    return {
        "evidence_id": str(e.id),
        "content_piece_id": str(piece.id),
        "source_snapshot_id": str(piece.source_snapshot_id),
        "source_id": str(snap.source_id) if snap else None,
        "quoted_text": e.quoted_text,
        "surrounding_text": piece.original_text[start:end],
        "source_location": e.source_location,
    }


@router.get("/api/v1/projects/{project_id}/duplicates")
async def list_duplicates(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (
        (
            await session.execute(
                select(ContentPiece).where(
                    ContentPiece.project_id == project_id, ContentPiece.duplicate_group_id.is_not(None)
                )
            )
        )
        .scalars()
        .all()
    )
    groups: dict[str, list[ContentPiece]] = {}
    for p in rows:
        groups.setdefault(str(p.duplicate_group_id), []).append(p)
    return [
        {
            "duplicate_group_id": gid,
            "members": [{"id": str(p.id), "is_canonical": p.is_canonical, "title": p.title} for p in members],
        }
        for gid, members in groups.items()
    ]
