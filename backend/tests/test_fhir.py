from datetime import date, datetime, timezone

from app.fhir.mapper import FHIRMapper
from app.ingestion.models import CleanRecord
from app.ingestion.service import IngestionService
from fastapi.testclient import TestClient
from fhir.resources.bundle import Bundle
from fhir.resources.diagnosticreport import DiagnosticReport
from fhir.resources.documentreference import DocumentReference
from fhir.resources.patient import Patient
from sqlmodel import Session


def test_fhir_patient_mapping():
    """Validates that CleanRecord maps to a valid HL7 FHIR R4 Patient resource."""
    record = CleanRecord(
        id="REC-001",
        patient_mrn="MRN-88401",
        patient_name="Eleanor Vance",
        dob=date(1982, 4, 12),
        gender="female",
        record_type="discharge_summary",
        encounter_date=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
        content_text="Patient admitted for chest pain.",
        source_format="json",
    )

    patient = FHIRMapper.build_patient_resource(record)
    assert isinstance(patient, Patient)
    assert patient.gender == "female"
    assert str(patient.birthDate) == "1982-04-12"

    assert patient.identifier is not None
    assert patient.identifier[0].value == "MRN-88401"

    assert patient.name is not None
    assert patient.name[0].family == "Vance"
    assert patient.name[0].given is not None
    assert patient.name[0].given[0] == "Eleanor"


def test_fhir_bundle_assembly_and_reference_integrity():
    """Validates that DocumentReference and DiagnosticReport correctly reference the Patient."""
    records = [
        CleanRecord(
            id="REC-001",
            patient_mrn="MRN-88401",
            patient_name="Eleanor Vance",
            dob=date(1982, 4, 12),
            gender="female",
            record_type="discharge_summary",
            encounter_date=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
            content_text="Patient discharged on Beta-blockers.",
            source_format="json",
        ),
        CleanRecord(
            id="REC-002",
            patient_mrn="MRN-88401",
            patient_name="Eleanor Vance",
            dob=date(1982, 4, 12),
            gender="female",
            record_type="imaging",
            encounter_date=datetime(2024, 1, 16, 11, 0, tzinfo=timezone.utc),
            content_text="Chest X-Ray shows mild cardiomegaly.",
            source_format="json",
        ),
    ]

    bundle, errors = FHIRMapper.assemble_patient_bundle("MRN-88401", records)
    assert len(errors) == 0
    assert isinstance(bundle, Bundle)
    assert bundle.type == "collection"

    assert bundle.entry is not None
    assert len(bundle.entry) == 3

    patient_res = bundle.entry[0].resource
    doc_res = bundle.entry[1].resource
    diag_res = bundle.entry[2].resource

    assert isinstance(patient_res, Patient)
    assert isinstance(doc_res, DocumentReference)
    assert isinstance(diag_res, DiagnosticReport)

    expected_ref = f"Patient/{patient_res.id}"
    assert doc_res.subject is not None
    assert doc_res.subject.reference == expected_ref

    assert diag_res.subject is not None
    assert diag_res.subject.reference == expected_ref


def test_fhir_normalization_pipeline_and_api(session: Session, client: TestClient):
    """End-to-end integration test: Ingest raw data -> Normalize to FHIR -> Query via API."""
    sample_json = """[
      {
        "export_id": "REC-101",
        "patient_mrn": "MRN-12345",
        "patient_full_name": "John Doe",
        "date_of_birth": "1975-08-20",
        "gender_code": "male",
        "document_type": "discharge_summary",
        "encounter_date": "2024-02-01T09:00:00Z",
        "content_body": "Patient recovering well."
      },
      {
        "export_id": "REC-102",
        "patient_mrn": "MRN-12345",
        "patient_full_name": "John Doe",
        "date_of_birth": "1975-08-20",
        "gender_code": "male",
        "document_type": "lab",
        "encounter_date": "2024-02-02T10:00:00Z",
        "content_body": "HbA1c 6.5%"
      }
    ]"""

    # Ingest clean records
    IngestionService.ingest_payload(session, sample_json, "json")

    # 1. Trigger FHIR Normalization API
    norm_res = client.post("/api/v1/fhir/normalize")
    assert norm_res.status_code == 200
    norm_data = norm_res.json()
    assert norm_data["success"] is True
    assert norm_data["data"]["total_bundles_created"] == 1
    assert norm_data["data"]["total_resources_mapped"] == 3

    # 2. Query paginated bundles
    bundles_res = client.get("/api/v1/fhir/bundles")
    assert bundles_res.status_code == 200
    bundles_data = bundles_res.json()
    assert bundles_data["pagination"]["total_records"] == 1
    assert bundles_data["data"][0]["patient_mrn"] == "MRN-12345"

    # 3. Retrieve raw FHIR Bundle JSON
    bundle_json_res = client.get("/api/v1/fhir/bundles/MRN-12345")
    assert bundle_json_res.status_code == 200
    raw_bundle = bundle_json_res.json()["data"]
    assert raw_bundle["resourceType"] == "Bundle"
    assert len(raw_bundle["entry"]) == 3
