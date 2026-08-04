"""Deterministic diagnostic-precondition gate (spec §8, and Gate 1 scope validity §21).

Pure function: no DB, no AI. Returns the exact §8.3 response shape. Full analysis stays blocked
until every required field is present; partial work (ingestion/parsing/classification) is allowed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class GateResult:
    status: str  # "pass" | "fail"
    missing_required_fields: list[str]
    warnings: list[str]
    can_run_partial_analysis: bool
    can_run_full_analysis: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "gate": "diagnostic_prerequisites",
            "status": self.status,
            "missing_required_fields": self.missing_required_fields,
            "warnings": self.warnings,
            "can_run_partial_analysis": self.can_run_partial_analysis,
            "can_run_full_analysis": self.can_run_full_analysis,
        }


# Required context fields (spec §8.1) that live on the context version.
_REQUIRED_TEXT = (
    "target_buying_decision",
    "purchase_type",
    "primary_product_or_service",
    "primary_segment_name",
    "primary_segment_definition",
    "primary_decision_maker_role",
    "primary_bottleneck",
    "bottleneck_statement",
)
_REQUIRED_DATES = (
    "analysis_period_start",
    "analysis_period_end",
    "comparison_period_start",
    "comparison_period_end",
)


def evaluate_prerequisites(
    context: dict[str, Any],
    *,
    project_name: str | None,
    has_primary_brand: bool,
) -> GateResult:
    missing: list[str] = []
    warnings: list[str] = []

    if not (project_name and project_name.strip()):
        missing.append("project_name")
    if not has_primary_brand:
        missing.append("brand_entity")

    for field in _REQUIRED_TEXT:
        value = context.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)
    for field in _REQUIRED_DATES:
        if not context.get(field):
            missing.append(field)

    channels = context.get("included_channels") or []
    if not channels:
        missing.append("included_channels")

    # If an A/D/P score is entered it needs >= 2 supporting evidence references (§8.1).
    score_evidence = context.get("score_evidence") or {}
    for key in ("attention", "desire", "persuasion"):
        if context.get(f"{key}_score") is not None:
            refs = score_evidence.get(key) or []
            if len(refs) < 2:
                missing.append(f"{key}_score_evidence")

    # Confidence-improving-but-optional fields → warnings, not blockers.
    if context.get("commercial_value_amount") is None:
        warnings.append("No margin/commercial value; commercial-relevance confidence will be capped at medium.")

    can_full = len(missing) == 0
    return GateResult(
        status="pass" if can_full else "fail",
        missing_required_fields=missing,
        warnings=warnings,
        can_run_partial_analysis=True,
        can_run_full_analysis=can_full,
    )
