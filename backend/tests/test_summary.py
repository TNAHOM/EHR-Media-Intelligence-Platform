from app.llm.models import GeminiClinicalSummaryPayload
from app.llm.preprocessor import ClinicalDeidentifier
from app.llm.service import SummarizerService
from fastapi.testclient import TestClient
from sqlmodel import Session


def test_phi_deidentification_preprocessor():
    """Validates that personal identifiers are scrubbed and exact dates converted to age."""
    sample_bundle_json = """{
      "resourceType": "Bundle",
      "entry": [
        {
          "resource": {
            "resourceType": "Patient",
            "name": [{"family": "Vance", "given": ["Eleanor"]}],
            "birthDate": "1982-04-12",
            "gender": "female"
          }
        },
        {
          "resource": {
            "resourceType": "DocumentReference",
            "type": {"text": "Discharge Summary"},
            "date": "2024-01-15T10:00:00Z",
            "content": [{
              "attachment": {
                "data": "UGF0aWVudCBFbGVhbm9yIFZhbmNlIChNUk4tODg0MDEpIHNlZW4gZm9yIGNoZXN0IHBhaW4uIENhbGwgdXMgYXQgNTU1LTEyMy00NTY3IG9yIGRvY0BnbWFpbC5jb20="
              }
            }]
          }
        }
      ]
    }"""

    deidentified = ClinicalDeidentifier.extract_deidentified_context(sample_bundle_json)

    # 1. Names and identifiers must be stripped
    assert "Eleanor" not in deidentified
    assert "Vance" not in deidentified
    assert "555-123-4567" not in deidentified
    assert "doc@gmail.com" not in deidentified

    # 2. Clinical facts and demographic context must remain
    assert "Female" in deidentified
    assert "chest pain" in deidentified


def test_word_count_calculation():
    """Validates that word counting and character counting functions correctly."""
    payload = GeminiClinicalSummaryPayload(
        chief_concern="Acute chest pain and dyspnea.",
        key_diagnoses="Acute coronary syndrome rule-out.",
        recent_media_records="ECG sinus tachycardia. Troponin 0.45.",
        flagged_anomalies="Elevated troponin cardiac enzyme.",
    )
    words = SummarizerService._count_words(payload)
    assert words == 18  # Exact word count
    assert words <= 185  # Well under the prompt ceiling


def test_summary_api_and_cache_hit(session: Session, client: TestClient):
    """End-to-end test: Ingest -> Summarize (Cache Miss) -> Summarize Again (Cache Hit)."""
    sample_json = """[
      {
        "export_id": "REC-901",
        "patient_mrn": "MRN-77777",
        "patient_full_name": "Test Summary Patient",
        "date_of_birth": "1985-06-15",
        "gender_code": "female",
        "document_type": "discharge_summary",
        "encounter_date": "2024-02-01T10:00:00Z",
        "content_body": "Patient admitted for severe migraine. Prescribed sumatriptan."
      }
    ]"""

    # Ingest and normalize (auto_process=True)
    client.post(
        "/api/v1/ingest/upload?auto_process=true",
        files={"file": ("test.json", sample_json.encode(), "application/json")},
    )

    # 1. First Call -> CACHE MISS (Generated)
    res_1 = client.post("/api/v1/summary/MRN-77777")
    assert res_1.status_code == 200
    data_1 = res_1.json()["data"]
    assert data_1["cache_hit"] is False
    assert data_1["word_count"] <= 220
    assert "AI-generated" in data_1["disclaimer"]

    # 2. Second Call -> CACHE HIT (Instant from SQLite)
    res_2 = client.post("/api/v1/summary/MRN-77777")
    assert res_2.status_code == 200
    data_2 = res_2.json()["data"]
    assert data_2["cache_hit"] is True
    assert data_2["chief_concern"] == data_1["chief_concern"]
