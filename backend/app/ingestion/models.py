from datetime import date, datetime, timezone
from typing import Any, Optional

from app.core.typeid import TypeIDPrefix, generate_id
from app.ingestion.schemas import (
    AuditLogEntry,
    AuditLogRead,
    CleanRecordRead,
    GenderType,
    IngestAndProcessResponse,
    IngestionSummary,
    RecordCategory,
)
from sqlmodel import Field as SQLField
from sqlmodel import Relationship, SQLModel


class AuditLogBase(SQLModel):
    field_name: str = SQLField(index=True)
    original_value: str | None = None
    cleaned_value: str | None = None
    transformation_rule: str


class AuditLog(AuditLogBase, table=True):
    __tablename__: Any = "audit_logs"

    id: str = SQLField(
        default_factory=lambda: generate_id(TypeIDPrefix.AUDIT),
        primary_key=True,
        description="Audit Log TypeID (e.g. audit_01j7...)",
    )
    record_id: str = SQLField(
        foreign_key="clean_records.id",
        index=True,
        ondelete="CASCADE",
    )
    created_at: datetime = SQLField(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
    )

    record: Optional["CleanRecord"] = Relationship(back_populates="audit_trail")


class CleanRecordBase(SQLModel):
    id: str = SQLField(
        default_factory=lambda: generate_id(TypeIDPrefix.RECORD),
        primary_key=True,
        index=True,
        description="Clean Record TypeID (e.g. rec_01j7...)",
    )
    patient_mrn: str = SQLField(
        index=True, description="Canonical MRN (e.g., MRN-88401)"
    )
    patient_name: str = SQLField(description="Normalized Title-cased Full Name")
    dob: date = SQLField(description="Canonical ISO date (YYYY-MM-DD)")
    gender: str = SQLField(description="FHIR-compliant administrative gender")
    record_type: str = SQLField(
        index=True, description="Categorized clinical record type"
    )
    encounter_date: datetime = SQLField(index=True, description="UTC ISO timestamp")
    content_text: str = SQLField(description="Sanitized clinical narrative or findings")
    source_format: str = SQLField(description="Source file type: json or csv")
    content_hash: str = SQLField(
        default="",
        index=True,
        description="SHA-256 fingerprint for deduplication",
    )


class CleanRecord(CleanRecordBase, table=True):
    __tablename__: Any = "clean_records"

    created_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))

    audit_trail: list[AuditLog] = Relationship(
        back_populates="record",
        cascade_delete=True,
    )


__all__ = [
    "AuditLogBase",
    "AuditLog",
    "CleanRecordBase",
    "CleanRecord",
    "GenderType",
    "RecordCategory",
    "AuditLogEntry",
    "AuditLogRead",
    "CleanRecordRead",
    "IngestionSummary",
    "IngestAndProcessResponse",
]
