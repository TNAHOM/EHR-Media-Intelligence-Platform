from datetime import datetime, timezone
from typing import Any

from pydantic import ConfigDict, Field
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel

from app.core.schema import AppBaseModel


class ClinicalSummaryBase(SQLModel):
    patient_mrn: str = SQLField(index=True, description="Canonical MRN")
    patient_id: str = SQLField(index=True, description="FHIR Patient Resource ID")
    chief_concern: str = SQLField(description="Primary presenting complaint")
    key_diagnoses: str = SQLField(description="Established or provisional diagnoses")
    recent_media_records: str = SQLField(
        description="Summary of imaging, scans, and labs"
    )
    flagged_anomalies: str = SQLField(description="Critical or abnormal findings")
    word_count: int = SQLField(
        description="Total word count across all 4 summary sections"
    )
    model_used: str = SQLField(description="LLM model identifier")
    disclaimer: str = SQLField(
        default=(
            "AI-generated clinical synthesis for clinician review only. "
            "Not a formal medical diagnosis or diagnostic decision."
        ),
        description="Mandatory clinical safety disclaimer",
    )


class ClinicalSummaryTable(ClinicalSummaryBase, table=True):
    __tablename__: Any = "clinical_summaries"

    id: int | None = SQLField(default=None, primary_key=True)
    content_hash: str = SQLField(
        index=True,
        description="Deterministic hash of patient MRN + Bundle JSON for caching",
    )
    created_at: datetime = SQLField(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))


class ClinicalSummaryRead(ClinicalSummaryBase):
    cache_hit: bool = False
    created_at: datetime


class GeminiClinicalSummaryPayload(AppBaseModel):
    chief_concern: str = Field(
        description="Primary presenting problem or chief complaint"
    )
    key_diagnoses: str = Field(
        description="Known or provisional diagnoses established in records"
    )
    recent_media_records: str = Field(
        description="Summary of recent imaging, scans, and diagnostic lab panels"
    )
    flagged_anomalies: str = Field(
        description="Critical or abnormal findings requiring clinician attention"
    )

    model_config = ConfigDict(extra="ignore")
