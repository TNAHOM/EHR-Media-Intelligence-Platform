from datetime import datetime, timezone
from typing import Any

from sqlmodel import Field as SQLField, SQLModel


class FHIRBundleBase(SQLModel):
    id: str = SQLField(
        primary_key=True, index=True, description="Bundle ID (e.g. bundle-MRN-88401)"
    )
    patient_mrn: str = SQLField(index=True, description="Canonical Patient MRN")
    patient_id: str = SQLField(index=True, description="FHIR Patient ID (e.g. pat-88401)")
    patient_name: str = SQLField(description="Patient Full Name")
    resource_count: int = SQLField(description="Total FHIR resources inside the bundle")
    validation_status: str = SQLField(
        default="VALID", description="Schema validation status"
    )


class FHIRBundle(FHIRBundleBase, table=True):
    __tablename__: Any = "fhir_bundles"

    bundle_json: str = SQLField(description="Serialized HL7 FHIR R4 Bundle JSON payload")
    created_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))


# DTO for API List Responses (Excludes heavy JSON payload for fast listing)
class FHIRBundleRead(FHIRBundleBase):
    created_at: datetime
    updated_at: datetime


class FHIRValidationReport(SQLModel):
    total_patients: int
    total_bundles_created: int
    total_resources_mapped: int
    errors: list[str] = []
