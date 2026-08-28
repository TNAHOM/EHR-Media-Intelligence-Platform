from fastapi.testclient import TestClient
from sqlmodel import Session


def test_semantic_search_and_filters(session: Session, client: TestClient):
    """End-to-end test: Ingest dataset -> Index Vectors -> Perform Semantic & Filtered Queries via Query Params."""
    sample_dataset = """[
      {
        "export_id": "REC-CARD-01",
        "patient_mrn": "MRN-CARD-100",
        "patient_full_name": "Alice Cardiology",
        "date_of_birth": "1970-01-01",
        "gender_code": "female",
        "document_type": "discharge_summary",
        "encounter_date": "2024-01-15T10:00:00Z",
        "content_body": "Patient admitted with acute retrosternal chest pain and elevated cardiac troponin."
      },
      {
        "export_id": "REC-RAD-02",
        "patient_mrn": "MRN-CARD-100",
        "patient_full_name": "Alice Cardiology",
        "date_of_birth": "1970-01-01",
        "gender_code": "female",
        "document_type": "imaging",
        "encounter_date": "2024-01-16T11:00:00Z",
        "content_body": "Chest X-Ray demonstrates moderate cardiomegaly with clear lung fields."
      },
      {
        "export_id": "REC-NEURO-03",
        "patient_mrn": "MRN-NEURO-200",
        "patient_full_name": "Bob Neurology",
        "date_of_birth": "1980-05-12",
        "gender_code": "male",
        "document_type": "clinical_note",
        "encounter_date": "2024-03-01T14:00:00Z",
        "content_body": "Follow-up for chronic migraine with visual aura and photophobia."
      }
    ]"""

    # 1. Ingest & Auto-Process (creates FHIR bundles + builds ChromaDB vector index)
    upload_res = client.post(
        "/api/v1/ingest/upload?auto_process=true",
        files={"file": ("test.json", sample_dataset.encode(), "application/json")},
    )
    assert upload_res.status_code == 200

    # 2. Test Semantic Search via Query Params: "heart attack enzyme" matches "chest pain and elevated troponin"
    res_cardiac = client.post(
        "/api/v1/search",
        params={"query": "heart attack and enzymes", "limit": 5},
    )
    assert res_cardiac.status_code == 200
    data_cardiac = res_cardiac.json()["data"]
    assert data_cardiac["total_results"] > 0
    top_match = data_cardiac["results"][0]
    assert top_match["patient_mrn"] == "MRN-CARD-100"
    assert top_match["relevance_score"] > 0.30
    assert data_cardiac["execution_time_ms"] < 2000.0

    # 3. Test Resource Type Filtering via Query Params: Filter only "DiagnosticReport"
    res_filtered = client.post(
        "/api/v1/search",
        params={"query": "cardiomegaly", "resource_type": "DiagnosticReport"},
    )
    assert res_filtered.status_code == 200
    data_filtered = res_filtered.json()["data"]
    for item in data_filtered["results"]:
        assert item["resource_type"] == "DiagnosticReport"

    # 4. Test Date Range Filtering via Query Params (Between March 1 and March 30, 2024)
    res_date = client.post(
        "/api/v1/search",
        params={
            "query": "migraine aura",
            "date_from": "2024-03-01",
            "date_to": "2024-03-30",
        },
    )
    assert res_date.status_code == 200
    data_date = res_date.json()["data"]
    assert data_date["total_results"] == 1
    assert data_date["results"][0]["patient_mrn"] == "MRN-NEURO-200"
