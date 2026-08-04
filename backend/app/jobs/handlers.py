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
