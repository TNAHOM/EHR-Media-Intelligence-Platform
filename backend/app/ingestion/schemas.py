from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.core.schema import AppBaseModel

GenderType = Literal["male", "female", "other", "unknown"]
RecordCategory = Literal["clinical_note", "discharge_summary", "lab", "imaging"]


class AuditLogEntry(AppBaseModel):
    field_name: str
    original_value: str | None = None
    cleaned_value: str | None = None
    transformation_rule: str


class CleanRecord(AppBaseModel):
    id: str = Field(description="Unique record identifier")
    patient_mrn: str = Field(description="Canonical standard MRN (e.g. MRN-88401)")
    patient_name: str = Field(description="Normalized Title-cased Full Name")
    dob: date = Field(description="Canonical ISO date (YYYY-MM-DD)")
    gender: GenderType = Field(description="FHIR-compliant administrative gender")
    record_type: RecordCategory = Field(description="Categorized clinical record type")
    encounter_date: datetime = Field(description="Standardized UTC ISO timestamp")
    content_text: str = Field(description="Sanitized clinical narrative or findings")
    source_format: Literal["json", "csv"]
    audit_trail: list[AuditLogEntry] = Field(default_factory=list)


class IngestionSummary(AppBaseModel):
    total_processed: int
    total_cleaned: int
    total_duplicates_dropped: int
    total_invalid_dropped: int
    records: list[CleanRecord]
    audit_logs_count: int
