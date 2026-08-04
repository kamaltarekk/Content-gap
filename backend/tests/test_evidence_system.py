from __future__ import annotations

import io

import pytest
from httpx import AsyncClient

from tests.conftest import requires_db

pytestmark = [requires_db, pytest.mark.asyncio]


async def _project(client: AsyncClient) -> str:
    r = await client.post("/api/v1/projects", json={"name": "مشروع أدلة", "primary_language": "ar"})
    return r.json()["id"]


def _text_pdf(pages_text: list[str | None]) -> bytes:
    """Build a PDF; None page = blank (image-only/empty)."""
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for text in pages_text:
        if text:
            c.drawString(72, 720, text)
        c.showPage()
    c.save()
    return buf.getvalue()


async def test_csv_import_creates_one_source_one_snapshot_many_pieces(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    rows = "text,platform\n" + "\n".join(f"post number {i} about water,instagram" for i in range(20))
    files = {"file": ("posts.csv", rows.encode("utf-8"), "text/csv")}
    data = {"text_column": "text", "source_category": "brand_owned", "content_format": "social_post"}
    r = await noauth_client.post(f"/api/v1/projects/{pid}/sources/csv/import", files=files, data=data)
    assert r.status_code == 201, r.text
    assert r.json()["content_piece_count"] == 20

    sources = (await noauth_client.get(f"/api/v1/projects/{pid}/sources")).json()
    assert len(sources) == 1
    detail = (await noauth_client.get(f"/api/v1/sources/{sources[0]['id']}")).json()
    assert len(detail["snapshots"]) == 1
    content = (await noauth_client.get(f"/api/v1/projects/{pid}/content")).json()
    assert len(content) == 20


async def test_arabic_bom_csv_with_arabic_headers(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    # UTF-8 BOM + Arabic header column.
    csv_text = "النص,المنصة\nالفلتر غالي جدا,انستغرام\nمياه نقية لعائلتك,فيسبوك\n"
    payload = ("﻿" + csv_text).encode("utf-8")
    # Preview surfaces the Arabic headers for explicit mapping.
    preview = await noauth_client.post(
        f"/api/v1/projects/{pid}/sources/csv/preview", files={"file": ("ar.csv", payload, "text/csv")}
    )
    assert "النص" in preview.json()["headers"]
    r = await noauth_client.post(
        f"/api/v1/projects/{pid}/sources/csv/import",
        files={"file": ("ar.csv", payload, "text/csv")},
        data={"text_column": "النص", "source_category": "customer_voice", "content_format": "social_post"},
    )
    assert r.json()["content_piece_count"] == 2
    content = (await noauth_client.get(f"/api/v1/projects/{pid}/content")).json()
    texts = {c["original_text"] for c in content}
    assert "الفلتر غالي جدا" in texts  # Arabic preserved verbatim, BOM stripped


async def test_partial_pdf_reports_warnings(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    pdf = _text_pdf(["Page one has real text about filters", None])  # 2nd page blank/image-only
    r = await noauth_client.post(
        f"/api/v1/projects/{pid}/sources/upload",
        files={"file": ("mixed.pdf", pdf, "application/pdf")},
        data={"source_category": "brand_owned", "content_format": "article"},
    )
    assert r.status_code == 201
    assert r.json()["extraction_quality"] == "partial"
    assert any("image_only" in w for w in r.json()["warnings"])


async def test_image_only_pdf_not_silently_complete(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    pdf = _text_pdf([None, None])  # no embedded text at all
    r = await noauth_client.post(
        f"/api/v1/projects/{pid}/sources/upload",
        files={"file": ("scan.pdf", pdf, "application/pdf")},
        data={"source_category": "brand_owned", "content_format": "article"},
    )
    assert r.status_code == 201
    assert r.json()["extraction_quality"] == "unreadable"  # never reported as complete
    assert r.json()["content_piece_count"] == 0  # no fabricated empty content piece


async def test_unsupported_mime_rejected(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    r = await noauth_client.post(
        f"/api/v1/projects/{pid}/sources/upload",
        files={"file": ("evil.bin", b"\x00\x01\x02", "application/octet-stream")},
        data={"source_category": "brand_owned", "content_format": "article"},
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


async def test_manual_text_size_limit(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    big = "ا" * 10_001  # over the 10,000-char manual-text limit
    r = await noauth_client.post(
        f"/api/v1/projects/{pid}/sources/manual",
        json={"source_category": "customer_voice", "display_name": "big", "text": big, "content_format": "other"},
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "MANUAL_TEXT_TOO_LONG"


async def test_duplicate_grouping_keeps_both_originals(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    original = "الفلتر يوفر مياه نقية لعائلتك"
    repost = "  الفلتر   يوفر مياه نقية لعائلتك  "  # near-duplicate: whitespace only
    for txt in (original, repost):
        await noauth_client.post(
            f"/api/v1/projects/{pid}/sources/manual",
            json={
                "source_category": "brand_owned",
                "display_name": "post",
                "text": txt,
                "content_format": "social_post",
            },
        )
    content = (await noauth_client.get(f"/api/v1/projects/{pid}/content")).json()
    assert len(content) == 2  # both originals remain accessible
    canonical = [c for c in content if c["is_canonical"]]
    dupes = [c for c in content if not c["is_canonical"]]
    assert len(canonical) == 1 and len(dupes) == 1
    assert canonical[0]["duplicate_group_id"] == dupes[0]["duplicate_group_id"]
    groups = (await noauth_client.get(f"/api/v1/projects/{pid}/duplicates")).json()
    assert len(groups) == 1 and len(groups[0]["members"]) == 2


async def test_source_to_evidence_trace_and_separate_texts(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    text = "مياه   صحية   لأطفالك"  # extra spaces so normalized != original
    r = await noauth_client.post(
        f"/api/v1/projects/{pid}/sources/manual",
        json={"source_category": "brand_owned", "display_name": "p", "text": text, "content_format": "social_post"},
    )
    piece_id = r.json()["content_piece_ids"][0]
    piece = (await noauth_client.get(f"/api/v1/content/{piece_id}")).json()
    # Original and normalized are separate (spec gate).
    assert piece["original_text"] == text
    assert piece["normalized_text"] == "مياه صحية لأطفالك"
    assert piece["original_text"] != piece["normalized_text"]

    evidence = (await noauth_client.get(f"/api/v1/content/{piece_id}/evidence")).json()
    assert len(evidence) >= 1
    assert evidence[0]["quoted_text"] == text  # verbatim
    ctx = (await noauth_client.get(f"/api/v1/evidence/{evidence[0]['id']}/source-context")).json()
    # Navigate to the exact source snapshot from the evidence span.
    assert ctx["source_snapshot_id"] == piece["source_snapshot_id"]
    assert ctx["source_id"]
