"""Import all models so their tables register on Base.metadata (Alembic + tests)."""

from app.db.models.audit import AuditLog
from app.db.models.buying_group import BuyingGroupRole
from app.db.models.content_piece import ContentPiece, EvidenceSpan
from app.db.models.context import DiagnosticContextVersion
from app.db.models.entity import Entity
from app.db.models.job import Job, JobEvent
from app.db.models.project import Project
from app.db.models.source import Source, SourceSnapshot
from app.db.models.user import User

__all__ = [
    "AuditLog",
    "BuyingGroupRole",
    "ContentPiece",
    "DiagnosticContextVersion",
    "Entity",
    "EvidenceSpan",
    "Job",
    "JobEvent",
    "Project",
    "Source",
    "SourceSnapshot",
    "User",
]
