# EHR Media Intelligence Platform

An enterprise-grade, HL7 FHIR R4-compliant Electronic Health Record (EHR) ingestion, semantic search, and AI-assisted clinical intelligence platform.

---

## System Architecture

```
                                  ┌─────────────────────────────┐
                                  │      React + Vite + TS      │
                                  │    Tailwind CSS Frontend    │
                                  └──────────────┬──────────────┘
                                                 │ REST API (/api/v1)
                                                 ▼
                                  ┌─────────────────────────────┐
                                  │       FastAPI Backend       │
                                  │      (Python 3.11/3.12)     │
                                  └──────┬───────────────┬──────┘
                                         │               │
                     ┌───────────────────┴───┐       ┌───┴───────────────────┐
                     ▼                       ▼       ▼                       ▼
            ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
            │ SQLite+SQLModel │     │  HL7 FHIR R4    │     │ ChromaDB Vector │
            │ Clean EHR Data  │     │ Bundle Resource │     │ Store (MiniLM)  │
            └─────────────────┘     └─────────────────┘     └─────────────────┘
                                             │                       │
                                             └───────────┬───────────┘
                                                         ▼
                                            ┌─────────────────────────┐
                                            │ Google Gemini 3.6 Flash │
                                            │  Clinical Synthesizer   │
                                            └─────────────────────────┘
```

---

## Core Capabilities

1. **Robust EHR Ingestion & Data Cleaning**
   - Ingests raw, heterogeneous JSON medical export dumps.
   - Normalizes patient MRNs, full names, dates of birth, and encounter timestamps.
   - Preserves audit trails of data cleaning and normalization rules applied.

2. **HL7 FHIR R4 Normalization**
   - Converts clinical records into compliant `DocumentReference` and `DiagnosticReport` FHIR R4 resources organized inside patient transaction bundles (`FHIRBundle`).

3. **Semantic Vector Search & Hybrid Filtering**
   - ChromaDB dense vector indexing using `sentence-transformers/all-MiniLM-L6-v2`.
   - Natural language queries across unstructured clinical narratives, imaging impressions, and lab findings.
   - Dynamic metadata filtering by MRN, FHIR resource type (`DocumentReference`, `DiagnosticReport`), and encounter date ranges.

4. **Lazy AI Clinical Summarization**
   - On-demand patient synthesis powered by Google Gemini (Gemini 3.6 Flash / 2.0).
   - Extracts chief concern, key diagnoses, media findings, and anomalies with word-count controls.
   - Caching layer in SQLite (`ClinicalSummaryTable`) prevents redundant LLM calls.
   - Drawer tabs isolate AI calls, guaranteeing that local medical records are viewable even if remote AI services experience network or quota issues.

---

## Repository Structure

```
├── backend/
│   ├── app/
│   │   ├── api/v1/          # FastAPI routers (ingestion, fhir, search, summary)
│   │   ├── core/            # Config, database setup, response schemas
│   │   ├── fhir/            # HL7 FHIR models and bundle generators
│   │   ├── ingestion/       # Normalization, cleaning rules, and audit trails
│   │   ├── llm/             # Gemini clinical summarization engine
│   │   └── search/          # ChromaDB vector store and semantic search
│   ├── scripts/             # Mock EHR dataset generators (generate_90_records.py)
│   ├── tests/               # Pytest suite (FHIR, ingestion, search, summary)
│   └── requirements.txt     # Python dependencies
├── data/
│   └── raw/                 # Raw EHR JSON datasets for ingestion
├── frontend/
│   ├── src/
│   │   ├── components/      # React components (PatientDrawer, ResultCard, EmptyState, etc.)
│   │   ├── services/        # Frontend API client
│   │   └── App.tsx          # Main search and browse application
│   └── package.json
├── .env.example             # Environment configuration template
└── README.md
```

---

## Quickstart Guide

### 1. Environment Setup

Copy `.env.example` to `.env` in the project root and provide your Google Gemini API key:

```bash
cp .env.example .env
```

Edit `.env`:
```ini
GEMINI_API_KEY="your-google-gemini-api-key"
GEMINI_MODEL="gemini-3.6-flash"
GEMINI_THINKING_LEVEL="LOW"
DATABASE_URL="sqlite:///./data/ehr.db"
RAW_DATA_DIR="./data/raw"
CHROMA_PERSIST_DIR="./data/chroma_db"
VITE_API_BASE_URL="http://127.0.0.1:8000/api/v1"
```

### 2. Backend Setup & Run

Create a virtual environment, install dependencies, generate sample data, and start the FastAPI server:

```powershell
# From the repository root:
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Generate the 90-record test dataset
python scripts/generate_90_records.py

# Launch FastAPI development server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API docs will be available at: `http://127.0.0.1:8000/docs`

### 3. Frontend Setup & Run

In a separate terminal:

```powershell
cd frontend
npm install
npm run dev
```

The application will be accessible at `http://localhost:5173`.

---

## API Endpoints Overview

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | API operational health check |
| `POST` | `/api/v1/ingest/upload` | Ingest and auto-process raw EHR dataset |
| `GET` | `/api/v1/records` | Paginated browse of cleaned clinical records |
| `POST` | `/api/v1/search` | Semantic vector search with metadata filters |
| `POST` | `/api/v1/summary/{mrn}` | Generate/retrieve Gemini clinical summary |
| `GET` | `/api/v1/fhir/bundles/{mrn}` | Retrieve HL7 FHIR R4 Bundle for patient |

---

## Running Automated Tests

Run the backend pytest test suite to verify ingestion, FHIR normalization, vector search, and clinical summarization:

```powershell
# From repository root
& "backend\.venv\Scripts\pytest.exe" backend\tests -v
```
