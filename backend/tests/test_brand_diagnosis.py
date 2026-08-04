"""Phase 7 gate — Brand Diagnosis.

Acceptance gate (spec §27, Phase 7): "A real fixture produces a brand diagnosis with clickable
evidence, limitations, separate severity/confidence, and no strategy-generation output."
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.db.models.classification import ContentClassification
from app.db.models.context import DiagnosticContextVersion
from app.db.session import get_sessionmaker
from app.services.brand_diagnosis import BOTTLENECK_ELEMENTS, element_coverage_score, grade_from_scores
from tests.conftest import requires_db

pytestmark = [requires_db]


# --- Pure formula tests (no DB) ----------------------------------------------------------------


def test_coverage_score_formula() -> None:
    assert element_coverage_score(0) == 0
    assert element_coverage_score(1) == 2
    assert element_coverage_score(3) == 6
    assert element_coverage_score(5) == 10
    assert element_coverage_score(7) == 10  # capped


def test_grade_excludes_insufficient_evidence_dimensions() -> None:
    # Two strong scored dims + operational unknowns marked insufficient_evidence => grade from the two.
    scored = [(9, "medium"), (9, "low"), (0, "insufficient_evidence"), (0, "insufficient_evidence")]
    assert grade_from_scores(scored) == "a"
    assert grade_from_scores([(0, "insufficient_evidence")]) is None


# --- Fixtures ----------------------------------------------------------------------------------


async def _project(client: AsyncClient) -> uuid.UUID:
    r = await client.post("/api/v1/projects", json={"name": f"bd-{uuid.uuid4().hex[:8]}", "primary_language": "ar"})
    return uuid.UUID(r.json()["id"])


async def _brand(client: AsyncClient, pid: uuid.UUID) -> uuid.UUID:
    r = await client.post(
        f"/api/v1/projects/{pid}/entities", json={"entity_type": "brand", "name": f"brand-{uuid.uuid4().hex[:6]}"}
    )
    return uuid.UUID(r.json()["id"])


async def _piece_and_span(
    client: AsyncClient, pid: uuid.UUID, text: str = "محتوى العلامة"
) -> tuple[uuid.UUID, uuid.UUID]:
    r = await client.post(
        f"/api/v1/projects/{pid}/sources/manual",
        json={"source_category": "brand_owned", "display_name": "c", "text": text, "content_format": "article"},
    )
    piece_id = uuid.UUID(r.json()["content_piece_ids"][0])
    spans = (await client.get(f"/api/v1/content/{piece_id}/evidence")).json()
    return piece_id, uuid.UUID(spans[0]["id"])


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


# --- 1. Coverage integration: 3 aligned pieces covering an element => score 6 -------------------


async def test_sales_element_coverage_from_pieces(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await _brand(noauth_client, pid)
    for i in range(3):
        piece_id, span_id = await _piece_and_span(noauth_client, pid, text=f"محتوى العلامة رقم {i}")
        await _classify(pid, piece_id, "primary_sales_element", "authority", span_id)
    diag = (await noauth_client.post(f"/api/v1/projects/{pid}/brand-diagnosis")).json()
    elements = {e["element"]: e for e in diag["audits"]["sales_elements"]["elements"]}
    assert elements["authority"]["coverage_score"] == 6
    assert elements["authority"]["evidence_span_ids"]  # clickable evidence present


# --- 2. Bottleneck-filtered sales-element audit ------------------------------------------------


async def test_bottleneck_filtered_sales_element_audit(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await _brand(noauth_client, pid)
    await _context(pid, "persuasion")
    diag = (await noauth_client.post(f"/api/v1/projects/{pid}/brand-diagnosis")).json()
    audit = diag["audits"]["sales_elements"]
    assert audit["bottleneck"] == "persuasion"
    relevant = {e["element"] for e in audit["elements"] if e["relevant_to_bottleneck"]}
    assert relevant == set(BOTTLENECK_ELEMENTS["persuasion"])


# --- 3. Not-aligned content is labeled, not penalized, and excluded from coverage --------------


async def test_not_aligned_content_behavior(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await _brand(noauth_client, pid)
    piece_id, span_id = await _piece_and_span(noauth_client, pid)
    # Same piece: out of current scope (journey not_applicable) yet nominally covers an element.
    await _classify(pid, piece_id, "journey_stage", "not_applicable", span_id)
    await _classify(pid, piece_id, "primary_sales_element", "authority", span_id)

    diag = (await noauth_client.post(f"/api/v1/projects/{pid}/brand-diagnosis")).json()
    da = diag["audits"]["decision_alignment"]
    labels = {p["content_piece_id"]: p["label"] for p in da["pieces"]}
    assert labels[str(piece_id)] == "not_aligned_with_current_decision"
    assert da["not_aligned"] == 1

    # Not-aligned content does not count toward coverage...
    elements = {e["element"]: e for e in diag["audits"]["sales_elements"]["elements"]}
    assert elements["authority"]["coverage_score"] == 0
    # ...and its alignment finding carries no severity (labeled, not a defect).
    da_findings = [f for f in diag["findings"] if f["dimension"] == "decision_alignment"]
    assert da_findings and all(f["severity"] is None for f in da_findings)


# --- 4. Severity and confidence are separate: an unsupported claim is high severity / low conf --


async def test_high_severity_low_confidence_finding(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    entity_id = await _brand(noauth_client, pid)
    piece_id, _span = await _piece_and_span(noauth_client, pid)
    await noauth_client.post(
        f"/api/v1/projects/{pid}/claims",
        json={
            "entity_id": str(entity_id),
            "content_piece_id": str(piece_id),
            "claim_text": "الأفضل بلا منازع",
            "claim_type": "quality",
        },
    )
    diag = (await noauth_client.post(f"/api/v1/projects/{pid}/brand-diagnosis")).json()
    claim_findings = [f for f in diag["findings"] if f["dimension"] == "claim_proof"]
    assert claim_findings
    f = claim_findings[0]
    # The two axes are independent columns and here take different values.
    assert f["severity"] == "high"
    assert f["confidence"] == "low"
    assert f["severity"] != f["confidence"]


# --- 5. Non-content blocker fixture ------------------------------------------------------------


async def test_non_content_blocker_fixture(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await _brand(noauth_client, pid)
    await noauth_client.post(
        f"/api/v1/projects/{pid}/voc/manual",
        json={"bank_type": "complaint", "verbatim_phrase": "التوصيل بطيء جدًا والشحن متأخر دائمًا"},
    )
    diag = (await noauth_client.post(f"/api/v1/projects/{pid}/brand-diagnosis")).json()
    blockers = [f for f in diag["findings"] if f["is_non_content_blocker"]]
    assert blockers
    b = blockers[0]
    assert b["dimension"] == "non_content_blocker"
    assert b["evidence_span_ids"]  # traceable to the verbatim complaint
    assert b["finding_status"] == "inference"


# --- 6. Readiness scorecard + limitations + NO strategy output ---------------------------------

_FORBIDDEN_KEYS = {
    "recommendation",
    "recommendations",
    "strategy",
    "suggested_content",
    "next_actions",
    "action_plan",
    "playbook",
    "advice",
}


def _walk_keys(obj: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(k)
            keys |= _walk_keys(v)
    elif isinstance(obj, list):
        for item in obj:
            keys |= _walk_keys(item)
    return keys


async def test_diagnosis_has_scorecard_limitations_and_no_strategy(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await _brand(noauth_client, pid)
    piece_id, span_id = await _piece_and_span(noauth_client, pid)
    await _classify(pid, piece_id, "primary_sales_element", "authority", span_id)
    diag = (await noauth_client.post(f"/api/v1/projects/{pid}/brand-diagnosis")).json()

    # Readiness scorecard: 8 dimensions, shown with scores; operational unknowns are honest.
    dims = {d["dimension"]: d for d in diag["readiness"]["dimensions"]}
    assert len(dims) == 8
    assert dims["expert_author_availability"]["confidence"] == "insufficient_evidence"
    assert dims["production_capacity_realism"]["confidence"] == "insufficient_evidence"

    # Limitations present; grade is one of A–D or null.
    assert "analyzed sample" in diag["limitations"]
    assert diag["readiness"]["grade"] in {"a", "b", "c", "d", None}

    # No strategy-generation output anywhere in the payload.
    assert _walk_keys(diag) & _FORBIDDEN_KEYS == set()


async def test_run_requires_primary_brand(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    r = await noauth_client.post(f"/api/v1/projects/{pid}/brand-diagnosis")
    assert r.status_code == 422  # no brand entity yet


@pytest.mark.parametrize("bottleneck", ["attention", "desire", "persuasion", "friction"])
def test_bottleneck_maps_are_valid_sales_elements(bottleneck: str) -> None:
    from app.core.enums import SalesElement

    valid = {e.value for e in SalesElement}
    assert set(BOTTLENECK_ELEMENTS[bottleneck]) <= valid
