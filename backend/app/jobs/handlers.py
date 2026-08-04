"""Job handlers. Real handlers (parse_source, classify_content, run_*_diagnosis, render_report,
purge_project, …) are added in later phases. A configurable `demo` handler exercises the job
mechanics (progress, cancellation, retry classification) for Phase 4 tests."""

from __future__ import annotations

from app.db.models.job import Job
from app.jobs.retry import (
    AmbiguousTimeoutError,
    PermanentValidationError,
    TransientConnectionError,
)
from app.jobs.runner import StageRunner, register

_FAULTS = {
    "transient": TransientConnectionError,
    "timeout": AmbiguousTimeoutError,
    "permanent": PermanentValidationError,
}


@register("classify_content")
async def classify_content_handler(runner: StageRunner, job: Job) -> list[str]:
    import uuid as _uuid

    from sqlalchemy import select

    from app.ai import get_ai_provider
    from app.db.models.content_piece import ContentPiece
    from app.services.classify import classify_piece

    manifest = job.input_manifest or {}
    project_id = _uuid.UUID(manifest["project_id"])
    context_version_id = str(manifest.get("context_version_id", ""))
    provider = get_ai_provider()

    pieces = (
        (
            await runner.session.execute(
                select(ContentPiece).where(
                    ContentPiece.project_id == project_id,
                    ContentPiece.include_in_analysis.is_(True),
                    ContentPiece.is_canonical.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    warnings: list[str] = []
    total = max(1, len(pieces))
    for i, piece in enumerate(pieces):
        await runner.stage(f"classify:{piece.id}", progress=int((i + 1) / total * 100))
        outcome = await classify_piece(runner.session, provider, piece=piece, context_version_id=context_version_id)
        if outcome.status == "needs_review":
            warnings.append(f"needs_review:{piece.id}")
    return warnings


@register("demo")
async def demo_handler(runner: StageRunner, job: Job) -> list[str]:
    manifest = job.input_manifest or {}
    stages: list[str] = manifest.get("stages") or ["stage_a", "stage_b", "stage_c"]
    raise_at = manifest.get("raise_at") or {}
    n = len(stages)
    for i, name in enumerate(stages):
        await runner.stage(name, progress=int((i + 1) / n * 100))
        if raise_at.get("stage") == name:
            exc_cls = _FAULTS.get(raise_at.get("kind", ""), RuntimeError)
            raise exc_cls(f"injected fault at {name}")
    return ["demo_warning"] if manifest.get("warn") else []
