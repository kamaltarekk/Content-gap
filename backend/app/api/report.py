from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.models.report import Report
from app.db.models.user import User
from app.db.session import get_session
from app.services import report as report_service

router = APIRouter(tags=["reports"])


@router.post("/api/v1/projects/{project_id}/reports", status_code=201)
async def generate(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        report = await report_service.generate_report(session, project_id)
    except report_service.ReportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    out = report_service.report_out(report)
    await session.commit()
    return out


@router.get("/api/v1/projects/{project_id}/reports")
async def list_reports(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (
        (
            await session.execute(
                select(Report).where(Report.project_id == project_id).order_by(Report.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": str(r.id),
            "status": r.status,
            "readiness_status": r.readiness_status,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


async def _get(session: AsyncSession, report_id: uuid.UUID) -> Report:
    report = await session.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report_not_found")
    return report


@router.get("/api/v1/reports/{report_id}")
async def get_report(report_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return report_service.report_out(await _get(session, report_id))


@router.post("/api/v1/reports/{report_id}/approve")
async def approve(
    report_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    report = await _get(session, report_id)
    await report_service.approve_report(session, report, user.id)
    await session.commit()
    return report_service.report_out(report)


@router.get("/api/v1/reports/{report_id}/export/{fmt}")
async def export(report_id: uuid.UUID, fmt: str, session: AsyncSession = Depends(get_session)) -> Response:
    report = await _get(session, report_id)
    if fmt == "json":
        return Response(report_service.export_json(report), media_type="application/json")
    if fmt == "csv":
        return Response(report_service.export_csv(report), media_type="text/csv")
    if fmt in ("html", "pdf", "print"):
        return Response(report_service.export_print_html(report), media_type="text/html; charset=utf-8")
    raise HTTPException(status_code=400, detail="unsupported_format")
