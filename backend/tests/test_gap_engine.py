"""Phase 9 gate — Comparative Coverage and Gap Engine.

Acceptance gate (spec §27, Phase 9): "All expected fixture gaps match gold-standard outcomes. No
critical gap can be confirmed without human approval."
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from app.db.models.classification import ContentClassification
from app.db.models.context import DiagnosticContextVersion
from app.db.session import get_sessionmaker
from app.services.gap_engine import (
    confidence_score,
    coverage_components,
    element_importance,
    severity_label,
    severity_score,
)
from tests.conftest import requires_db

pytestmark = [requires_db]

DEEP = "ن" * 260  # a "deep" piece (>= 200 chars) earns the depth component
SHALLOW = "نص قصير"


# --- Pure scoring (no DB) ----------------------------------------------------------------------


def test_coverage_components_brand_weak_competitor_strong() -> None:
    brand = coverage_components(covering=1, max_len=20, has_claim=False, has_proven=False, stage=None, relevant=True)
    comp = coverage_components(
        covering=2, max_len=300, has_claim=True, has_proven=True, stage="decision", relevant=True
    )
    assert brand.total == 4 and brand.total < 5
    assert comp.total == 10 and comp.total > 7


def test_severity_and_confidence_are_independent() -> None:
    # High severity can coexist with low confidence — separate axes (spec §18).
    sev = severity_score(impact=10, relevance=10, journey=7, coverage_deficiency=10, commercial=10)
    assert severity_label(sev) == "critical"
    conf = confidence_score(voc=0, diversity=0, sample=0, performance=3, human=0)
    assert conf < sev  # different scales, computed independently


def test_importance_low_without_customer_evidence() -> None:
    assert element_importance(relevant=True, has_approved_voc=False, has_confirmed_pattern=False) == 4
    assert element_importance(relevant=True, has_approved_voc=True, has_confirmed_pattern=True) == 10


# --- Fixtures ----------------------------------------------------------------------------------


async def _project(client: AsyncClient) -> uuid.UUID:
    r = await client.post("/api/v1/projects", json={"name": f"gap-{uuid.uuid4().hex[:8]}", "primary_language": "ar"})
    return uuid.UUID(r.json()["id"])


async def _brand(client: AsyncClient, pid: uuid.UUID) -> uuid.UUID:
    r = await client.post(
        f"/api/v1/projects/{pid}/entities", json={"entity_type": "brand", "name": f"brand-{uuid.uuid4().hex[:6]}"}
    )
    return uuid.UUID(r.json()["id"])


async def _competitor(client: AsyncClient, pid: uuid.UUID) -> uuid.UUID:
    r = await client.post(
        f"/api/v1/projects/{pid}/entities",
        json={
            "entity_type": "competitor",
            "name": f"comp-{uuid.uuid4().hex[:6]}",
            "competitor_type": "direct",
            "comparison_rationale": "r",
        },
    )
    return uuid.UUID(r.json()["id"])


async def _piece(client: AsyncClient, pid: uuid.UUID, entity_id: uuid.UUID, text: str) -> tuple[uuid.UUID, uuid.UUID]:
    r = await client.post(
        f"/api/v1/projects/{pid}/sources/manual",
        json={
            "entity_id": str(entity_id),
            "source_category": "brand_owned",
            "display_name": "p",
            "text": text,
            "content_format": "article",
        },
    )
    piece_id = uuid.UUID(r.json()["content_piece_ids"][0])
    span = (await client.get(f"/api/v1/content/{piece_id}/evidence")).json()[0]["id"]
    return piece_id, uuid.UUID(span)


async def _classify(pid: uuid.UUID, piece_id: uuid.UUID, dimension: str, value: str, span_id: uuid.UUID) -> None:
    async with get_sessionmaker()() as session:
        session.add(
            ContentClassification(
                project_id=pid,
                content_piece_id=piece_id,
                classification_dimension=dimension,
                proposed_value=value,
                origin="ai_proposed",
                confidence="high",
                evidence_ids=[str(span_id)],
                fingerprint=uuid.uuid4().hex,
                is_current=True,
            )
        )
        await session.commit()


async def _context(pid: uuid.UUID, bottleneck: str) -> None:
    async with get_sessionmaker()() as session:
        session.add(
            DiagnosticContextVersion(
                project_id=pid,
                version_number=1,
                target_buying_decision="d",
                purchase_type="first_purchase",
                primary_product_or_service="p",
                primary_segment_name="s",
                primary_segment_definition="sd",
                primary_decision_maker_role="individual_buyer",
                primary_bottleneck=bottleneck,
                bottleneck_statement="b",
                status="approved",
            )
        )
        await session.commit()


async def _approve_voc(
    client: AsyncClient,
    pid: uuid.UUID,
    phrase: str,
    times: int = 1,
    bank: str = "motivation",
    entity_id: uuid.UUID | None = None,
) -> None:
    for _ in range(times):
        body: dict = {"bank_type": bank, "verbatim_phrase": phrase}
        if entity_id:
            body["entity_id"] = str(entity_id)
        r = await client.post(f"/api/v1/projects/{pid}/voc/manual", json=body)
        await client.post(f"/api/v1/voc/{r.json()['id']}/approve")


async def _competitor_strong(client: AsyncClient, pid: uuid.UUID, cid: uuid.UUID, element: str, n: int = 2) -> None:
    for i in range(n):
        piece, span = await _piece(client, pid, cid, DEEP + f" {element} {cid.hex} {i}")
        await _classify(pid, piece, "primary_sales_element", element, span)
        await _classify(pid, piece, "journey_stage", "decision", span)


# --- 1. Brand <5 and competitor >7 → competitive deficit candidate ----------------------------


async def test_competitive_deficit_candidate(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await _brand(noauth_client, pid)
    brand_id = (await noauth_client.get(f"/api/v1/projects/{pid}/entities")).json()[0]["id"]
    cid = await _competitor(noauth_client, pid)
    await _context(pid, "persuasion")
    await _approve_voc(noauth_client, pid, "أحتاج دليل الخبرة")  # importance >= 5, customer-evidenced

    bp, bs = await _piece(noauth_client, pid, uuid.UUID(brand_id), SHALLOW)
    await _classify(pid, bp, "primary_sales_element", "authority", bs)
    await _competitor_strong(noauth_client, pid, cid, "authority")

    run = (await noauth_client.post(f"/api/v1/projects/{pid}/gap-analysis")).json()
    deficit = next(g for g in run["gaps"] if g["territory"] == "authority")
    assert deficit["gap_type"] == "competitive_coverage_gap"
    assert deficit["gap_status"] == "candidate"
    assert deficit["brand_score"] < 5 and deficit["best_competitor_score"] > 7


# --- 2. Same-stage/touchpoint requirement: no cross-territory deficit --------------------------


async def test_same_territory_requirement(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await _brand(noauth_client, pid)
    brand_id = (await noauth_client.get(f"/api/v1/projects/{pid}/entities")).json()[0]["id"]
    cid = await _competitor(noauth_client, pid)
    await _context(pid, "persuasion")

    # Brand is weak on 'authority'; the competitor is strong only on 'comparison' (a different territory).
    bp, bs = await _piece(noauth_client, pid, uuid.UUID(brand_id), SHALLOW)
    await _classify(pid, bp, "primary_sales_element", "authority", bs)
    await _competitor_strong(noauth_client, pid, cid, "comparison")

    run = (await noauth_client.post(f"/api/v1/projects/{pid}/gap-analysis")).json()
    # The brand's authority weakness is never matched to the competitor's comparison strength.
    assert not any(g["territory"] == "authority" for g in run["gaps"])


# --- 3. Competitor-only signal → confidence capped at low -------------------------------------


async def test_competitor_only_signal_confidence_cap(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await _brand(noauth_client, pid)
    cid = await _competitor(noauth_client, pid)
    await _context(pid, "persuasion")
    # Competitor publishes on 'authority', but there is NO customer/VoC evidence of importance.
    await _competitor_strong(noauth_client, pid, cid, "authority")

    run = (await noauth_client.post(f"/api/v1/projects/{pid}/gap-analysis")).json()
    gap = next(g for g in run["gaps"] if g["territory"] == "authority")
    assert gap["competitor_only_signal"] is True
    assert gap["confidence"] in ("low", "insufficient_evidence")  # §18.3 cap


# --- 4. White-space fixture --------------------------------------------------------------------


async def test_white_space_fixture(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await _brand(noauth_client, pid)
    await _competitor(noauth_client, pid)  # exists but has no coverage on the territory
    await _context(pid, "persuasion")
    # High customer-need importance (relevant + approved VoC + confirmed 3x pattern) but nobody covers it.
    await _approve_voc(noauth_client, pid, "من هو الخبير خلف المنتج؟", times=3, bank="question")

    run = (await noauth_client.post(f"/api/v1/projects/{pid}/gap-analysis")).json()
    ws = [g for g in run["gaps"] if g["gap_type"] == "market_white_space"]
    assert ws and ws[0]["gap_status"] == "candidate"


# --- 5. False-opportunity fixture --------------------------------------------------------------


async def test_false_opportunity_fixture(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await _brand(noauth_client, pid)
    cid = await _competitor(noauth_client, pid)
    await _context(pid, "persuasion")
    # Competitor publishes heavily on 'authority' but no VoC/journey/performance evidence supports it.
    await _competitor_strong(noauth_client, pid, cid, "authority")

    run = (await noauth_client.post(f"/api/v1/projects/{pid}/gap-analysis")).json()
    fo = [g for g in run["gaps"] if g["gap_type"] == "false_opportunity"]
    assert fo and fo[0]["gap_status"] == "rejected"


# --- 6. Saturated territory fixture ------------------------------------------------------------


async def test_saturated_territory_fixture(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await _brand(noauth_client, pid)
    brand_id = (await noauth_client.get(f"/api/v1/projects/{pid}/entities")).json()[0]["id"]
    c1 = await _competitor(noauth_client, pid)
    c2 = await _competitor(noauth_client, pid)
    await _context(pid, "persuasion")

    # Two competitors cover 'authority' strongly; brand coverage is similar/generic (>=5).
    for i in range(2):
        bp, bs = await _piece(noauth_client, pid, uuid.UUID(brand_id), SHALLOW + f" {i}")
        await _classify(pid, bp, "primary_sales_element", "authority", bs)
    await _competitor_strong(noauth_client, pid, c1, "authority")
    await _competitor_strong(noauth_client, pid, c2, "authority")

    run = (await noauth_client.post(f"/api/v1/projects/{pid}/gap-analysis")).json()
    sat = [g for g in run["gaps"] if g["gap_type"] == "market_saturation"]
    assert sat and sat[0]["territory"] == "authority"


# --- 7. Non-content gap fixture ----------------------------------------------------------------


async def test_non_content_gap_fixture(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await _brand(noauth_client, pid)
    await _approve_voc(noauth_client, pid, "التوصيل بطيء جدًا والشحن متأخر", bank="complaint")

    run = (await noauth_client.post(f"/api/v1/projects/{pid}/gap-analysis")).json()
    nc = [g for g in run["gaps"] if g["gap_type"] == "non_content_gap"]
    assert nc
    assert nc[0]["gap_status"] == "non_content_blocker"
    assert nc[0]["root_cause_type"] == "operational_gap"


# --- 8. Every critical gap has evidence + alternative explanation; no auto-confirm -------------


async def test_critical_gap_evidence_alternatives_and_approval(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await _brand(noauth_client, pid)
    brand_id = (await noauth_client.get(f"/api/v1/projects/{pid}/entities")).json()[0]["id"]
    cid = await _competitor(noauth_client, pid)
    await _context(pid, "persuasion")
    await _approve_voc(noauth_client, pid, "أثبت لي النتائج", times=3)  # importance 10
    await noauth_client.post(
        f"/api/v1/projects/{pid}/performance/manual",
        json={
            "entity_id": str(brand_id),
            "metric_name": "revenue",
            "metric_value": 1000,
            "period_start": "2026-01-01",
            "period_end": "2026-01-31",
            "paid_organic_status": "organic",
        },
    )
    await _competitor_strong(noauth_client, pid, cid, "authority")  # brand has 0 → coverage deficiency 10

    run = (await noauth_client.post(f"/api/v1/projects/{pid}/gap-analysis")).json()
    gaps = run["gaps"]
    # The engine never auto-confirms anything.
    assert all(g["gap_status"] != "confirmed" for g in gaps)
    criticals = [g for g in gaps if g["severity"] == "critical"]
    assert criticals, "expected at least one critical gap"
    for g in criticals:
        assert g["evidence_span_ids"], "critical gap must cite evidence"
        assert g["alternative_explanations"], "critical gap must carry an alternative explanation"
        assert g["requires_human_approval"] is True

    # A critical gap becomes 'confirmed' only through explicit human approval.
    approved = (await noauth_client.post(f"/api/v1/gaps/{criticals[0]['id']}/approve")).json()
    assert approved["gap_status"] == "confirmed"
    assert approved["requires_human_approval"] is False
