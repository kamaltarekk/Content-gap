"""Phase 11 gate — Security, Cost, and Operational Hardening (Section 31 production gates).

Covers the Cost gate (no paid call on page load, budget caps, provider cost logged), the Security
gate (no raw PII in logs, project purge), and PII redaction preview.
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from app.ai.fake_provider import FakeAIProvider
from app.core.log_scrub import ErrorReporter, scrub
from app.core.pii import redact
from app.db.models.content_piece import ContentPiece
from app.db.models.cost_ledger import CostLedgerEntry
from app.db.models.project import Project
from app.db.session import get_sessionmaker
from app.services.classify import classify_piece
from app.services.cost_ledger import BudgetExceeded, check_budget
from tests.conftest import requires_db

pytestmark = [requires_db]


# --- Pure PII + log scrub (no DB) --------------------------------------------------------------


def test_redact_emails_and_phones() -> None:
    text = "Contact ali@example.com or +20 100 123 4567 for the order"
    redacted, counts = redact(text)
    assert counts["emails"] == 1 and counts["phones"] == 1
    assert "ali@example.com" not in redacted
    assert "REDACTED_EMAIL" in redacted and "REDACTED_PHONE" in redacted


def test_scrub_removes_secrets_and_evidence() -> None:
    event = {
        "message": "boom",
        "authorization": "Bearer secret-token-xyz",
        "quoted_text": "verbatim customer evidence that must not leak",
        "note": "reach me at ali@example.com",
        "nested": {"api_key": "fake-provider-key-123", "count": 5},
    }
    out = scrub(event)
    assert out["authorization"] == "[REDACTED]"
    assert out["quoted_text"] == "[REDACTED]"  # evidence text never logged
    assert out["nested"]["api_key"] == "[REDACTED]"
    assert out["nested"]["count"] == 5  # non-sensitive kept
    assert "ali@example.com" not in out["note"]  # PII scrubbed even in free-text fields


def test_error_reporter_scrubs() -> None:
    reporter = ErrorReporter()
    event = reporter.capture("failure", anthropic_api_key="fake-provider-key-xyz", original_text="raw evidence")
    assert event["anthropic_api_key"] == "[REDACTED]"
    assert event["original_text"] == "[REDACTED]"


# --- Fixtures ----------------------------------------------------------------------------------


async def _project(client: AsyncClient) -> uuid.UUID:
    r = await client.post("/api/v1/projects", json={"name": f"ops-{uuid.uuid4().hex[:8]}", "primary_language": "ar"})
    return uuid.UUID(r.json()["id"])


async def _piece(client: AsyncClient, pid: uuid.UUID, text: str = "قارن الأسعار ودراسة حالة") -> uuid.UUID:
    r = await client.post(
        f"/api/v1/projects/{pid}/sources/manual",
        json={"source_category": "brand_owned", "display_name": "p", "text": text, "content_format": "article"},
    )
    return uuid.UUID(r.json()["content_piece_ids"][0])


# --- No paid call on page load -----------------------------------------------------------------


async def test_no_paid_call_on_page_load(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await _piece(noauth_client, pid)
    # Hit read-only "page load" endpoints.
    await noauth_client.get("/api/v1/config/public")
    await noauth_client.get(f"/api/v1/projects/{pid}/summary")
    cost = (await noauth_client.get(f"/api/v1/projects/{pid}/cost")).json()
    assert cost["total_cost_usd"] == 0 and cost["call_count"] == 0


# --- Provider cost is logged in the ledger -----------------------------------------------------


async def test_classification_logs_provider_cost(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    piece_id = await _piece(noauth_client, pid)
    async with get_sessionmaker()() as session:
        piece = await session.get(ContentPiece, piece_id)
        await classify_piece(session, FakeAIProvider(), piece=piece, context_version_id="ctx-1")
        await session.commit()
    cost = (await noauth_client.get(f"/api/v1/projects/{pid}/cost")).json()
    assert cost["call_count"] == 1 and cost["total_cost_usd"] > 0


# --- Budget-cap block --------------------------------------------------------------------------


async def test_budget_cap_blocks_paid_run(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await _piece(noauth_client, pid)
    # Set a cap below already-recorded spend.
    async with get_sessionmaker()() as session:
        session.add(
            CostLedgerEntry(
                project_id=pid,
                task="content_piece_classification",
                model="m",
                input_tokens=1000,
                output_tokens=1000,
                cost_usd=1.0,
                cache_hit=False,
            )
        )
        project = await session.get(Project, pid)
        project.budget_cap_usd = 0.5
        await session.commit()

    run = await noauth_client.post(f"/api/v1/projects/{pid}/classification/run", json={})
    assert run.status_code == 402
    assert "budget_cap_exceeded" in run.json()["error"]["message"].lower()


async def test_check_budget_pure(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    async with get_sessionmaker()() as session:
        project = await session.get(Project, pid)
        project.budget_cap_usd = 1.0
        session.add(
            CostLedgerEntry(
                project_id=pid, task="t", model="m", input_tokens=1, output_tokens=1, cost_usd=2.0, cache_hit=False
            )
        )
        await session.commit()
    async with get_sessionmaker()() as session:
        try:
            await check_budget(session, pid)
            raised = False
        except BudgetExceeded:
            raised = True
    assert raised


# --- PII warning + redaction preview -----------------------------------------------------------


async def test_pii_warning_and_redaction_preview(noauth_client: AsyncClient) -> None:
    warn = (await noauth_client.get("/api/v1/pii/warning")).json()
    assert "PII" in warn["warning"]

    preview = (
        await noauth_client.post(
            "/api/v1/pii/redaction-preview",
            json={"text": "اتصل على ali@example.com أو 01001234567 لإتمام الطلب"},
        )
    ).json()
    assert preview["has_pii"] is True
    assert preview["found"]["emails"] == 1
    assert "ali@example.com" not in preview["preview"]


# --- Project purge removes raw and derived data ------------------------------------------------


async def test_project_purge_removes_all_data(noauth_client: AsyncClient) -> None:
    pid = await _project(noauth_client)
    await _piece(noauth_client, pid)
    # Confirm data exists.
    async with get_sessionmaker()() as session:
        before = (
            (await session.execute(__import__("sqlalchemy").select(ContentPiece).where(ContentPiece.project_id == pid)))
            .scalars()
            .all()
        )
    assert before

    result = (await noauth_client.post(f"/api/v1/projects/{pid}/purge")).json()
    assert result["content_pieces"] >= 1

    # Project and all derived rows are gone.
    assert (await noauth_client.get(f"/api/v1/projects/{pid}")).status_code == 404
    async with get_sessionmaker()() as session:
        after = (
            (await session.execute(__import__("sqlalchemy").select(ContentPiece).where(ContentPiece.project_id == pid)))
            .scalars()
            .all()
        )
        assert after == []
