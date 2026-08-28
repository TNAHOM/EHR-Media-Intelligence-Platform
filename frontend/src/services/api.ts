const API_BASE = "http://127.0.0.1:8000/api/v1";

export interface SearchRecordParams {
  query?: string;
  resourceType?: string;
  dateFrom?: string;
  dateTo?: string;
  patientMrn?: string;
  limit?: number;
}

export interface SearchResultItem {
  record_id: string | number;
  patient_mrn: string;
  patient_name: string;
  record_date: string;
  resource_type: string;
  record_type?: string;
  relevance_score: number;
  snippet: string;
  full_content?: string;
}

export interface SearchResponse {
  success?: boolean;
  message?: string;
  data: {
    results: SearchResultItem[];
    execution_time_ms: number;
  };
}

export interface PatientSummaryData {
  model_used: string;
  cache_hit: boolean;
  word_count: number;
  chief_concern: string;
  key_diagnoses: string;
  recent_media_records: string;
  flagged_anomalies: string;
  disclaimer: string;
}

export interface PatientSummaryResponse {
  success?: boolean;
  message?: string;
  data?: PatientSummaryData;
}

export interface FHIRBundleData {
  resourceType?: string;
  id?: string;
  type?: string;
  total?: number;
  entry?: Array<{
    fullUrl?: string;
    resource?: Record<string, unknown>;
  }>;
  [key: string]: unknown;
}

export interface FHIRBundleResponse {
  success?: boolean;
  message?: string;
  data?: FHIRBundleData;
}

export interface IngestionResultData {
  ingestion?: {
    total_processed?: number;
    total_cleaned?: number;
    total_duplicates_dropped?: number;
  };
  fhir_normalization?: {
    total_bundles_created?: number;
    total_resources_mapped?: number;
  };
}

export interface UploadEHRResponse {
  success?: boolean;
  message?: string;
  data: IngestionResultData;
}

export async function searchRecords({
  query,
  resourceType,
  dateFrom,
  dateTo,
  patientMrn,
  limit = 5,
}: SearchRecordParams): Promise<SearchResponse> {
  const params = new URLSearchParams();
  if (query) params.append("query", query);
  if (resourceType) params.append("resource_type", resourceType);
  if (dateFrom) params.append("date_from", dateFrom);
  if (dateTo) params.append("date_to", dateTo);
  if (patientMrn) params.append("patient_mrn", patientMrn);
  if (limit) params.append("limit", limit.toString());

  const response = await fetch(`${API_BASE}/search?${params.toString()}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Search request failed");
  }

  return response.json();
}

export async function fetchPatientSummary(mrn: string): Promise<PatientSummaryResponse> {
  const response = await fetch(`${API_BASE}/summary/${encodeURIComponent(mrn)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to fetch clinical summary");
  }

  return response.json();
}

export async function fetchFHIRBundle(mrn: string): Promise<FHIRBundleResponse> {
  const response = await fetch(`${API_BASE}/fhir/bundles/${encodeURIComponent(mrn)}`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to fetch FHIR Bundle");
  }
  return response.json();
}

export async function uploadEHRFile(file: File, autoProcess = true): Promise<UploadEHRResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/ingest/upload?auto_process=${autoProcess}`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Upload failed");
  }

  return response.json();
}
