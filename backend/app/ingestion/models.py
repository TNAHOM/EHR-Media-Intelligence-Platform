from datetime import date, datetime, timezone
from typing import Any, Literal, Optional

from sqlmodel import Field, Relationship, SQLModel

GenderType = Literal["male", "female", "other", "unknown"]
RecordCategory = Literal["clinical_note", "discharge_summary", "lab", "imaging"]


class AuditLogBase(SQLModel):
    field_name: str = Field(index=True)
    original_value: str | None = None
    cleaned_value: str | None = None
    transformation_rule: str


class AuditLog(AuditLogBase, table=True):
    __tablename__: Any = "audit_logs"

    id: int | None = Field(default=None, primary_key=True)
    record_id: str = Field(
        foreign_key="clean_records.id",
        index=True,
        ondelete="CASCADE",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Use Optional["CleanRecord"] so SQLAlchemy mapper resolves properly
    record: Optional["CleanRecord"] = Relationship(back_populates="audit_trail")


class CleanRecordBase(SQLModel):
    id: str = Field(primary_key=True, index=True)
    patient_mrn: str = Field(index=True, description="Canonical MRN (e.g., MRN-88401)")
    patient_name: str = Field(description="Normalized Title-cased Full Name")
    dob: date = Field(description="Canonical ISO date (YYYY-MM-DD)")
    gender: str = Field(description="FHIR-compliant administrative gender")
    record_type: str = Field(index=True, description="Categorized clinical record type")
    encounter_date: datetime = Field(index=True, description="UTC ISO timestamp")
    content_text: str = Field(description="Sanitized clinical narrative or findings")
    source_format: str = Field(description="Source file type: json or csv")


class CleanRecord(CleanRecordBase, table=True):
    __tablename__: Any = "clean_records"

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
