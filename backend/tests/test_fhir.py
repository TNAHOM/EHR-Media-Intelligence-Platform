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
        content_hash="test_hash_patient_001",
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
            content_hash="test_hash_doc_001",
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
            content_hash="test_hash_diag_002",
        ),
    ]

    bundle, errors = FHIRMapper.assemble_patient_bundle("MRN-88401", records)
    assert len(errors) == 0
    assert isinstance(bundle, Bundle)
    assert bundle.type == "collection"

    assert bundle.entry is not None
    assert len(bundle.entry) == 3

    # Entry 0: Patient
    patient_entry = bundle.entry[0].resource
    assert isinstance(patient_entry, Patient)
    patient_ref_id = f"Patient/{patient_entry.id}"

    # Entry 1: DocumentReference referencing Patient
    doc_entry = bundle.entry[1].resource
    assert isinstance(doc_entry, DocumentReference)
    assert doc_entry.subject is not None
    assert doc_entry.subject.reference == patient_ref_id

    # Entry 2: DiagnosticReport referencing Patient
    diag_entry = bundle.entry[2].resource
    assert isinstance(diag_entry, DiagnosticReport)
    assert diag_entry.subject is not None
    assert diag_entry.subject.reference == patient_ref_id


def test_fhir_normalization_pipeline_and_api(session: Session, client: TestClient):
    """End-to-end integration test: Ingest JSON -> Run /fhir/normalize -> Query Bundle Endpoint."""
    raw_ehr_json = """[
      {
        "export_id": "REC-101",
        "patient_mrn": "MRN-11223",
        "patient_full_name": "Gregory House",
        "date_of_birth": "1959-06-11",
        "gender_code": "male",
        "document_type": "clinical_note",
        "encounter_date": "2024-01-10T09:00:00Z",
        "content_body": "Patient presents with severe right leg pain."
      },
      {
        "export_id": "REC-102",
        "patient_mrn": "MRN-11223",
        "patient_full_name": "Gregory House",
        "date_of_birth": "1959-06-11",
        "gender_code": "male",
        "document_type": "lab",
        "encounter_date": "2024-01-11T14:00:00Z",
        "content_body": "Comprehensive Metabolic Panel: All within normal limits."
      }
    ]"""

    # 1. Ingest Raw Records without auto-processing
    ingest_res = IngestionService.ingest_payload(session, raw_ehr_json, "json")
    assert ingest_res.total_cleaned == 2

    # 2. Trigger Normalization Endpoint
    norm_res = client.post("/api/v1/fhir/normalize")
    assert norm_res.status_code == 200
    norm_data = norm_res.json()
    assert norm_data["success"] is True
    assert norm_data["data"]["total_bundles_created"] == 1
    assert norm_data["data"]["total_resources_mapped"] == 3

    # 3. Fetch Generated Bundle by MRN
    bundle_res = client.get("/api/v1/fhir/bundles/MRN-11223")
    assert bundle_res.status_code == 200
    bundle_data = bundle_res.json()["data"]
    assert bundle_data["resourceType"] == "Bundle"
    assert len(bundle_data["entry"]) == 3
