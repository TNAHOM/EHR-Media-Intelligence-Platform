from datetime import date, datetime, timezone
from typing import Literal, Optional, Any

from sqlmodel import Field as SQLField, Relationship, SQLModel

from app.fhir.models import FHIRBundleRead, FHIRValidationReport

GenderType = Literal["male", "female", "other", "unknown"]
RecordCategory = Literal["clinical_note", "discharge_summary", "lab", "imaging"]


class AuditLogBase(SQLModel):
    field_name: str = SQLField(index=True)
    original_value: str | None = None
    cleaned_value: str | None = None
    transformation_rule: str


class AuditLog(AuditLogBase, table=True):
    __tablename__: Any = "audit_logs"

    id: int | None = SQLField(default=None, primary_key=True)
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
    id: str = SQLField(primary_key=True, index=True)
    patient_mrn: str = SQLField(index=True, description="Canonical MRN (e.g., MRN-88401)")
    patient_name: str = SQLField(description="Normalized Title-cased Full Name")
    dob: date = SQLField(description="Canonical ISO date (YYYY-MM-DD)")
    gender: str = SQLField(description="FHIR-compliant administrative gender")
    record_type: str = SQLField(index=True, description="Categorized clinical record type")
    encounter_date: datetime = SQLField(index=True, description="UTC ISO timestamp")
    content_text: str = SQLField(description="Sanitized clinical narrative or findings")
    source_format: str = SQLField(description="Source file type: json or csv")


class CleanRecord(CleanRecordBase, table=True):
    __tablename__: Any = "clean_records"

    created_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))

    audit_trail: list[AuditLog] = Relationship(
        back_populates="record",
        cascade_delete=True,
    )


# DTO Schemas for API Serialization
class AuditLogRead(AuditLogBase):
    id: int
    record_id: str
    created_at: datetime


class CleanRecordRead(CleanRecordBase):
    created_at: datetime
    audit_trail: list[AuditLogRead] = []


class IngestionSummary(SQLModel):
    total_processed: int
    total_cleaned: int
    total_duplicates_dropped: int
    total_invalid_dropped: int
    records: list[CleanRecordRead]
    audit_logs_count: int


# Composite DTO for Unified Ingest + FHIR Pipeline Response
class IngestAndProcessResponse(SQLModel):
    ingestion: IngestionSummary
    fhir_normalization: FHIRValidationReport | None = None
    bundles: list[FHIRBundleRead] | None = None
