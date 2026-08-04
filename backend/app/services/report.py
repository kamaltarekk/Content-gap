"""Final diagnostic report assembly, strategy-readiness gate, and exports (spec §12.13, §21 Gate 7).

A report is an **immutable snapshot**: it freezes the brand diagnosis, competitor diagnoses, the
comparative matrix, the gap register, root causes, evidence quality, a research backlog, the
strategy-readiness decision, and a full version manifest at generation time. Adding data later
creates a NEW report; prior reports stay byte-for-byte reproducible (spec §6.2).

The readiness decision is one of the four approved statuses (§21 Gate 7). The report is a
diagnosis — it never emits a content strategy or calendar; unknown opportunities become research
backlog items (§17.6, §19.3).
"""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import UTC, datetime
from html import escape

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.content_piece import ContentPiece, EvidenceSpan
from app.db.models.context import DiagnosticContextVersion
from app.db.models.entity import Entity
from app.db.models.report import Report
from app.services import brand_diagnosis, competitor, gap_engine

COMPETITOR_BANNER = competitor.LIMITATION_BANNER
PROMPT_VERSIONS = {"content_piece_classification": "v1"}


class ReportError(Exception):
    pass


# --- Strategy-readiness decision (Gate 7) ------------------------------------------------------


def decide_readiness(gaps: list[dict], has_approved_context: bool) -> tuple[str, str, list[dict]]:
    """Return (status, plain-language reason, unresolved_items) — one of the four §21 statuses."""
    unresolved: list[dict] = []
    non_content = [g for g in gaps if g["gap_type"] == "non_content_gap"]
    criticals = [g for g in gaps if g["severity"] == "critical"]
    high = [g for g in gaps if g["severity"] in ("critical", "high")]
    insufficient = [g for g in high if g["confidence"] == "insufficient_evidence"]
    unconfirmed_criticals = [g for g in criticals if g["gap_status"] != "confirmed"]
    open_candidates = [g for g in gaps if g["gap_status"] in ("candidate", "probable")]

    for g in unconfirmed_criticals:
        unresolved.append(
            {"gap_id": g["id"], "territory": g["territory"], "reason": "critical gap awaits human decision"}
        )
    for g in open_candidates:
        unresolved.append(
            {"gap_id": g["id"], "territory": g["territory"], "reason": f"{g['gap_status']} gap not yet resolved"}
        )

    if non_content:
        return (
            "blocked_by_non_content_issue",
            "One or more non-content blockers must change (business/product/operations/sales) before "
            "content can credibly address the problem.",
            [{"gap_id": g["id"], "territory": g["territory"], "reason": "non-content blocker"} for g in non_content],
        )
    if not has_approved_context:
        return (
            "more_evidence_required",
            "The diagnostic context is not approved yet, so a final readiness decision cannot be made.",
            unresolved,
        )
    if insufficient:
        return (
            "more_evidence_required",
            "Critical or high-priority gaps do not yet have sufficient evidence to support a reliable "
            "conclusion. Collect more evidence before proceeding.",
            unresolved,
        )
    if unconfirmed_criticals or open_candidates:
        return (
            "ready_with_unresolved_hypotheses",
            "The evidence base is adequate, but some gaps remain unconfirmed hypotheses that need human "
            "review before they become confirmed.",
            unresolved,
        )
    return (
        "ready_for_content_strategy",
        "Every critical gap has a decision link, bottleneck link, evidence, separate severity and "
        "confidence, an alternative explanation, a root cause, and a human decision.",
        [],
    )


# --- Assembly ----------------------------------------------------------------------------------


async def generate_report(session: AsyncSession, project_id: uuid.UUID) -> Report:
    settings = get_settings()
    entities = (await session.execute(select(Entity).where(Entity.project_id == project_id))).scalars().all()
    brand = next((e for e in entities if e.entity_type == "brand"), None)
    if brand is None:
        raise ReportError("no_primary_brand_entity")
    competitors = [e for e in entities if e.entity_type == "competitor"]

    bd = await brand_diagnosis.run_brand_diagnosis(session, project_id)
    brand_payload = await brand_diagnosis.get_diagnosis_payload(session, bd.id)

    competitor_payloads: list[dict] = []
    for c in competitors:
        cd = await competitor.run_competitor_diagnosis(session, project_id, c.id)
        competitor_payloads.append(await competitor.get_diagnosis_payload(session, cd.id))

    gap_run = await gap_engine.run_gap_analysis(session, project_id)
    gap_payload = await gap_engine.get_run_payload(session, gap_run.id)
    gaps = gap_payload["gaps"]

    context = (
        await session.execute(
            select(DiagnosticContextVersion)
            .where(DiagnosticContextVersion.project_id == project_id)
            .order_by(DiagnosticContextVersion.version_number.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    has_approved_context = context is not None and context.status == "approved"

    readiness_status, readiness_reason, unresolved = decide_readiness(gaps, has_approved_context)

    critical_high = [g for g in gaps if g["severity"] in ("critical", "high")]
    non_content_blockers = [g for g in gaps if g["gap_type"] == "non_content_gap"]

    # Research backlog: unresolved candidates and competitor leaks become questions to investigate —
    # never an automatic content calendar (spec §17.6, §19.3).
    research_backlog = [
        {
            "territory": g["territory"],
            "gap_type": g["gap_type"],
            "question": f"Validate '{g['territory']}': confirm need relevance, brand capability, and a proof path.",
        }
        for g in gaps
        if g["gap_status"] in ("candidate", "probable") or g["gap_type"] == "competitor_leak_opportunity"
    ]

    piece_count = (
        (
            await session.execute(
                select(ContentPiece).where(ContentPiece.project_id == project_id, ContentPiece.is_canonical.is_(True))
            )
        )
        .scalars()
        .all()
    )
    span_count = len(
        (
            await session.execute(
                select(EvidenceSpan.id)
                .join(ContentPiece, EvidenceSpan.content_piece_id == ContentPiece.id)
                .where(ContentPiece.project_id == project_id)
            )
        ).all()
    )

    executive = (
        f"Diagnosed the brand against {len(competitors)} competitor(s). Detected {len(gaps)} gap(s) "
        f"({sum(1 for g in gaps if g['severity'] == 'critical')} critical, "
        f"{sum(1 for g in gaps if g['severity'] == 'high')} high). "
        f"Strategy-readiness: {readiness_status}."
    )

    version_manifest = {
        "context_version_id": str(context.id) if context else None,
        "context_version_number": context.version_number if context else None,
        "context_status": context.status if context else None,
        "rule_version": gap_engine.RULE_VERSION,
        "ai_provider": settings.ai_provider,
        "ai_model": settings.anthropic_model,
        "prompt_versions": PROMPT_VERSIONS,
        "dataset": {
            "content_pieces": len(piece_count),
            "evidence_spans": span_count,
            "entities": len(entities),
            "competitors": len(competitors),
        },
        "generated_at": datetime.now(UTC).isoformat(),
    }

    snapshot = {
        "project_id": str(project_id),
        "executive_diagnosis": executive,
        "scope_and_limitations": {
            "brand": brand_payload["limitations"],
            "competitor_banner": COMPETITOR_BANNER,
        },
        "brand_diagnosis": brand_payload,
        "competitor_diagnoses": competitor_payloads,
        "comparative_matrix": gap_payload["matrix"],
        "gaps": gaps,
        "critical_and_high_gaps": critical_high,
        "root_causes": [
            {"territory": g["territory"], "gap_type": g["gap_type"], "root_cause_type": g["root_cause_type"]}
            for g in gaps
        ],
        "non_content_blockers": non_content_blockers,
        "evidence_quality": {
            "brand_content_pieces": len(piece_count),
            "evidence_spans": span_count,
            "competitor_samples": [
                {
                    "entity_id": p["entity_id"],
                    "sample_sufficiency": p["sample_sufficiency"],
                    "sample_piece_count": p["sample_piece_count"],
                }
                for p in competitor_payloads
            ],
        },
        "research_backlog": research_backlog,
        "readiness_decision": {
            "status": readiness_status,
            "reason": readiness_reason,
            "unresolved_items": unresolved,
        },
        "version_manifest": version_manifest,
    }

    report = Report(
        project_id=project_id,
        status="draft",
        readiness_status=readiness_status,
        readiness_reason=readiness_reason,
        snapshot=snapshot,
        version_manifest=version_manifest,
    )
    session.add(report)
    await session.flush()
    return report


async def approve_report(session: AsyncSession, report: Report, user_id: uuid.UUID | None) -> Report:
    report.status = "approved"
    report.approved_by = user_id
    report.approved_at = datetime.now(UTC)
    return report


def report_out(report: Report) -> dict:
    return {
        "id": str(report.id),
        "project_id": str(report.project_id),
        "status": report.status,
        "readiness_status": report.readiness_status,
        "readiness_reason": report.readiness_reason,
        "snapshot": report.snapshot,
        "version_manifest": report.version_manifest,
    }


# --- Exports -----------------------------------------------------------------------------------


def export_json(report: Report) -> str:
    return json.dumps(report.snapshot, ensure_ascii=False, indent=2)


def export_csv(report: Report) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "territory",
            "gap_type",
            "gap_status",
            "severity",
            "severity_score",
            "confidence",
            "confidence_score",
            "root_cause_type",
        ]
    )
    for g in report.snapshot.get("gaps", []):
        writer.writerow(
            [
                g["territory"],
                g["gap_type"],
                g["gap_status"],
                g["severity"],
                g["severity_score"],
                g["confidence"],
                g["confidence_score"],
                g["root_cause_type"],
            ]
        )
    return buf.getvalue()


def export_print_html(report: Report) -> str:
    """A print-ready (browser-print-to-PDF) Arabic-first RTL document. No external assets."""
    s = report.snapshot
    rd = s["readiness_decision"]
    vm = s["version_manifest"]
    rows = "".join(
        f"<tr><td>{escape(g['territory'])}</td><td>{escape(g['gap_type'])}</td>"
        f"<td>{escape(g['gap_status'])}</td><td>{escape(g['severity'])}</td>"
        f"<td>{escape(g['confidence'])}</td><td>{escape(g['root_cause_type'])}</td></tr>"
        for g in s.get("critical_and_high_gaps", [])
    )
    brand_lim = escape(s["scope_and_limitations"]["brand"])
    comp_banner = escape(s["scope_and_limitations"]["competitor_banner"])
    head_cells = ["المجال", "النوع", "الحالة", "الخطورة", "الثقة", "السبب الجذري"]
    header = "".join(f"<th>{c}</th>" for c in head_cells)
    return f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>التقرير التشخيصي النهائي</title>
<style>
  @media print {{ body {{ margin: 1cm; }} .no-print {{ display: none; }} }}
  body {{ font-family: system-ui, sans-serif; direction: rtl; text-align: right; line-height: 1.6; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #999; padding: 6px; text-align: right; }}
  .banner {{ background: #fff3cd; padding: 8px; border-radius: 4px; }}
</style>
</head>
<body>
  <h1>التقرير التشخيصي النهائي</h1>
  <h2>الملخص التنفيذي — Executive diagnosis</h2>
  <p>{escape(s["executive_diagnosis"])}</p>
  <h2>نطاق التحليل وحدوده — Scope &amp; limitations</h2>
  <p>{brand_lim}</p>
  <p class="banner">{comp_banner}</p>
  <h2>قرار جاهزية الاستراتيجية — Strategy readiness</h2>
  <p><strong>{escape(rd["status"])}</strong>: {escape(rd["reason"])}</p>
  <h2>الفجوات الحرجة وعالية الأولوية — Critical &amp; high-priority gaps</h2>
  <table>
    <thead><tr>{header}</tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <h2>سجل الإصدارات — Version manifest</h2>
  <p>rule_version: {escape(str(vm["rule_version"]))} · context: {escape(str(vm["context_version_number"]))} ·
     model: {escape(str(vm["ai_model"]))} · pieces: {escape(str(vm["dataset"]["content_pieces"]))}</p>
</body>
</html>"""
