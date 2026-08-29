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


def test_api_upload_and_auto_orchestration(client: TestClient):
    """Integration Test: Tests unified upload + automatic FHIR generation (auto_process=True)."""
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

    # 1. Test Upload with default auto_process=True
    response = client.post(
        "/api/v1/ingest/upload?auto_process=true",
        files={"file": ("test.json", test_json, "application/json")},
    )
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["data"]["ingestion"]["total_cleaned"] == 1
    assert res_data["data"]["fhir_normalization"]["total_bundles_created"] == 1
    assert len(res_data["data"]["bundles"]) == 1
    assert res_data["data"]["bundles"][0]["patient_mrn"] == "MRN-55555"

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


def test_api_upload_csv_auto_orchestration(client: TestClient):
    """Integration Test: Validates that uploading a .csv file functions identically to .json,

    including automatic FHIR normalization, bundle creation, and vector index update.
    """
    test_csv = b"""patient_mrn,patient_full_name,date_of_birth,gender_code,document_type,encounter_date,content_body
MRN-CSV-7701,Elena Rostova,1988-03-22,female,discharge_summary,2024-02-10T11:00:00Z,"Patient admitted with acute exacerbation of asthma. Treated with albuterol nebulizers and oral prednisone."
MRN-CSV-7701,Elena Rostova,1988-03-22,female,imaging,2024-02-11T09:00:00Z,"Chest Radiograph PA: Lung hyperinflation noted without acute focal consolidation or pneumothorax."
MRN-CSV-8802,Dmitri Volkov,1972-11-04,male,lab,2024-02-12T14:30:00Z,"Basic Metabolic Panel: Sodium 140 mEq/L, Potassium 4.2 mEq/L, Creatinine 0.9 mg/dL. All normal."
"""

    # 1. Post CSV upload with auto_process=True
    response = client.post(
        "/api/v1/ingest/upload?auto_process=true",
        files={"file": ("clinical_records.csv", test_csv, "text/csv")},
    )
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["data"]["ingestion"]["total_cleaned"] == 3
    assert res_data["data"]["fhir_normalization"]["total_bundles_created"] == 2
    assert res_data["data"]["fhir_normalization"]["total_resources_mapped"] == 5

    # 2. Verify Paginated Records query for the CSV patient
    paged_res = client.get("/api/v1/records?page=1&page_size=10&mrn=MRN-CSV-7701")
    assert paged_res.status_code == 200
    paged_data = paged_res.json()
    assert paged_data["pagination"]["total_records"] == 2
    records = paged_data["data"]
    assert all(r["patient_mrn"] == "MRN-CSV-7701" for r in records)
    assert any(r["record_type"] == "discharge_summary" for r in records)
    assert any(r["record_type"] == "imaging" for r in records)

    # 3. Verify FHIR Bundle endpoint for CSV-ingested patient
    bundle_res = client.get("/api/v1/fhir/bundles/MRN-CSV-7701")
    assert bundle_res.status_code == 200
    bundle_data = bundle_res.json()["data"]
    assert bundle_data["resourceType"] == "Bundle"
    assert len(bundle_data["entry"]) == 3  # 1 Patient + 1 DocumentReference + 1 DiagnosticReport

    # 4. Verify Semantic Vector Search against CSV-uploaded clinical content
    search_res = client.post(
        "/api/v1/search",
        params={"query": "asthma nebulizer treatment", "patient_mrn": "MRN-CSV-7701"},
    )
    assert search_res.status_code == 200
    search_data = search_res.json()["data"]
    assert search_data["total_results"] >= 1
    assert search_data["results"][0]["patient_mrn"] == "MRN-CSV-7701"
    assert "albuterol nebulizers" in search_data["results"][0]["full_content"]

