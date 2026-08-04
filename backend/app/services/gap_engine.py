"""Comparative coverage + gap-detection engine (spec §16–§19).

Deterministic and evidence-first. Coverage is scored per entity × territory (sales element) from the
six §16.1 components. Gaps are detected by the core rules (competitive deficit, white space,
saturation, false opportunity, competitor leak, non-content). For every gap, severity and
confidence are scored **separately** (§18) with the §18.3 caps applied, a root cause is assigned
(§19.1), and high/critical gaps carry at least one alternative explanation (§18.4).

Two invariants are enforced here:

* The engine never emits ``confirmed`` — a critical gap can only reach ``confirmed`` through
  explicit human approval (§18.3).
* Absence and competitor-only signals are handled honestly: a gap driven only by competitor
  publishing behavior is confidence-capped at ``low``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SalesElement
from app.db.models.classification import ContentClassification
from app.db.models.content_piece import ContentPiece, EvidenceSpan
from app.db.models.context import DiagnosticContextVersion
from app.db.models.entity import Entity
from app.db.models.gap import CoverageCell, Gap, GapAnalysisRun
from app.db.models.voc import Claim, PerformanceRecord, VocEntry
from app.services.brand_diagnosis import BOTTLENECK_ELEMENTS, NON_CONTENT_KEYWORDS

RULE_VERSION = "v0"
DEEP_LEN = 200  # chars: a piece at or above this length counts as "deep" for the depth component

SEVERITY_WEIGHTS = {"impact": 0.30, "relevance": 0.25, "journey": 0.20, "coverage_deficiency": 0.15, "commercial": 0.10}
CONFIDENCE_WEIGHTS = {"voc": 0.25, "diversity": 0.20, "sample": 0.20, "performance": 0.15, "human": 0.20}

_CONF_ORDER = ["insufficient_evidence", "low", "medium", "high"]


class GapEngineError(Exception):
    pass


# --- Pure scoring ------------------------------------------------------------------------------


@dataclass
class Components:
    presence: int
    relevance: int
    depth: int
    proof: int
    touchpoint: int
    micro_decision: int

    @property
    def total(self) -> int:
        return self.presence + self.relevance + self.depth + self.proof + self.touchpoint + self.micro_decision


def coverage_components(
    covering: int, max_len: int, has_claim: bool, has_proven: bool, stage: str | None, relevant: bool
) -> Components:
    """The six §16.1 coverage components (total 0–10) for one entity × territory."""
    presence = min(2, covering)
    if stage in ("decision", "evaluation"):
        relevance = 2
    elif stage == "not_applicable":
        relevance = 0
    else:
        relevance = 1 if covering else 0
    depth = 2 if (covering and max_len >= DEEP_LEN) else (1 if covering else 0)
    proof = 2 if has_proven else (1 if has_claim else 0)
    touchpoint = 1 if covering else 0
    micro = 1 if stage in ("decision", "evaluation") else 0
    return Components(presence, relevance, depth, proof, touchpoint, micro)


def element_importance(relevant: bool, has_approved_voc: bool, has_confirmed_pattern: bool) -> int:
    """Customer-need importance (0–10) for a territory (spec §17.1/§17.3). Bottleneck relevance and
    real customer evidence raise it; a topic nobody voices stays low so competitor noise cannot
    manufacture importance."""
    imp = 0
    imp += 4 if relevant else 0
    imp += 3 if has_approved_voc else 0
    imp += 3 if has_confirmed_pattern else 0
    return min(10, imp)


def severity_label(score: float) -> str:
    if score >= 80:
        return "critical"
    if score >= 65:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def confidence_label(score: float) -> str:
    if score >= 75:
        return "high"
    if score >= 50:
        return "medium"
    if score >= 25:
        return "low"
    return "insufficient_evidence"


def _cap(label: str, cap: str) -> str:
    return _CONF_ORDER[min(_CONF_ORDER.index(label), _CONF_ORDER.index(cap))]


def severity_score(impact: int, relevance: int, journey: int, coverage_deficiency: int, commercial: int) -> float:
    dims = {
        "impact": impact,
        "relevance": relevance,
        "journey": journey,
        "coverage_deficiency": coverage_deficiency,
        "commercial": commercial,
    }
    return round(sum(SEVERITY_WEIGHTS[k] * dims[k] for k in dims) * 10, 2)


def confidence_score(voc: int, diversity: int, sample: int, performance: int, human: int) -> float:
    dims = {"voc": voc, "diversity": diversity, "sample": sample, "performance": performance, "human": human}
    return round(sum(CONFIDENCE_WEIGHTS[k] * dims[k] for k in dims) * 10, 2)


# --- Data gathering ----------------------------------------------------------------------------


@dataclass
class _EntityData:
    entity: Entity
    piece_ids: set[uuid.UUID]
    max_len_by_element: dict[str, int]
    covering_by_element: dict[str, list[uuid.UUID]]
    stage_by_element: dict[str, str | None]
    span_by_piece: dict[uuid.UUID, uuid.UUID]
    has_claim: bool
    has_proven: bool


async def _effective_map(session: AsyncSession, project_id: uuid.UUID, dimension: str) -> dict[uuid.UUID, str]:
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
    out: dict[uuid.UUID, str] = {}
    for r in rows:
        val = r.approved_value or r.proposed_value
        if val:
            out[r.content_piece_id] = val
    return out


async def _gather(session: AsyncSession, project_id: uuid.UUID) -> tuple[list[_EntityData], dict]:
    entities = (await session.execute(select(Entity).where(Entity.project_id == project_id))).scalars().all()
    brand = next((e for e in entities if e.entity_type == "brand"), None)
    if brand is None:
        raise GapEngineError("no_primary_brand_entity")

    pieces = (
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
    element_val = await _effective_map(session, project_id, "primary_sales_element")
    stage_val = await _effective_map(session, project_id, "journey_stage")

    all_ids = {p.id for p in pieces}
    span_by_piece: dict[uuid.UUID, uuid.UUID] = {}
    if all_ids:
        for span in (
            (await session.execute(select(EvidenceSpan).where(EvidenceSpan.content_piece_id.in_(all_ids))))
            .scalars()
            .all()
        ):
            span_by_piece.setdefault(span.content_piece_id, span.id)

    claims = (await session.execute(select(Claim).where(Claim.project_id == project_id))).scalars().all()
    claims_by_entity: dict[uuid.UUID, list[Claim]] = {}
    for c in claims:
        claims_by_entity.setdefault(c.entity_id, []).append(c)

    data: list[_EntityData] = []
    for entity in entities:
        e_pieces = [p for p in pieces if p.entity_id == entity.id]
        covering: dict[str, list[uuid.UUID]] = {}
        max_len: dict[str, int] = {}
        stage_by_el: dict[str, str | None] = {}
        for p in e_pieces:
            el = element_val.get(p.id)
            if not el:
                continue
            covering.setdefault(el, []).append(p.id)
            max_len[el] = max(max_len.get(el, 0), len(p.original_text))
            st = stage_val.get(p.id)
            # Prefer a decision/evaluation stage if any covering piece has one.
            if st in ("decision", "evaluation") or stage_by_el.get(el) is None:
                stage_by_el[el] = st
        ent_claims = claims_by_entity.get(entity.id, [])
        data.append(
            _EntityData(
                entity=entity,
                piece_ids={p.id for p in e_pieces},
                max_len_by_element=max_len,
                covering_by_element=covering,
                stage_by_element=stage_by_el,
                span_by_piece={p.id: span_by_piece[p.id] for p in e_pieces if p.id in span_by_piece},
                has_claim=bool(ent_claims),
                has_proven=any(c.proof_status in ("proven", "partially_proven") for c in ent_claims),
            )
        )

    voc = (await session.execute(select(VocEntry).where(VocEntry.project_id == project_id))).scalars().all()
    perf = (
        (await session.execute(select(PerformanceRecord).where(PerformanceRecord.project_id == project_id)))
        .scalars()
        .all()
    )
    signals = {
        "has_approved_voc": any(v.review_status == "approved" for v in voc),
        "has_confirmed_pattern": any((v.occurrence_count or 0) >= 3 for v in voc),
        "has_commercial_perf": any(not r.is_proxy for r in perf),
        "voc": voc,
        "brand_id": brand.id,
    }
    return data, signals


# --- Root cause + alternatives -----------------------------------------------------------------


def _root_cause(gap_type: str, brand: Components | None, has_claim: bool, has_proven: bool) -> str:
    if gap_type == "non_content_gap":
        return "operational_gap"
    if gap_type in ("false_opportunity", "market_saturation"):
        return "unknown"
    if gap_type == "competitor_leak_opportunity":
        return "coverage_gap"
    # coverage-style gaps (deficit / white space): distinguish the §19.1 tree branches.
    if has_claim and not has_proven:
        return "evidence_gap"
    if brand and brand.presence >= 1:
        return "quality_gap"  # content exists but is shallow/unclear
    return "coverage_gap"


_ALTERNATIVES = [
    "Distribution was weak rather than the content meaning.",
    "The product or offer may be the real problem, not the content.",
    "The public sample excludes private sales content.",
    "The content is correct but hard to find at the needed touchpoint.",
]


def _alternatives_for(severity: str) -> list[dict]:
    if severity in ("critical", "high"):
        return [{"text": t, "status": "pending"} for t in _ALTERNATIVES[:2]]
    return []


# --- Orchestration -----------------------------------------------------------------------------


@dataclass
class _GapDraft:
    territory: str
    gap_type: str
    gap_status: str
    summary: str
    brand_score: int | None
    best_competitor_score: int | None
    evidence_span_ids: list[str]
    root_cause: str
    competitor_only_signal: bool
    severity_dims: tuple[int, int, int, int, int]
    confidence_dims: tuple[int, int, int, int]  # voc, diversity, sample, performance (human added later)
    relevant: bool = False
    fields: dict = field(default_factory=dict)


async def run_gap_analysis(session: AsyncSession, project_id: uuid.UUID) -> GapAnalysisRun:
    data, signals = await _gather(session, project_id)
    context = (
        await session.execute(
            select(DiagnosticContextVersion)
            .where(DiagnosticContextVersion.project_id == project_id)
            .order_by(DiagnosticContextVersion.version_number.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    bottleneck = context.primary_bottleneck if context else "unknown"
    relevant_set = set(BOTTLENECK_ELEMENTS.get(bottleneck, [e.value for e in SalesElement]))

    run = GapAnalysisRun(
        project_id=project_id,
        rule_version=RULE_VERSION,
        primary_bottleneck=bottleneck,
        weights={"severity": SEVERITY_WEIGHTS, "confidence": CONFIDENCE_WEIGHTS},
    )
    session.add(run)
    await session.flush()

    brand_data = next(d for d in data if d.entity.entity_type == "brand")
    competitors = [d for d in data if d.entity.entity_type == "competitor"]

    # --- Coverage matrix (one cell per entity × sales element) ---------------------------------
    cells: dict[tuple[uuid.UUID, str], Components] = {}
    for d in data:
        for element in [e.value for e in SalesElement]:
            covering = d.covering_by_element.get(element, [])
            comp = coverage_components(
                covering=len(covering),
                max_len=d.max_len_by_element.get(element, 0),
                has_claim=d.has_claim,
                has_proven=d.has_proven,
                stage=d.stage_by_element.get(element),
                relevant=element in relevant_set,
            )
            cells[(d.entity.id, element)] = comp
            ev = [str(d.span_by_piece[p]) for p in covering if p in d.span_by_piece]
            session.add(
                CoverageCell(
                    run_id=run.id,
                    project_id=project_id,
                    entity_id=d.entity.id,
                    is_brand=d.entity.entity_type == "brand",
                    territory=element,
                    score=comp.total,
                    presence=comp.presence,
                    relevance=comp.relevance,
                    depth=comp.depth,
                    proof=comp.proof,
                    touchpoint=comp.touchpoint,
                    micro_decision=comp.micro_decision,
                    reasoning=f"presence={comp.presence} relevance={comp.relevance} depth={comp.depth} "
                    f"proof={comp.proof} touchpoint={comp.touchpoint} micro={comp.micro_decision}",
                    evidence_span_ids=ev,
                )
            )

    drafts: list[_GapDraft] = []
    sample_score = 7 if len(brand_data.piece_ids) >= 15 else 4 if brand_data.piece_ids else 0
    voc_score = 10 if signals["has_approved_voc"] else 0
    perf_score = 10 if signals["has_commercial_perf"] else 3

    # --- Per-territory competitive rules -------------------------------------------------------
    for element in [e.value for e in SalesElement]:
        relevant = element in relevant_set
        brand_cell = cells[(brand_data.entity.id, element)]
        brand_score = brand_cell.total
        comp_scores = [(d, cells[(d.entity.id, element)].total) for d in competitors]
        best = max(comp_scores, key=lambda x: x[1], default=(None, 0))
        best_comp_score = best[1]
        strong_comps = [c for c in comp_scores if c[1] > 7]
        importance = element_importance(relevant, signals["has_approved_voc"], signals["has_confirmed_pattern"])

        # Evidence for a territory gap: competitor coverage spans + brand VoC spans (the need).
        comp_ev: list[str] = []
        for d, score in comp_scores:
            if score > 0:
                comp_ev += [
                    str(d.span_by_piece[p]) for p in d.covering_by_element.get(element, []) if p in d.span_by_piece
                ]
        voc_ev = [str(v.evidence_span_id) for v in signals["voc"] if v.review_status == "approved"][:3]

        gap_type = status = None
        competitor_only = False
        if best_comp_score >= 6 and importance < 5 and brand_score < 5:
            gap_type, status, competitor_only = "false_opportunity", "rejected", True
        elif brand_score < 5 and best_comp_score > 7:
            gap_type, status = "competitive_coverage_gap", "candidate"
            competitor_only = not signals["has_approved_voc"]
        elif importance >= 7 and brand_score < 5 and all(s < 5 for _d, s in comp_scores):
            gap_type, status = "market_white_space", "candidate"
        elif len(strong_comps) >= 2 and brand_score >= 5:
            gap_type, status, competitor_only = "market_saturation", "rejected", True
        if gap_type is None:
            continue

        coverage_def = max(0, 10 - brand_score)
        sev_dims = (
            min(10, importance),
            10 if relevant else 4,
            7 if relevant else 4,
            coverage_def,
            10 if signals["has_commercial_perf"] else 5,
        )
        diversity = min(10, 2 * len({*comp_ev, *voc_ev}))
        drafts.append(
            _GapDraft(
                territory=element,
                gap_type=gap_type,
                gap_status=status,
                summary=_territory_summary(gap_type, element, brand_score, best_comp_score, importance),
                brand_score=brand_score,
                best_competitor_score=best_comp_score,
                evidence_span_ids=list({*comp_ev, *voc_ev}),
                root_cause=_root_cause(gap_type, brand_cell, brand_data.has_claim, brand_data.has_proven),
                competitor_only_signal=competitor_only,
                severity_dims=sev_dims,
                confidence_dims=(0 if competitor_only else voc_score, diversity, sample_score, perf_score),
                relevant=relevant,
            )
        )

    # --- Competitor leak (public competitor complaints) ----------------------------------------
    comp_ids = {d.entity.id for d in competitors}
    for v in signals["voc"]:
        if v.entity_id in comp_ids and v.bank_type in ("complaint", "switching_reason"):
            drafts.append(
                _GapDraft(
                    territory="competitor_leak",
                    gap_type="competitor_leak_opportunity",
                    gap_status="candidate",
                    summary=(
                        f"Public competitor leak ('{v.verbatim_phrase}'): an opportunity only if the brand can "
                        "credibly perform better and provide proof. If capability is unknown, this is a research item."
                    ),
                    brand_score=None,
                    best_competitor_score=None,
                    evidence_span_ids=[str(v.evidence_span_id)],
                    root_cause="coverage_gap",
                    competitor_only_signal=True,
                    severity_dims=(6, 5, 5, 6, 5),
                    confidence_dims=(0, 2, sample_score, perf_score),
                )
            )

    # --- Non-content gap (brand operational complaints) ----------------------------------------
    for v in signals["voc"]:
        is_brand_voc = v.entity_id == signals["brand_id"] or v.entity_id is None
        if is_brand_voc and v.bank_type in ("complaint", "switching_reason"):
            low = v.verbatim_phrase.lower()
            hit = next((kw for kw in NON_CONTENT_KEYWORDS if kw in low), None)
            if hit:
                drafts.append(
                    _GapDraft(
                        territory="non_content",
                        gap_type="non_content_gap",
                        gap_status="non_content_blocker",
                        summary=(
                            f"Non-content blocker (keyword '{hit}'): content cannot credibly address this until the "
                            "underlying business/product/operational condition changes."
                        ),
                        brand_score=None,
                        best_competitor_score=None,
                        evidence_span_ids=[str(v.evidence_span_id)],
                        root_cause="operational_gap",
                        competitor_only_signal=False,
                        severity_dims=(8, 6, 6, 6, 6),
                        confidence_dims=(10 if signals["has_approved_voc"] else 5, 4, sample_score, perf_score),
                    )
                )

    # --- Persist gaps with separate severity/confidence + caps ---------------------------------
    for draft in drafts:
        sev = severity_score(*draft.severity_dims)
        sev_label = severity_label(sev)
        voc_dim, diversity, sample, performance = draft.confidence_dims
        conf = confidence_score(voc_dim, diversity, sample, performance, human=0)
        conf_label = confidence_label(conf)
        if voc_dim == 0:  # no direct customer/journey evidence → max medium (§18.3)
            conf_label = _cap(conf_label, "medium")
        if draft.competitor_only_signal:  # only competitor publishing behavior → max low (§18.3)
            conf_label = _cap(conf_label, "low")

        requires_approval = sev_label in ("critical", "high")
        session.add(
            Gap(
                run_id=run.id,
                project_id=project_id,
                territory=draft.territory,
                gap_type=draft.gap_type,
                gap_status=draft.gap_status,  # never 'confirmed' — only human approval can confirm
                severity_label=sev_label,
                severity_score=sev,
                confidence_label=conf_label,
                confidence_score=conf,
                root_cause_type=draft.root_cause,
                summary=draft.summary,
                brand_score=draft.brand_score,
                best_competitor_score=draft.best_competitor_score,
                evidence_span_ids=draft.evidence_span_ids,
                alternative_explanations=_alternatives_for(sev_label),
                competitor_only_signal=draft.competitor_only_signal,
                requires_human_approval=requires_approval,
            )
        )
    await session.flush()
    return run


def _territory_summary(gap_type: str, element: str, brand: int, best_comp: int, importance: int) -> str:
    if gap_type == "competitive_coverage_gap":
        return (
            f"Competitive deficit on '{element}': brand coverage {brand}/10 vs strongest competitor "
            f"{best_comp}/10 at the same territory. Candidate — needs evidence review."
        )
    if gap_type == "market_white_space":
        return (
            f"White space on '{element}': customer-need importance {importance}/10, but neither brand "
            f"({brand}/10) nor any competitor covers it well. Candidate — confirm the brand can own it."
        )
    if gap_type == "false_opportunity":
        return (
            f"False opportunity on '{element}': competitors publish here ({best_comp}/10) but no customer, "
            "journey, or performance evidence supports its importance."
        )
    if gap_type == "market_saturation":
        return (
            f"Saturated territory '{element}': multiple competitors cover it strongly and brand coverage "
            f"({brand}/10) is similar/generic. Not a differentiation opportunity."
        )
    return f"{gap_type} on '{element}'."


class GapNotApprovable(Exception):
    pass


async def approve_gap(session: AsyncSession, gap: Gap, user_id: uuid.UUID | None) -> Gap:
    """Human approval — the only path by which a critical gap becomes ``confirmed`` (§18.3).
    Approval also credits the human-validation confidence component."""
    from datetime import UTC, datetime

    gap.gap_status = "confirmed"
    gap.approved_by = user_id
    gap.approved_at = datetime.now(UTC)
    gap.requires_human_approval = False
    # Human validation raises confidence (the §18.2 human component).
    bumped = float(gap.confidence_score) + CONFIDENCE_WEIGHTS["human"] * 10 * 10
    gap.confidence_score = min(100.0, bumped)
    gap.confidence_label = confidence_label(gap.confidence_score)
    return gap


async def get_run_payload(session: AsyncSession, run_id: uuid.UUID) -> dict:
    run = await session.get(GapAnalysisRun, run_id)
    if run is None:
        raise GapEngineError("run_not_found")
    cells = (await session.execute(select(CoverageCell).where(CoverageCell.run_id == run_id))).scalars().all()
    gaps = (await session.execute(select(Gap).where(Gap.run_id == run_id))).scalars().all()
    return {
        "id": str(run.id),
        "rule_version": run.rule_version,
        "primary_bottleneck": run.primary_bottleneck,
        "weights": run.weights,
        "matrix": [
            {
                "entity_id": str(c.entity_id),
                "is_brand": c.is_brand,
                "territory": c.territory,
                "score": c.score,
                "evidence_span_ids": c.evidence_span_ids,
            }
            for c in cells
        ],
        "gaps": [_gap_out(g) for g in gaps],
    }


def _gap_out(g: Gap) -> dict:
    return {
        "id": str(g.id),
        "territory": g.territory,
        "gap_type": g.gap_type,
        "gap_status": g.gap_status,
        "severity": g.severity_label,  # severity and confidence are always separate
        "severity_score": float(g.severity_score),
        "confidence": g.confidence_label,
        "confidence_score": float(g.confidence_score),
        "root_cause_type": g.root_cause_type,
        "summary": g.summary,
        "brand_score": g.brand_score,
        "best_competitor_score": g.best_competitor_score,
        "evidence_span_ids": g.evidence_span_ids,
        "alternative_explanations": g.alternative_explanations,
        "competitor_only_signal": g.competitor_only_signal,
        "requires_human_approval": g.requires_human_approval,
    }
