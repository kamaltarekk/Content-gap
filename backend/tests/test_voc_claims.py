"""Phase 6 gate — Voice of Customer, claims/proof, and performance records.

Acceptance gate (spec §27, Phase 6): "VoC, claims, proof, and performance records remain
traceable and cannot be promoted from proxy or claim to fact without evidence."
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from tests.conftest import requires_db

pytestmark = [requires_db]

# A verbatim Arabic complaint. It must round-trip byte-for-byte — never rewritten or transliterated.
ARABIC_PHRASE = "التطبيق بطيء جدًا ويتعطل عند كل عملية دفع"


async def _project(client: AsyncClient) -> uuid.UUID:
    r = await client.post("/api/v1/projects", json={"name": f"voc-{uuid.uuid4().hex[:8]}", "primary_language": "ar"})
    return uuid.UUID(r.json()["id"])


async def _entity(client: AsyncClient, pid: uuid.UUID) -> uuid.UUID:
    r = await client.post(
        f"/api/v1/projects/{pid}/entities",
        json={"entity_type": "brand", "name": f"brand-{uuid.uuid4().hex[:6]}"},
    )
    return uuid.UUID(r.json()["id"])


async def _piece_and_span(client: AsyncClient, pid: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    r = await client.post(
        f"/api/v1/projects/{pid}/sources/manual",
        json={
            "source_category": "brand_owned",
            "display_name": "c",
            "text": "نص للادعاء",
            "content_format": "social_post",
        },
    )
    piece_id = uuid.UUID(r.json()["content_piece_ids"][0])
    spans = (await client.get(f"/api/v1/content/{piece_id}/evidence")).json()
    return piece_id, uuid.UUID(spans[0]["id"])


# --- 1. Verbatim preservation -----------------------------------------------------------------


async def test_voc_phrase_stored_verbatim(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    r = await noauth_client.post(
        f"/api/v1/projects/{pid}/voc/manual",
        json={"bank_type": "complaint", "verbatim_phrase": ARABIC_PHRASE},
    )
    assert r.status_code == 201
    assert r.json()["verbatim_phrase"] == ARABIC_PHRASE  # byte-for-byte, no rewrite/transliteration
    listed = (await noauth_client.get(f"/api/v1/projects/{pid}/voc")).json()
    assert listed[0]["verbatim_phrase"] == ARABIC_PHRASE


# --- 2. Repetition detection: 3 identical phrases confirm a pattern ---------------------------


async def test_three_occurrences_confirm_pattern(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    for _ in range(3):
        await noauth_client.post(
            f"/api/v1/projects/{pid}/voc/manual",
            json={"bank_type": "complaint", "verbatim_phrase": ARABIC_PHRASE},
        )
    entries = (await noauth_client.get(f"/api/v1/projects/{pid}/voc")).json()
    assert all(e["occurrence_count"] == 3 for e in entries)  # every sibling reflects the total
    banks = (await noauth_client.get(f"/api/v1/projects/{pid}/voc/language-banks")).json()
    complaint = next(b for b in banks if b["bank_type"] == "complaint")
    assert len(complaint["confirmed_patterns"]) == 1  # >= voc_pattern_confirm_min (3)


# --- 3. High-confidence bank requires >= 10 approved phrases ----------------------------------


async def test_language_bank_high_confidence_threshold(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    ids: list[str] = []
    for i in range(10):
        r = await noauth_client.post(
            f"/api/v1/projects/{pid}/voc/manual",
            json={"bank_type": "motivation", "verbatim_phrase": f"دافع الشراء رقم {i}"},
        )
        ids.append(r.json()["id"])

    banks = (await noauth_client.get(f"/api/v1/projects/{pid}/voc/language-banks")).json()
    bank = next(b for b in banks if b["bank_type"] == "motivation")
    assert bank["phrase_count"] == 10 and bank["approved_count"] == 0
    assert bank["confidence"] == "low"  # phrases exist but none approved yet

    for voc_id in ids:
        assert (await noauth_client.post(f"/api/v1/voc/{voc_id}/approve")).status_code == 200
    banks = (await noauth_client.get(f"/api/v1/projects/{pid}/voc/language-banks")).json()
    bank = next(b for b in banks if b["bank_type"] == "motivation")
    assert bank["approved_count"] == 10 and bank["confidence"] == "high"


# --- 4. A claim starts unsupported and cannot be promoted to fact without evidence ------------


async def test_claim_cannot_be_promoted_to_fact_without_evidence(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    entity_id = await _entity(noauth_client, pid)
    piece_id, _span = await _piece_and_span(noauth_client, pid)
    r = await noauth_client.post(
        f"/api/v1/projects/{pid}/claims",
        json={
            "entity_id": str(entity_id),
            "content_piece_id": str(piece_id),
            "claim_text": "الأسرع في السوق",
            "claim_type": "speed",
        },
    )
    assert r.status_code == 201
    claim = r.json()
    assert claim["proof_status"] == "unsupported"
    assert claim["finding_status"] == "brand_claim"

    # Promotion to observed_fact must be refused while there is no supporting evidence.
    blocked = await noauth_client.post(
        f"/api/v1/claims/{claim['id']}/promote", json={"finding_status": "observed_fact"}
    )
    assert blocked.status_code == 422


async def test_claim_promotes_to_fact_once_supported(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    entity_id = await _entity(noauth_client, pid)
    piece_id, span_id = await _piece_and_span(noauth_client, pid)
    claim_id = (
        await noauth_client.post(
            f"/api/v1/projects/{pid}/claims",
            json={
                "entity_id": str(entity_id),
                "content_piece_id": str(piece_id),
                "claim_text": "نتائج مثبتة",
                "claim_type": "quality",
            },
        )
    ).json()["id"]

    ev = await noauth_client.post(
        f"/api/v1/claims/{claim_id}/evidence",
        json={
            "evidence_span_id": str(span_id),
            "proof_type": "case_study",
            "evidence_role": "supports",
            "quality_score": 9,
        },
    )
    assert ev.status_code == 201 and ev.json()["proof_status"] == "proven"
    promoted = await noauth_client.post(f"/api/v1/claims/{claim_id}/promote", json={"finding_status": "observed_fact"})
    assert promoted.status_code == 200 and promoted.json()["finding_status"] == "observed_fact"


# --- 5. Contradictory evidence flips proof_status to contradicted -----------------------------


async def test_contradictory_evidence_marks_claim_contradicted(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    entity_id = await _entity(noauth_client, pid)
    piece_id, span_id = await _piece_and_span(noauth_client, pid)
    claim_id = (
        await noauth_client.post(
            f"/api/v1/projects/{pid}/claims",
            json={
                "entity_id": str(entity_id),
                "content_piece_id": str(piece_id),
                "claim_text": "متوفر ٢٤ ساعة",
                "claim_type": "convenience",
            },
        )
    ).json()["id"]

    r = await noauth_client.post(
        f"/api/v1/claims/{claim_id}/evidence",
        json={
            "evidence_span_id": str(span_id),
            "proof_type": "customer_review",
            "evidence_role": "contradicts",
            "quality_score": 8,
        },
    )
    assert r.status_code == 201 and r.json()["proof_status"] == "contradicted"
    # A contradicted claim can never be promoted to observed_fact.
    blocked = await noauth_client.post(f"/api/v1/claims/{claim_id}/promote", json={"finding_status": "observed_fact"})
    assert blocked.status_code == 422


# --- 6. Engagement metrics are proxies; commercial metrics are not ----------------------------


async def test_performance_proxy_classification(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    entity_id = await _entity(noauth_client, pid)

    async def add(metric: str, status: str = "organic") -> dict:
        return (
            await noauth_client.post(
                f"/api/v1/projects/{pid}/performance/manual",
                json={
                    "entity_id": str(entity_id),
                    "metric_name": metric,
                    "metric_value": 100,
                    "period_start": "2026-01-01",
                    "period_end": "2026-01-31",
                    "paid_organic_status": status,
                },
            )
        ).json()

    assert (await add("views"))["is_proxy"] is True
    assert (await add("mystery_metric"))["is_proxy"] is True  # unknown metric stays a proxy
    assert (await add("revenue"))["is_proxy"] is False  # commercial outcome is not a proxy


# --- 7. Performance validation warns on mixed paid/organic and incompatible periods -----------


async def test_performance_validation_warnings(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    entity_id = await _entity(noauth_client, pid)

    async def add(metric: str, status: str, start: str, end: str) -> None:
        await noauth_client.post(
            f"/api/v1/projects/{pid}/performance/manual",
            json={
                "entity_id": str(entity_id),
                "metric_name": metric,
                "metric_value": 10,
                "period_start": start,
                "period_end": end,
                "paid_organic_status": status,
            },
        )

    # Same metric, paid and organic — must be kept separate, not summed.
    await add("reach", "paid", "2026-01-01", "2026-01-31")
    await add("reach", "organic", "2026-01-01", "2026-01-31")
    # Same metric, two different periods — cannot be aggregated without normalization.
    await add("clicks", "organic", "2026-01-01", "2026-01-31")
    await add("clicks", "organic", "2026-02-01", "2026-02-28")

    v = (await noauth_client.get(f"/api/v1/projects/{pid}/performance/validation")).json()
    joined = " ".join(v["warnings"])
    assert "paid_and_organic_mixed:reach" in joined
    assert "incompatible_periods:clicks" in joined
    assert len(v["paid"]) == 1 and len(v["organic"]) == 3
