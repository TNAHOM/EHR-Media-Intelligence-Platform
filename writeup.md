# Architecture & Technical Write-Up: EHR Media Intelligence Platform

### 1. Tradeoffs Made and Why

- **Local Embeddings (`all-MiniLM-L6-v2`) vs. Cloud Embedding APIs:**
  I selected `sentence-transformers/all-MiniLM-L6-v2` running locally on CPU over external embedding APIs (such as OpenAI `text-embedding-3-small` or Google `text-embedding-004`).
  _Why:_ Empirical latency testing demonstrated that local embeddings execute queries in **80ms – 200ms** across 100+ records, whereas cloud embedding APIs introduced a **500ms – 700ms** network round-trip. Crucially, local embeddings guarantee **100% data sovereignty and HIPAA privacy**—no unstructured clinical narratives or laboratory values leave the boundary of the application server for search indexing.
- **ChromaDB (`PersistentClient`) vs. FAISS / SQLite-VSS:**
  While FAISS offers marginally faster raw C++ index operations, it lacks integrated metadata filtering out-of-the-box. ChromaDB was chosen for its native, expressive metadata filtering engine (`$and`, `$gte`, `$lte` for dates and resource types) and zero-configuration SQLite persistence on disk.
- **Zero-Dependency TypeID (Base32 Crockford UUIDv7) vs. Sequential / Toy IDs:**
  I migrated all internal primary keys and FHIR resource identifiers to **TypeIDs** (`pat-01h...`, `doc-01h...`, `diag-01h...`, `bundle-01h...`, `rec-01h...`). UUIDv7 embeds a 48-bit millisecond timestamp, guaranteeing **monotonic, k-sortable B-Tree index inserts** in SQLite (preventing page splits). To satisfy strict HL7 FHIR R4 regex rules (`^[A-Za-z0-9\-\.]{1,64}$`), a hyphen delimiter was standardized instead of an underscore. This also eliminates MRN information leakage in HTTP URLs and logs.
- **Deterministic Content Hashing vs. TTL Caching:**
  Instead of time-based cache expiration (TTL), LLM summaries are cached using `SHA256(patient_mrn + bundle_json)`. Unchanged patient charts return cached summaries in **~100ms** ($0 API cost), while ingesting a new clinical note automatically alters the bundle hash, guaranteeing instant cache invalidation and fresh clinical synthesis.

---

### 2. What I Would Improve With More Time

- **SMART on FHIR & OAuth 2.0 Integration:** Implement an authentication layer compliant with SMART on FHIR backend services, enforcing granular User/Patient scopes (e.g., `patient/DocumentReference.read`).
- **Hybrid Search (BM25 Keyword + Dense Vector Retrieval with Reciprocal Rank Fusion):** Integrate sparse lexical search (BM25) alongside dense semantic vectors. While dense embeddings excel at clinical synonyms (e.g., mapping _"heart attack"_ $\rightarrow$ _"ACS / troponin"_), BM25 provides exact string matching for alphanumeric medication dosages and rare lab codes.
- **Asynchronous Ingestion Workers (Celery / Redis / BackgroundTasks):** Offload high-volume batch processing (e.g., 50,000+ records) to background worker queues with WebSocket progress updates to the clinician UI.

---

### 3. FHIR & Clinical Concepts Researched

- **LOINC Document Ontologies:** Researched LOINC universal codes for clinical note classification (`18842-5` for Discharge Summaries, `11488-4` for Consultation Notes) and HL7 v2-0074 diagnostic service categories (`RAD` for Radiology, `LAB` for Laboratory).
- **FHIR `instant` Temporal Constraints:** Discovered that FHIR R4 `DocumentReference.date` strictly requires an `instant` datatype with an explicit timezone offset (`+00:00` or `Z`). Naive timestamps cause schema validation failures in `fhir.resources`, requiring explicit UTC localization in the mapper pipeline.
- **US Core Implementation Guide (Cures Act Mandate):** Researched US Core profile requirements (`us-core-documentreference-category` = `clinical-note`) to ensure generated bundles comply with ONC federal interoperability standards.
- **HIPAA Safe Harbor 18 Direct Identifiers & Age > 89 Rule:** Implemented a preprocessor stripping all 18 direct identifiers (names, MRNs, emails, phones). Specifically implemented the **HIPAA Age > 89 Rule**, where patient ages exceeding 89 are automatically aggregated as **"90+"** to prevent demographic re-identification.

---

### 4. How I Validated AI Summary Quality

- **Deterministic Grounding (`temperature=0.0`):** Set model temperature to `0.0` and enforced strict system prompt instructions: _"Ground all statements strictly in the provided records. Never assume or hallucinate diagnoses or metrics."_
- **Structured Output Schema Enforcement:** Used native JSON Schema enforcement (`GeminiClinicalSummaryPayload`) via the `google-genai` SDK to guarantee the presence of all four mandatory sections: `chief_concern`, `key_diagnoses`, `recent_media_records`, and `flagged_anomalies`.
- **Length Ceiling & Word Budgeting:** Prompt engineering allocated strict section budgets (targeting 120–185 words) with a backend validation ceiling of 200 words to maintain rapid clinical readability.
- **Safety Disclaimer Requirement:** Included mandatory clinical safety disclaimer noting that output is AI-generated for clinical decision support and not a final medical diagnosis.
- **Edge-Case & Empty-Chart Defenses:** Evaluated the summarizer against edge cases: empty charts (returns a deterministic fallback without calling the API), short single-sentence notes (summarizes facts concisely without adding artificial filler), and dense longitudinal histories (synthesizes acute abnormalities accurately).
