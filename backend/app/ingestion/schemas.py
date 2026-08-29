from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.core.schema import AppBaseModel
from app.fhir.models import FHIRBundleRead, FHIRValidationReport

GenderType = Literal["male", "female", "other", "unknown"]
RecordCategory = Literal["clinical_note", "discharge_summary", "lab", "imaging"]


class AuditLogEntry(AppBaseModel):
    field_name: str
    original_value: str | None = None
    cleaned_value: str | None = None
    transformation_rule: str


class AuditLogRead(AppBaseModel):
    id: str
    record_id: str
    field_name: str
    original_value: str | None = None
    cleaned_value: str | None = None
    transformation_rule: str
    created_at: datetime


class CleanRecordRead(AppBaseModel):
    id: str
    patient_mrn: str
    patient_name: str
    dob: date
    gender: str
    record_type: str
    encounter_date: datetime
    content_text: str
    source_format: str
    content_hash: str
    created_at: datetime
    audit_trail: list[AuditLogRead] = Field(default_factory=list)


class IngestionSummary(AppBaseModel):
    total_processed: int
    total_cleaned: int
    total_duplicates_dropped: int
    total_invalid_dropped: int
    records: list[CleanRecordRead] = Field(default_factory=list)
    audit_logs_count: int


class IngestAndProcessResponse(AppBaseModel):
    ingestion: IngestionSummary
    fhir_normalization: FHIRValidationReport | None = None
    bundles: list[FHIRBundleRead] | None = None
