from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ResourceTypeFilter = Literal["DocumentReference", "DiagnosticReport", "ClinicalSummary"]


class SearchQueryRequest(BaseModel):
    query: str = Field(
        description="Natural language search query from clinician", min_length=2
    )
    resource_type: ResourceTypeFilter | None = Field(
        default=None, description="Optional filter by FHIR resource type"
    )
    date_from: date | None = Field(
        default=None, description="Filter records on or after this date (YYYY-MM-DD)"
    )
    date_to: date | None = Field(
        default=None, description="Filter records on or before this date (YYYY-MM-DD)"
    )
    patient_mrn: str | None = Field(
        default=None, description="Optional scope to a single patient MRN"
    )
    limit: int = Field(
        default=5, ge=1, le=50, description="Top-K ranked matches to return (default 5)"
    )

    # strict=False allows parsing ISO date strings ("YYYY-MM-DD") from HTTP JSON requests
    model_config = ConfigDict(strict=False, extra="ignore")


class SearchResultItem(BaseModel):
    record_id: str = Field(description="Internal resource identifier")
    patient_mrn: str = Field(description="Patient MRN")
    patient_name: str = Field(description="Patient Full Name")
    resource_type: str = Field(
        description="FHIR Resource type: DocumentReference, DiagnosticReport, or ClinicalSummary"
    )
    record_type: str = Field(
        description="Clinical category: discharge_summary, lab, imaging, ai_summary"
    )
    record_date: str = Field(description="ISO Date of the record")
    relevance_score: float = Field(
        description="Normalized similarity score from 0.0 to 1.0 (Higher = more relevant)"
    )
    snippet: str = Field(
        description="Highlighted text snippet matching the clinical query"
    )
    full_content: str = Field(
        description="Complete underlying clinical narrative or findings"
    )


class SearchResponse(BaseModel):
    query: str
    total_results: int
    execution_time_ms: float
    results: list[SearchResultItem]


class IndexStats(BaseModel):
    total_indexed_documents: int
    document_references_count: int
    diagnostic_reports_count: int
    clinical_summaries_count: int
    status: str
