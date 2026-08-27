from datetime import datetime, timezone
from typing import Any

from sqlmodel import Field, SQLModel


class FHIRBundleBase(SQLModel):
    id: str = Field(
        primary_key=True, index=True, description="Bundle ID (e.g. bundle-MRN-88401)"
    )
    patient_mrn: str = Field(index=True, description="Canonical Patient MRN")
    patient_id: str = Field(index=True, description="FHIR Patient ID (e.g. pat-88401)")
    patient_name: str = Field(description="Patient Full Name")
    resource_count: int = Field(description="Total FHIR resources inside the bundle")
    validation_status: str = Field(
        default="VALID", description="Schema validation status"
    )


class FHIRBundle(FHIRBundleBase, table=True):
    __tablename__: Any = "fhir_bundles"

    bundle_json: str = Field(description="Serialized HL7 FHIR R4 Bundle JSON payload")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# DTO for API List Responses (Excludes heavy JSON payload for fast listing)
class FHIRBundleRead(FHIRBundleBase):
    created_at: datetime
    updated_at: datetime


class FHIRValidationReport(SQLModel):
    total_patients: int
    total_bundles_created: int
    total_resources_mapped: int
    errors: list[str] = []
