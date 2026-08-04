"""Import all models so their tables register on Base.metadata (Alembic + tests)."""

from app.db.models.audit import AuditLog
from app.db.models.brand_diagnosis import BrandDiagnosis, BrandFinding, BrandReadinessScore
from app.db.models.buying_group import BuyingGroupRole
from app.db.models.classification import ContentClassification
from app.db.models.content_piece import ContentPiece, EvidenceSpan
from app.db.models.context import DiagnosticContextVersion
from app.db.models.entity import Entity
from app.db.models.job import Job, JobEvent
from app.db.models.project import Project
from app.db.models.source import Source, SourceSnapshot
from app.db.models.user import User
from app.db.models.voc import Claim, ClaimEvidence, PerformanceRecord, VocEntry

__all__ = [
    "AuditLog",
    "BrandDiagnosis",
    "BrandFinding",
    "BrandReadinessScore",
    "BuyingGroupRole",
    "Claim",
    "ClaimEvidence",
    "ContentClassification",
    "ContentPiece",
    "DiagnosticContextVersion",
    "Entity",
    "EvidenceSpan",
    "Job",
    "JobEvent",
    "PerformanceRecord",
    "Project",
    "Source",
    "SourceSnapshot",
    "User",
    "VocEntry",
]
