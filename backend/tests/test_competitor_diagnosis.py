"""Phase 8 gate — Competitor Diagnosis.

Acceptance gate (spec §27, Phase 8): "The tool can diagnose up to three competitors from public
samples without presenting private or internal conclusions as facts."
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from app.services.competitor import sample_sufficiency
from tests.conftest import requires_db

pytestmark = [requires_db]


# --- Pure sufficiency formula (no DB) ----------------------------------------------------------


def test_sample_sufficiency_volume_alone_is_not_high() -> None:
    # 100 shallow pieces on a single channel cannot beat a smaller multi-channel sample.
    big_shallow = sample_sufficiency(100, ["instagram"], duplicate_rate=0.5)
    small_deep = sample_sufficiency(20, ["instagram", "website"], duplicate_rate=0.0)
    assert big_shallow != "high"  # capped by single channel + high duplication
    assert small_deep == "medium"
    assert sample_sufficiency(0, [], 0.0) == "insufficient_evidence"
    assert sample_sufficiency(40, ["a", "b"], 0.0) == "high"  # breadth + volume can reach high


# --- Fixtures ----------------------------------------------------------------------------------


async def _project(client: AsyncClient) -> uuid.UUID:
    r = await client.post("/api/v1/projects", json={"name": f"cd-{uuid.uuid4().hex[:8]}", "primary_language": "ar"})
    return uuid.UUID(r.json()["id"])


async def _competitor(client: AsyncClient, pid: uuid.UUID, name: str | None = None) -> uuid.UUID:
    r = await client.post(
        f"/api/v1/projects/{pid}/entities",
        json={
            "entity_type": "competitor",
            "name": name or f"comp-{uuid.uuid4().hex[:6]}",
            "competitor_type": "direct",
            "comparison_rationale": "منافس مباشر في نفس الفئة",
        },
    )
    assert r.status_code == 201, r.text
    return uuid.UUID(r.json()["id"])


# --- 1. Comparison-rationale requirement -------------------------------------------------------


async def test_comparison_rationale_required(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    bad = await noauth_client.post(
        f"/api/v1/projects/{pid}/entities", json={"entity_type": "competitor", "name": "NoRationale"}
    )
    assert bad.status_code == 422


async def test_max_three_competitors(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    for _ in range(3):
        await _competitor(noauth_client, pid)
    fourth = await noauth_client.post(
        f"/api/v1/projects/{pid}/entities",
        json={"entity_type": "competitor", "name": "fourth", "competitor_type": "direct", "comparison_rationale": "r"},
    )
    assert fourth.status_code == 409


# --- 2. Blocked website partial completion -----------------------------------------------------


async def test_blocked_website_partial_completion(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    cid = await _competitor(noauth_client, pid)
    body = {
        "channels": ["website"],
        "items": [
            {"content_format": "article", "text": "مقال عام عن المنتج", "url": "https://c/1"},
            {"content_format": "article", "url": "https://c/2", "status": "blocked"},
            {"content_format": "article", "url": "https://c/3", "status": "failed"},
        ],
    }
    r = await noauth_client.post(f"/api/v1/projects/{pid}/competitors/{cid}/collect", json=body)
    assert r.status_code == 201
    m = r.json()
    assert m["status"] == "partial"  # not silently "complete"
    assert m["collected_count"] == 1 and m["blocked_count"] == 1 and m["failed_count"] == 1
    statuses = {i["item_status"] for i in m["items"]}
    assert {"collected", "blocked", "failed"} <= statuses


# --- 3. Unequal sample comparison shows sufficiency, not raw volume ----------------------------


async def test_unequal_sample_comparison(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    big = await _competitor(noauth_client, pid, "Big")
    small = await _competitor(noauth_client, pid, "Small")

    # Big: 100 distinct pieces but all on ONE channel (shallow breadth).
    big_items = [{"content_format": "social_post", "text": f"عرض ترويجي رقم {i}", "url": f"b{i}"} for i in range(100)]
    await noauth_client.post(
        f"/api/v1/projects/{pid}/competitors/{big}/collect",
        json={"channels": ["instagram"], "items": big_items},
    )
    # Small: 20 distinct pieces on two channels (deeper).
    small_items = [
        {"content_format": "article" if i % 2 else "landing_page", "text": f"شرح مفصل رقم {i}", "url": f"s{i}"}
        for i in range(20)
    ]
    await noauth_client.post(
        f"/api/v1/projects/{pid}/competitors/{small}/collect",
        json={"channels": ["website", "youtube"], "items": small_items},
    )

    big_diag = (await noauth_client.post(f"/api/v1/projects/{pid}/competitors/{big}/diagnosis")).json()
    small_diag = (await noauth_client.post(f"/api/v1/projects/{pid}/competitors/{small}/diagnosis")).json()
    # The larger raw sample does not automatically win: its single-channel + duplicate sample is
    # not rated 'high', while the smaller multi-channel sample is 'medium'.
    assert big_diag["sample_sufficiency"] != "high"
    assert small_diag["sample_sufficiency"] == "medium"
    assert big_diag["audits"]["sample"]["piece_count"] >= small_diag["audits"]["sample"]["piece_count"]


# --- 4. No definitive absence claim ------------------------------------------------------------


async def test_no_definitive_absence_claim(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    cid = await _competitor(noauth_client, pid)
    await noauth_client.post(
        f"/api/v1/projects/{pid}/competitors/{cid}/collect",
        json={"channels": ["website"], "items": [{"content_format": "article", "text": "محتوى بدون تسعير"}]},
    )
    diag = (await noauth_client.post(f"/api/v1/projects/{pid}/competitors/{cid}/diagnosis")).json()
    pricing = next(f for f in diag["findings"] if f["dimension"] == "coverage" and f["subject"] == "pricing")
    assert pricing["presence"] == "not_found_in_sample"
    assert "No evidence of pricing was found in the analyzed public sample" in pricing["summary"]
    # Never a definitive "does not" absence claim anywhere.
    joined = " ".join(f["summary"] for f in diag["findings"]).lower()
    assert "does not" not in joined and "doesn't" not in joined


# --- 5. No inferred commercial performance -----------------------------------------------------


async def test_no_inferred_commercial_performance(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    cid = await _competitor(noauth_client, pid)
    await noauth_client.post(
        f"/api/v1/projects/{pid}/competitors/{cid}/collect",
        json={"channels": ["website"], "items": [{"content_format": "article", "text": "منشور"}]},
    )
    # Even if a 'revenue' record was recorded against the competitor, the diagnosis treats
    # performance as public proxy only and asserts no direct commercial outcome.
    await noauth_client.post(
        f"/api/v1/projects/{pid}/performance/manual",
        json={
            "entity_id": str(cid),
            "metric_name": "revenue",
            "metric_value": 1000,
            "period_start": "2026-01-01",
            "period_end": "2026-01-31",
            "paid_organic_status": "organic",
        },
    )
    diag = (await noauth_client.post(f"/api/v1/projects/{pid}/competitors/{cid}/diagnosis")).json()
    assert diag["audits"]["performance"]["has_direct_outcome"] is False
    perf = [f for f in diag["findings"] if f["dimension"] == "performance"]
    assert perf and perf[0]["is_public_proxy"] is True
    assert "cannot be inferred" in perf[0]["summary"]


# --- 6. Public claim remains a claim; nothing is an observed fact ------------------------------


async def test_public_claim_remains_claim_and_no_observed_fact(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    cid = await _competitor(noauth_client, pid)
    coll = await noauth_client.post(
        f"/api/v1/projects/{pid}/competitors/{cid}/collect",
        json={"channels": ["website"], "items": [{"content_format": "article", "text": "الأفضل في السوق"}]},
    )
    piece_id = next(i["content_piece_id"] for i in coll.json()["items"] if i["content_piece_id"])
    await noauth_client.post(
        f"/api/v1/projects/{pid}/claims",
        json={
            "entity_id": str(cid),
            "content_piece_id": piece_id,
            "claim_text": "الأفضل في السوق",
            "claim_type": "quality",
        },
    )
    diag = (await noauth_client.post(f"/api/v1/projects/{pid}/competitors/{cid}/diagnosis")).json()

    # Mandatory public-evidence limitation banner (§15.1).
    assert "public or uploaded sources" in diag["limitation_banner"]
    # The public claim stays a claim.
    claim_findings = [f for f in diag["findings"] if f["dimension"] == "claim_proof"]
    assert claim_findings and claim_findings[0]["finding_status"] == "brand_claim"
    # Audience/positioning is inference, not observed_fact.
    audience = [f for f in diag["findings"] if f["dimension"] == "audience"]
    assert audience and audience[0]["finding_status"] == "inference"
    # Invariant: NOTHING in a competitor diagnosis is presented as an observed fact.
    assert all(f["finding_status"] != "observed_fact" for f in diag["findings"])
