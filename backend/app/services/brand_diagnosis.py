"""Brand diagnosis engine (spec §14, §16.5).

Deterministic and evidence-driven: every score and finding is computed from data already in the
database (content classifications, claims/proof, performance records, Voice of Customer) and is
traceable to real evidence spans. Two hard rules from the spec are enforced here:

* Severity and confidence are always separate and never collapsed (§4.19).
* The engine describes what the evidence shows — it never emits strategy or recommendations.
  Absence of coverage is reported as "no evidence in the analyzed sample", never proof of absence.

Readiness dimensions that genuinely require operational input (author/expert access, production
capacity) are reported with ``insufficient_evidence`` rather than inferred from public posting
behavior (§14.1).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SalesElement
from app.db.models.brand_diagnosis import BrandDiagnosis, BrandFinding, BrandReadinessScore
from app.db.models.classification import ContentClassification
from app.db.models.content_piece import ContentPiece, EvidenceSpan
from app.db.models.context import DiagnosticContextVersion
from app.db.models.entity import Entity
from app.db.models.voc import Claim, ClaimEvidence, PerformanceRecord, VocEntry

COVERAGE_PER_PIECE = 2  # each covering piece adds this many points, capped at 10 (spec §16.5 scale)

# Sales elements grouped by the bottleneck they most influence. Groups follow spec §14.5
# (Core / Trust / Intellectual / Instinct) mapped onto the four bottlenecks (§8). When the project
# bottleneck is unknown, every element is treated as relevant.
BOTTLENECK_ELEMENTS: dict[str, list[str]] = {
    "attention": ["trigger", "claim", "gain"],
    "desire": ["gain", "offer", "scarcity", "urgency", "reciprocity"],
    "persuasion": [
        "identity",
        "authority",
        "social_proof",
        "claim_proof",
        "fear_free",
        "objection_handler",
        "comparison",
        "calculation",
        "reason",
    ],
    "friction": ["logistics", "fear_free", "offer"],
}

# v0 keyword seed for detecting problems content cannot fix (spec §17.7). A match makes the issue a
# *candidate* non-content blocker; human review confirms it. Bilingual (Arabic + English).
NON_CONTENT_KEYWORDS: tuple[str, ...] = (
    "delivery",
    "shipping",
    "shipment",
    "late",
    "refund",
    "return",
    "out of stock",
    "stock",
    "expensive",
    "price",
    "cost",
    "broken",
    "defect",
    "crash",
    "bug",
    "slow",
    "توصيل",
    "شحن",
    "تأخير",
    "متأخر",
    "استرجاع",
    "استرداد",
    "مخزون",
    "نفذ",
    "سعر",
    "غالي",
    "تكلفة",
    "عطل",
    "بطيء",
    "يتعطل",
)

# Metric-name → performance signal category (spec §14.7). Unknown proxy metrics fall back to
# visible_public_proxy; direct commercial outcomes are detected via the record's is_proxy flag.
_SIGNAL_BY_METRIC: dict[str, str] = {
    "views": "attention",
    "impressions": "attention",
    "reach": "attention",
    "watch_time": "attention",
    "likes": "desire",
    "saves": "desire",
    "shares": "desire",
    "followers": "desire",
    "comments": "persuasion",
    "engagement": "persuasion",
}


def element_coverage_score(covering_pieces: int) -> int:
    """Coverage score (0–10) for a sales element or journey stage from the number of aligned brand
    pieces that cover it. Deterministic and capped at 10."""
    return min(10, COVERAGE_PER_PIECE * covering_pieces)


def grade_from_scores(scored: list[tuple[int, str]]) -> str | None:
    """A–D grade from the readiness dimensions that have real evidence. Dimensions marked
    ``insufficient_evidence`` are excluded so operational unknowns never inflate or deflate the
    grade. Returns None when nothing is scorable yet."""
    usable = [score for score, confidence in scored if confidence != "insufficient_evidence"]
    if not usable:
        return None
    avg = sum(usable) / len(usable)
    if avg >= 8:
        return "a"
    if avg >= 6:
        return "b"
    if avg >= 4:
        return "c"
    return "d"


@dataclass
class _Finding:
    dimension: str
    subject: str
    confidence: str
    summary: str
    severity: str | None = None
    finding_status: str = "inference"
    limitations: str | None = None
    is_non_content_blocker: bool = False
    evidence_span_ids: list[str] = field(default_factory=list)


class BrandDiagnosisError(Exception):
    pass


async def _effective(
    session: AsyncSession, project_id: uuid.UUID, dimension: str
) -> dict[uuid.UUID, tuple[str, list[str]]]:
    """Current classification value + evidence ids per content piece for one dimension."""
    rows = (
        (
            await session.execute(
                select(ContentClassification).where(
                    ContentClassification.project_id == project_id,
                    ContentClassification.classification_dimension == dimension,
                    ContentClassification.is_current.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    out: dict[uuid.UUID, tuple[str, list[str]]] = {}
    for r in rows:
        value = r.approved_value or r.proposed_value
        if value is None:
            continue
        ids = [str(x) for x in (r.evidence_ids or [])]
        out[r.content_piece_id] = (value, ids)
    return out


LIMITATIONS_TEXT = (
    "This brand diagnosis is based only on the sources collected and included for analysis. "
    "Absence of coverage means 'no evidence of X in the analyzed sample', not proof of absence. "
    "Severity and confidence are reported separately. Readiness dimensions requiring operational "
    "input (author/expert access, production capacity) are marked insufficient_evidence. "
    "No strategy or recommendations are produced by this diagnosis."
)


async def run_brand_diagnosis(session: AsyncSession, project_id: uuid.UUID) -> BrandDiagnosis:
    brand = (
        await session.execute(
            select(Entity).where(Entity.project_id == project_id, Entity.entity_type == "brand").limit(1)
        )
    ).scalar_one_or_none()
    if brand is None:
        raise BrandDiagnosisError("no_primary_brand_entity")

    competitor_ids = set(
        (
            await session.execute(
                select(Entity.id).where(Entity.project_id == project_id, Entity.entity_type == "competitor")
            )
        )
        .scalars()
        .all()
    )
    context = (
        await session.execute(
            select(DiagnosticContextVersion)
            .where(DiagnosticContextVersion.project_id == project_id)
            .order_by(DiagnosticContextVersion.version_number.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    bottleneck = context.primary_bottleneck if context else "unknown"

    # Brand content pieces (competitor pieces are diagnosed separately in Phase 8).
    piece_rows = (
        (
            await session.execute(
                select(ContentPiece).where(
                    ContentPiece.project_id == project_id,
                    ContentPiece.is_canonical.is_(True),
                    ContentPiece.include_in_analysis.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    pieces = [p for p in piece_rows if p.entity_id not in competitor_ids]
    piece_ids = {p.id for p in pieces}

    # First evidence span per piece (for citing coverage back to a clickable source).
    span_by_piece: dict[uuid.UUID, uuid.UUID] = {}
    if piece_ids:
        for span in (
            (await session.execute(select(EvidenceSpan).where(EvidenceSpan.content_piece_id.in_(piece_ids))))
            .scalars()
            .all()
        ):
            span_by_piece.setdefault(span.content_piece_id, span.id)

    journey = await _effective(session, project_id, "journey_stage")
    elements = await _effective(session, project_id, "primary_sales_element")

    # Decision alignment: a piece is not aligned when its journey stage is not_applicable
    # (spec §14.2). Not-aligned content is labeled, not penalized, and excluded from coverage.
    not_aligned = {pid for pid, (val, _ids) in journey.items() if val == "not_applicable" and pid in piece_ids}
    aligned_pieces = piece_ids - not_aligned

    findings: list[_Finding] = []

    # --- Sales-element audit (bottleneck-filtered) --------------------------------------------
    relevant = set(BOTTLENECK_ELEMENTS.get(bottleneck, [e.value for e in SalesElement]))
    element_audit: list[dict] = []
    for element in [e.value for e in SalesElement]:
        covering = [pid for pid, (val, _ids) in elements.items() if val == element and pid in aligned_pieces]
        score = element_coverage_score(len(covering))
        ev_ids = [str(span_by_piece[p]) for p in covering if p in span_by_piece]
        is_relevant = element in relevant
        element_audit.append(
            {
                "element": element,
                "coverage_score": score,
                "relevant_to_bottleneck": is_relevant,
                "covering_pieces": len(covering),
                "evidence_span_ids": ev_ids,
            }
        )
        if is_relevant and score < 5:
            findings.append(
                _Finding(
                    dimension="sales_element",
                    subject=element,
                    severity="high" if score == 0 else "medium",
                    confidence="medium" if covering else "low",
                    summary=(
                        f"Sales element '{element}' has weak coverage (score {score}/10) at the "
                        f"'{bottleneck}' bottleneck."
                    ),
                    limitations=None if covering else "No evidence of this element in the analyzed sample.",
                    evidence_span_ids=ev_ids,
                )
            )

    # --- Journey coverage audit ----------------------------------------------------------------
    journey_audit: list[dict] = []
    stage_counts: dict[str, list[uuid.UUID]] = {}
    for pid, (val, _ids) in journey.items():
        if pid in aligned_pieces and val not in ("unknown", "not_applicable"):
            stage_counts.setdefault(val, []).append(pid)
    for stage, covering in stage_counts.items():
        score = element_coverage_score(len(covering))
        journey_audit.append(
            {
                "stage": stage,
                "coverage_score": score,
                "evidence_span_ids": [str(span_by_piece[p]) for p in covering if p in span_by_piece],
            }
        )

    # --- Decision alignment audit --------------------------------------------------------------
    for pid in not_aligned:
        ev = [str(span_by_piece[pid])] if pid in span_by_piece else []
        findings.append(
            _Finding(
                dimension="decision_alignment",
                subject=str(pid),
                severity=None,  # not a defect — labeled, not penalized (spec §14.2)
                confidence="medium",
                summary="Content is not aligned with the current target decision; labeled, not penalized.",
                evidence_span_ids=ev,
            )
        )
    decision_alignment = {
        "aligned": len(aligned_pieces),
        "not_aligned": len(not_aligned),
        "pieces": [
            {
                "content_piece_id": str(pid),
                "label": "not_aligned_with_current_decision" if pid in not_aligned else "aligned",
            }
            for pid in piece_ids
        ],
    }

    # --- Claim–proof integrity -----------------------------------------------------------------
    claims = (await session.execute(select(Claim).where(Claim.project_id == project_id))).scalars().all()
    claim_audit: list[dict] = []
    for claim in claims:
        claim_audit.append(
            {
                "claim_id": str(claim.id),
                "claim_text": claim.claim_text,
                "proof_status": claim.proof_status,
                "finding_status": claim.finding_status,
            }
        )
        ev_ids = [
            str(ce.evidence_span_id)
            for ce in (await session.execute(select(ClaimEvidence).where(ClaimEvidence.claim_id == claim.id)))
            .scalars()
            .all()
        ]
        if claim.proof_status == "unsupported":
            findings.append(
                _Finding(
                    dimension="claim_proof",
                    subject=str(claim.id),
                    severity="high",  # an unproven public claim is a serious integrity risk...
                    confidence="low",  # ...but our confidence is low: no qualifying evidence exists yet
                    finding_status="brand_claim",
                    summary=f"Claim '{claim.claim_text}' is unsupported: no qualifying evidence in the sample.",
                    limitations="Severity reflects risk; confidence reflects the thin evidence base.",
                    evidence_span_ids=ev_ids,
                )
            )
        elif claim.proof_status == "contradicted":
            findings.append(
                _Finding(
                    dimension="claim_proof",
                    subject=str(claim.id),
                    severity="critical",
                    confidence="medium",
                    finding_status="brand_claim",
                    summary=f"Claim '{claim.claim_text}' is contradicted by evidence in the analyzed sample.",
                    evidence_span_ids=ev_ids,
                )
            )

    # --- Performance evidence quality ----------------------------------------------------------
    perf = (
        (await session.execute(select(PerformanceRecord).where(PerformanceRecord.project_id == project_id)))
        .scalars()
        .all()
    )
    signals: list[dict] = []
    has_direct_outcome = False
    for r in perf:
        if not r.is_proxy:
            signal = "direct_commercial_outcome"
            has_direct_outcome = True
        else:
            signal = _SIGNAL_BY_METRIC.get(r.metric_name.strip().lower(), "visible_public_proxy")
        signals.append({"record_id": str(r.id), "metric": r.metric_name, "signal_type": signal, "is_proxy": r.is_proxy})
    if perf and not has_direct_outcome:
        findings.append(
            _Finding(
                dimension="performance_evidence",
                subject="performance",
                severity="medium",
                confidence="medium",
                summary="Only proxy signals are present; conversion cannot be inferred from views or engagement.",
                limitations="No direct commercial-outcome evidence in the analyzed sample (spec §14.7).",
            )
        )

    # --- Non-content blocker detection ---------------------------------------------------------
    voc = (
        (
            await session.execute(
                select(VocEntry).where(
                    VocEntry.project_id == project_id,
                    VocEntry.bank_type.in_(("complaint", "switching_reason")),
                )
            )
        )
        .scalars()
        .all()
    )
    seen_patterns: set[str] = set()
    for entry in voc:
        low = entry.verbatim_phrase.lower()
        hit = next((kw for kw in NON_CONTENT_KEYWORDS if kw in low), None)
        key = entry.pattern_key or entry.verbatim_phrase
        if hit and key not in seen_patterns:
            seen_patterns.add(key)
            findings.append(
                _Finding(
                    dimension="non_content_blocker",
                    subject=hit,
                    severity="high",
                    confidence="medium",
                    finding_status="inference",
                    is_non_content_blocker=True,
                    summary=(
                        "Recurring customer complaint points to a non-content blocker "
                        f"(keyword '{hit}'): content cannot resolve it until the underlying "
                        "business/product/operational condition changes."
                    ),
                    limitations="Candidate blocker from a keyword heuristic; requires human confirmation.",
                    evidence_span_ids=[str(entry.evidence_span_id)],
                )
            )

    # --- Readiness scorecard (0–10 per dimension, shown before the A–D grade) -------------------
    approved_voc = [e for e in await _all_voc(session, project_id) if e.review_status == "approved"]
    supports = (
        (await session.execute(select(ClaimEvidence).where(ClaimEvidence.evidence_role == "supports"))).scalars().all()
    )
    supports = [s for s in supports if any(c.id == s.claim_id for c in claims)]
    story_pieces = [p for p in pieces if p.content_format in ("testimonial", "review", "call_note")]
    commercial_perf = [r for r in perf if not r.is_proxy]

    voc_span = approved_voc[0].evidence_span_id if approved_voc else None
    support_span = supports[0].evidence_span_id if supports else None
    story_span = span_by_piece.get(story_pieces[0].id) if story_pieces else None

    proven = [c for c in claims if c.proof_status in ("proven", "partially_proven")]
    if claims:
        gov_score = round(10 * len(proven) / len(claims))
        gov_conf = "medium" if len(claims) >= 3 else "low"
    else:
        gov_score, gov_conf = 0, "insufficient_evidence"

    readiness_rows: list[BrandReadinessScore] = []
    dims: list[tuple[str, int, str, str, uuid.UUID | None]] = [
        (
            "expert_author_availability",
            0,
            "insufficient_evidence",
            "Requires operational input; not inferable from public content (spec §14.1).",
            None,
        ),
        (
            "evidence_availability",
            element_coverage_score(len(supports)),
            "medium" if supports else "low",
            f"{len(supports)} supporting proof link(s) in the evidence library.",
            support_span,
        ),
        (
            "story_inventory",
            element_coverage_score(len(story_pieces)),
            "medium" if story_pieces else "low",
            f"{len(story_pieces)} story/testimonial/call piece(s) available.",
            story_span,
        ),
        (
            "product_knowledge",
            min(10, len(pieces)),
            "low" if pieces else "insufficient_evidence",
            f"{len(pieces)} brand content piece(s) demonstrating product knowledge.",
            None,
        ),
        (
            "voc_availability",
            min(10, len(approved_voc)),
            "medium" if approved_voc else "low",
            f"{len(approved_voc)} approved Voice-of-Customer phrase(s).",
            voc_span,
        ),
        (
            "production_capacity_realism",
            0,
            "insufficient_evidence",
            "Requires operational input; not inferable from posting frequency (spec §14.1).",
            None,
        ),
        (
            "claim_governance",
            gov_score,
            gov_conf,
            f"{len(proven)}/{len(claims)} claims proven or partially proven.",
            None,
        ),
        (
            "measurement_readiness",
            min(10, 3 * len(commercial_perf)),
            "medium" if commercial_perf else "insufficient_evidence",
            f"{len(commercial_perf)} direct commercial-outcome metric(s) available.",
            None,
        ),
    ]
    grade = grade_from_scores([(score, conf) for _d, score, conf, _r, _s in dims])

    # Persist the diagnosis + its rows.
    diagnosis = BrandDiagnosis(
        project_id=project_id,
        entity_id=brand.id,
        context_version_id=context.id if context else None,
        readiness_grade=grade,
        primary_bottleneck=bottleneck,
        limitations=LIMITATIONS_TEXT,
        audits={
            "sales_elements": {"bottleneck": bottleneck, "elements": element_audit},
            "journey_coverage": journey_audit,
            "decision_alignment": decision_alignment,
            "claim_proof": claim_audit,
            "performance_evidence": {"signals": signals, "has_direct_outcome": has_direct_outcome},
        },
    )
    session.add(diagnosis)
    await session.flush()

    for dim, score, conf, rationale, span_id in dims:
        row = BrandReadinessScore(
            diagnosis_id=diagnosis.id,
            dimension=dim,
            score=score,
            confidence=conf,
            rationale=rationale,
            evidence_span_id=span_id,
        )
        session.add(row)
        readiness_rows.append(row)

    for f in findings:
        session.add(
            BrandFinding(
                diagnosis_id=diagnosis.id,
                project_id=project_id,
                dimension=f.dimension,
                subject=f.subject,
                severity=f.severity,
                confidence=f.confidence,
                finding_status=f.finding_status,
                summary=f.summary,
                limitations=f.limitations,
                is_non_content_blocker=f.is_non_content_blocker,
                evidence_span_ids=f.evidence_span_ids,
            )
        )
    await session.flush()
    return diagnosis


async def _all_voc(session: AsyncSession, project_id: uuid.UUID) -> list[VocEntry]:
    return list((await session.execute(select(VocEntry).where(VocEntry.project_id == project_id))).scalars().all())


async def get_diagnosis_payload(session: AsyncSession, diagnosis_id: uuid.UUID) -> dict:
    diagnosis = await session.get(BrandDiagnosis, diagnosis_id)
    if diagnosis is None:
        raise BrandDiagnosisError("diagnosis_not_found")
    readiness = (
        (await session.execute(select(BrandReadinessScore).where(BrandReadinessScore.diagnosis_id == diagnosis_id)))
        .scalars()
        .all()
    )
    findings = (
        (await session.execute(select(BrandFinding).where(BrandFinding.diagnosis_id == diagnosis_id))).scalars().all()
    )
    return {
        "id": str(diagnosis.id),
        "project_id": str(diagnosis.project_id),
        "entity_id": str(diagnosis.entity_id),
        "primary_bottleneck": diagnosis.primary_bottleneck,
        "readiness": {
            "grade": diagnosis.readiness_grade,
            "dimensions": [
                {
                    "dimension": r.dimension,
                    "score": r.score,
                    "confidence": r.confidence,
                    "rationale": r.rationale,
                    "evidence_span_id": str(r.evidence_span_id) if r.evidence_span_id else None,
                }
                for r in readiness
            ],
        },
        "audits": diagnosis.audits,
        "findings": [
            {
                "id": str(f.id),
                "dimension": f.dimension,
                "subject": f.subject,
                "severity": f.severity,  # always separate from confidence
                "confidence": f.confidence,
                "finding_status": f.finding_status,
                "summary": f.summary,
                "limitations": f.limitations,
                "is_non_content_blocker": f.is_non_content_blocker,
                "evidence_span_ids": f.evidence_span_ids,
            }
            for f in findings
        ],
        "limitations": diagnosis.limitations,
    }
