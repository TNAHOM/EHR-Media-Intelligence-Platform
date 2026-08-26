from app.ingestion.cleaners import ClinicalDataCleaner
from app.ingestion.models import CleanRecord
from app.ingestion.service import IngestionService
from fastapi.testclient import TestClient
from sqlmodel import Session, select


def test_date_cleaning_variations():
    """Edge Case 1: Standardizes multiple date variations and handles corrupt dates."""
    dob1, log1 = ClinicalDataCleaner.parse_dob("04/12/1982")
    assert str(dob1) == "1982-04-12"
    assert log1 is not None

    dob2, log2 = ClinicalDataCleaner.parse_dob("12-May-1990")
    assert str(dob2) == "1990-05-12"
    assert log2 is not None

    dob3, log3 = ClinicalDataCleaner.parse_dob("corrupted_value_123")
    assert dob3 is None
    assert log3 is None


def test_duplicate_record_deduplication(session: Session):
    """Edge Case 2: Deduplicates identical patient clinical narratives."""
    sample_json = """
    [
      {
        "export_id": "REC-001",
        "patient_mrn": "MRN-88401",
        "patient_full_name": "Eleanor Vance",
        "date_of_birth": "1982-04-12",
        "gender_code": "female",
        "encounter_date": "2024-01-15T10:00:00Z",
        "content_body": "Patient presents with persistent cough."
      },
      {
        "export_id": "REC-002",
        "patient_mrn": "MRN-88401",
        "patient_full_name": "Eleanor Vance",
        "date_of_birth": "1982-04-12",
        "gender_code": "female",
        "encounter_date": "2024-01-15T10:00:00Z",
        "content_body": "Patient presents with persistent cough."
      }
    ]
    """
    summary = IngestionService.ingest_payload(session, sample_json, "json")
    assert summary.total_cleaned == 1
    assert summary.total_duplicates_dropped == 1

    stored = session.exec(select(CleanRecord)).all()
    assert len(stored) == 1
    assert stored[0].id == "REC-001"


def test_missing_identifiers_and_gender_mapping(session: Session):
    """Edge Case 3: Drops records missing mandatory MRNs and strictly normalizes gender."""
    sample_csv = """record_id,mrn,patient_name,birth_date,gender,category,recorded_date,clinical_text
CSV-01,,No MRN Patient,1980-01-01,Male,lab,2024-02-01,Normal report
CSV-02,MRN-99120,Valid Patient,1980-01-01,Woman,lab,2024-02-01,Normal report
"""
    summary = IngestionService.ingest_payload(session, sample_csv, "csv")
    assert summary.total_cleaned == 1
    assert summary.total_invalid_dropped == 1

    record = session.get(CleanRecord, "CSV-02")
    assert record is not None
    assert record.gender == "female"
    assert len(record.audit_trail) > 0
    assert any(log.field_name == "gender" for log in record.audit_trail)


def test_api_upload_and_pagination(client: TestClient):
    """Integration Test: Tests file upload endpoint, pagination, and audit log endpoint."""
    test_json = b"""[
      {
        "export_id": "REC-API-01",
        "patient_mrn": "MRN-55555",
        "patient_full_name": "Integration Test Patient",
        "date_of_birth": "1995-05-10",
        "gender_code": "M",
        "encounter_date": "2024-03-01T08:00:00Z",
        "content_body": "Normal lab findings."
      }
    ]"""

    # 1. Test Upload
    response = client.post(
        "/api/v1/ingest/upload",
        files={"file": ("test.json", test_json, "application/json")},
    )
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["data"]["total_cleaned"] == 1

    # 2. Test Paginated Records
    paged_res = client.get("/api/v1/records?page=1&page_size=10&mrn=MRN-55555")
    assert paged_res.status_code == 200
    paged_data = paged_res.json()
    assert paged_data["pagination"]["total_records"] == 1
    assert paged_data["data"][0]["patient_mrn"] == "MRN-55555"

    # 3. Test Audit Log
    audit_res = client.get("/api/v1/audit-logs/REC-API-01")
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert len(audit_data["data"]) > 0
