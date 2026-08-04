from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.rules.preconditions import evaluate_prerequisites
from tests.conftest import requires_db

pytestmark = [requires_db, pytest.mark.asyncio]


async def _project(client: AsyncClient, name: str = "مشروع نقاء") -> str:
    r = await client.post("/api/v1/projects", json={"name": name, "primary_language": "ar"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _full_context() -> dict:
    return {
        "target_buying_decision": "شراء أول فلتر مياه منزلي",
        "purchase_type": "first_purchase",
        "primary_product_or_service": "فلتر مياه تحت الحوض",
        "primary_segment_name": "أسر حضرية مهتمة بالصحة",
        "primary_segment_definition": "آباء في المدن يقلقون على جودة مياه الأطفال",
        "primary_decision_maker_role": "parent_caregiver",
        "primary_bottleneck": "persuasion",
        "bottleneck_statement": "يعتقدون أن الفلتر مكلف وصعب الصيانة",
        "analysis_period_start": "2026-01-01",
        "analysis_period_end": "2026-06-30",
        "comparison_period_start": "2026-01-01",
        "comparison_period_end": "2026-06-30",
        "included_channels": ["instagram", "website"],
    }


async def test_one_primary_brand_constraint(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    r1 = await noauth_client.post(f"/api/v1/projects/{pid}/entities", json={"entity_type": "brand", "name": "نقاء"})
    assert r1.status_code == 201 and r1.json()["is_primary_brand"] is True
    r2 = await noauth_client.post(
        f"/api/v1/projects/{pid}/entities", json={"entity_type": "brand", "name": "علامة ثانية"}
    )
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "ONE_PRIMARY_BRAND_PER_PROJECT"


async def test_competitor_requires_rationale(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    bad = await noauth_client.post(
        f"/api/v1/projects/{pid}/entities", json={"entity_type": "competitor", "name": "AquaPure"}
    )
    assert bad.status_code == 422
    ok = await noauth_client.post(
        f"/api/v1/projects/{pid}/entities",
        json={
            "entity_type": "competitor",
            "name": "AquaPure",
            "competitor_type": "direct",
            "comparison_rationale": "منافس مباشر",
        },
    )
    assert ok.status_code == 201


async def test_missing_prerequisite_response(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    # No brand entity, incomplete context (missing periods + channels).
    ctx = _full_context()
    del ctx["included_channels"]
    del ctx["analysis_period_start"]
    r = await noauth_client.post(f"/api/v1/projects/{pid}/context/versions", json=ctx)
    vid = r.json()["id"]
    gate = (await noauth_client.post(f"/api/v1/context/versions/{vid}/validate")).json()
    assert gate["status"] == "fail"
    assert gate["can_run_full_analysis"] is False
    assert gate["can_run_partial_analysis"] is True
    for missing in ("brand_entity", "included_channels", "analysis_period_start"):
        assert missing in gate["missing_required_fields"]
    # Approve must be blocked with the gate detail.
    approve = await noauth_client.post(f"/api/v1/context/versions/{vid}/approve")
    assert approve.status_code == 422


async def test_approve_then_immutable_and_clone_on_edit(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await noauth_client.post(f"/api/v1/projects/{pid}/entities", json={"entity_type": "brand", "name": "نقاء"})
    created = await noauth_client.post(f"/api/v1/projects/{pid}/context/versions", json=_full_context())
    vid = created.json()["id"]

    gate = (await noauth_client.post(f"/api/v1/context/versions/{vid}/validate")).json()
    assert gate["can_run_full_analysis"] is True

    approved = await noauth_client.post(f"/api/v1/context/versions/{vid}/approve")
    assert approved.status_code == 200 and approved.json()["status"] == "approved"

    # Approved context is immutable.
    patched = await noauth_client.patch(f"/api/v1/context/versions/{vid}", json={"bottleneck_statement": "changed"})
    assert patched.status_code == 409

    # Clone-on-edit produces a new pending version that IS editable.
    clone = await noauth_client.post(f"/api/v1/context/versions/{vid}/clone")
    assert clone.status_code == 201
    cid = clone.json()["id"]
    assert clone.json()["status"] == "pending"
    assert clone.json()["version_number"] == created.json()["version_number"] + 1
    edit = await noauth_client.patch(f"/api/v1/context/versions/{cid}", json={"bottleneck_statement": "نسخة معدلة"})
    assert edit.status_code == 200 and edit.json()["bottleneck_statement"] == "نسخة معدلة"

    # The original approved version is unchanged.
    original = (await noauth_client.get(f"/api/v1/context/versions/{vid}")).json()
    assert original["bottleneck_statement"] == _full_context()["bottleneck_statement"]


async def test_arabic_persistence_roundtrip(noauth_client: AsyncClient) -> None:
    arabic_name = "مشروع اختبار العربية ١٢٣ mixed"
    pid = await _project(noauth_client, name=arabic_name)
    ctx = _full_context()
    created = await noauth_client.post(f"/api/v1/projects/{pid}/context/versions", json=ctx)
    got = (await noauth_client.get(f"/api/v1/context/versions/{created.json()['id']}")).json()
    # Arabic preserved byte-for-byte, not transliterated.
    assert got["target_buying_decision"] == ctx["target_buying_decision"]
    assert got["primary_segment_definition"] == ctx["primary_segment_definition"]
    project = (await noauth_client.get(f"/api/v1/projects/{pid}")).json()
    assert project["name"] == arabic_name


@pytest.mark.asyncio
async def test_score_evidence_requirement() -> None:
    # Pure precondition rule: a score entered without >= 2 evidence refs is blocked.
    ctx = _full_context()
    ctx["attention_score"] = 6
    ctx["score_evidence"] = {"attention": ["ev-1"]}
    result = evaluate_prerequisites(ctx, project_name="p", has_primary_brand=True)
    assert "attention_score_evidence" in result.missing_required_fields
    ctx["score_evidence"] = {"attention": ["ev-1", "ev-2"]}
    ok = evaluate_prerequisites(ctx, project_name="p", has_primary_brand=True)
    assert ok.can_run_full_analysis is True
