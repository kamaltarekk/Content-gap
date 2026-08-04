"""Phase 10 gate — Reports and Strategy-Readiness Gate.

Acceptance gate (spec §27, Phase 10): "An approved report can be reopened later with unchanged
content and complete evidence/version trace."
"""

from __future__ import annotations

import json
import uuid

from httpx import AsyncClient

from app.db.models.classification import ContentClassification
from app.db.models.context import DiagnosticContextVersion
from app.db.session import get_sessionmaker
from app.services.report import decide_readiness
from tests.conftest import requires_db

pytestmark = [requires_db]

DEEP = "ن" * 260


# --- Pure readiness decision (no DB) -----------------------------------------------------------


def test_readiness_four_statuses_pure() -> None:
    non_content = [
        {
            "id": "1",
            "territory": "non_content",
            "gap_type": "non_content_gap",
            "gap_status": "non_content_blocker",
            "severity": "high",
            "confidence": "medium",
        }
    ]
    assert decide_readiness(non_content, True)[0] == "blocked_by_non_content_issue"

    insufficient = [
        {
            "id": "2",
            "territory": "a",
            "gap_type": "competitive_coverage_gap",
            "gap_status": "candidate",
            "severity": "critical",
            "confidence": "insufficient_evidence",
        }
    ]
    assert decide_readiness(insufficient, True)[0] == "more_evidence_required"
    assert decide_readiness([], False)[0] == "more_evidence_required"  # context not approved

    candidate = [
        {
            "id": "3",
            "territory": "a",
            "gap_type": "competitive_coverage_gap",
            "gap_status": "candidate",
            "severity": "medium",
            "confidence": "medium",
        }
    ]
    assert decide_readiness(candidate, True)[0] == "ready_with_unresolved_hypotheses"

    assert decide_readiness([], True)[0] == "ready_for_content_strategy"


# --- Fixtures ----------------------------------------------------------------------------------


async def _project(client: AsyncClient) -> uuid.UUID:
    r = await client.post("/api/v1/projects", json={"name": f"rep-{uuid.uuid4().hex[:8]}", "primary_language": "ar"})
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


async def _approved_context(pid: uuid.UUID, bottleneck: str = "persuasion") -> None:
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


# --- 1. Snapshot immutability: old report unchanged after new data ----------------------------


async def test_report_snapshot_immutable_after_new_data(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    brand = await _brand(noauth_client, pid)
    await _approved_context(pid)
    report_a = (await noauth_client.post(f"/api/v1/projects/{pid}/reports")).json()
    snapshot_a = report_a["snapshot"]

    # Add new data, then generate a second report.
    await _piece(noauth_client, pid, brand, "محتوى جديد للعلامة")
    report_b = (await noauth_client.post(f"/api/v1/projects/{pid}/reports")).json()
    assert report_b["id"] != report_a["id"]

    # Reopen A: byte-for-byte unchanged.
    reopened = (await noauth_client.get(f"/api/v1/reports/{report_a['id']}")).json()
    assert reopened["snapshot"] == snapshot_a
    assert (
        reopened["snapshot"]["version_manifest"]["dataset"]["content_pieces"]
        == snapshot_a["version_manifest"]["dataset"]["content_pieces"]
    )
    # B reflects the new data.
    assert (
        report_b["snapshot"]["version_manifest"]["dataset"]["content_pieces"]
        > snapshot_a["version_manifest"]["dataset"]["content_pieces"]
    )


# --- 2. Version manifest carries context/dataset/model/prompt/rule versions -------------------


async def test_version_manifest_complete(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await _brand(noauth_client, pid)
    await _approved_context(pid)
    report = (await noauth_client.post(f"/api/v1/projects/{pid}/reports")).json()
    vm = report["version_manifest"]
    assert vm["context_version_number"] == 1 and vm["context_status"] == "approved"
    assert vm["rule_version"] and vm["ai_model"]
    assert vm["prompt_versions"]  # non-empty prompt version map
    assert set(vm["dataset"]) >= {"content_pieces", "evidence_spans", "entities"}


# --- 3. Readiness: four statuses via the API ---------------------------------------------------


async def test_readiness_blocked_by_non_content(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await _brand(noauth_client, pid)
    await _approved_context(pid)
    await noauth_client.post(
        f"/api/v1/projects/{pid}/voc/manual",
        json={"bank_type": "complaint", "verbatim_phrase": "التوصيل بطيء جدًا والشحن متأخر"},
    )
    report = (await noauth_client.post(f"/api/v1/projects/{pid}/reports")).json()
    assert report["readiness_status"] == "blocked_by_non_content_issue"


async def test_readiness_more_evidence_without_context(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await _brand(noauth_client, pid)  # no approved context
    report = (await noauth_client.post(f"/api/v1/projects/{pid}/reports")).json()
    assert report["readiness_status"] == "more_evidence_required"


async def test_readiness_ready_when_clean(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await _brand(noauth_client, pid)
    await _approved_context(pid)
    report = (await noauth_client.post(f"/api/v1/projects/{pid}/reports")).json()
    assert report["readiness_status"] == "ready_for_content_strategy"
    assert report["readiness_status"] in {
        "ready_for_content_strategy",
        "ready_with_unresolved_hypotheses",
        "more_evidence_required",
        "blocked_by_non_content_issue",
    }


async def test_readiness_unresolved_with_candidate_gap(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    brand = await _brand(noauth_client, pid)
    cid = await _competitor(noauth_client, pid)
    await _approved_context(pid)
    # Importance via approved VoC + brand weak / competitor strong => a candidate deficit gap.
    r = await noauth_client.post(
        f"/api/v1/projects/{pid}/voc/manual", json={"bank_type": "motivation", "verbatim_phrase": "أحتاج دليل الخبرة"}
    )
    await noauth_client.post(f"/api/v1/voc/{r.json()['id']}/approve")
    bp, bs = await _piece(noauth_client, pid, brand, "نص قصير")
    await _classify(pid, bp, "primary_sales_element", "authority", bs)
    for i in range(2):
        cp, cs = await _piece(noauth_client, pid, cid, DEEP + f" {i}")
        await _classify(pid, cp, "primary_sales_element", "authority", cs)
        await _classify(pid, cp, "journey_stage", "decision", cs)

    report = (await noauth_client.post(f"/api/v1/projects/{pid}/reports")).json()
    assert report["readiness_status"] == "ready_with_unresolved_hypotheses"
    assert report["snapshot"]["readiness_decision"]["unresolved_items"]


# --- 4. Arabic print (browser-print PDF) export ------------------------------------------------


async def test_arabic_print_export(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await _brand(noauth_client, pid)
    await _approved_context(pid)
    rep = (await noauth_client.post(f"/api/v1/projects/{pid}/reports")).json()
    html = (await noauth_client.get(f"/api/v1/reports/{rep['id']}/export/html")).text
    assert 'dir="rtl"' in html and 'lang="ar"' in html
    assert "@media print" in html
    assert "التقرير التشخيصي" in html  # Arabic heading present


# --- 5. Export schema validation (JSON + CSV) --------------------------------------------------


async def test_exports_json_and_csv(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await _brand(noauth_client, pid)
    await _approved_context(pid)
    rep = (await noauth_client.post(f"/api/v1/projects/{pid}/reports")).json()

    j = (await noauth_client.get(f"/api/v1/reports/{rep['id']}/export/json")).json()
    for key in ("executive_diagnosis", "readiness_decision", "version_manifest", "gaps", "brand_diagnosis"):
        assert key in j
    assert j["readiness_decision"]["status"] == rep["readiness_status"]

    csv_resp = await noauth_client.get(f"/api/v1/reports/{rep['id']}/export/csv")
    assert csv_resp.headers["content-type"].startswith("text/csv")
    header = csv_resp.text.splitlines()[0]
    assert header.startswith("territory,gap_type,gap_status,severity")


async def test_report_requires_brand(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    r = await noauth_client.post(f"/api/v1/projects/{pid}/reports")
    assert r.status_code == 422


async def test_report_approve_freezes_content(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await _brand(noauth_client, pid)
    await _approved_context(pid)
    rep = (await noauth_client.post(f"/api/v1/projects/{pid}/reports")).json()
    before = json.dumps(rep["snapshot"], sort_keys=True)
    approved = (await noauth_client.post(f"/api/v1/reports/{rep['id']}/approve")).json()
    assert approved["status"] == "approved"
    assert json.dumps(approved["snapshot"], sort_keys=True) == before  # approval never mutates content
