const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

export interface PaginationMeta {
  total_records: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface AuditLogItem {
  id: number;
  record_id: string;
  field_name: string;
  original_value?: string | null;
  cleaned_value?: string | null;
  transformation_rule: string;
  created_at: string;
}

export interface CleanRecordItem {
  id: string;
  patient_mrn: string;
  patient_name: string;
  dob: string;
  gender: string;
  record_type: string;
  encounter_date: string;
  content_text: string;
  source_format: string;
  created_at: string;
  audit_trail?: AuditLogItem[];
}

export interface PaginatedRecordsResponse {
  success: boolean;
  message: string;
  data: CleanRecordItem[];
  pagination: PaginationMeta;
}

export interface FetchRecordsParams {
  page?: number;
  pageSize?: number;
  mrn?: string;
  resourceType?: string;
  recordType?: string;
  dateFrom?: string;
  dateTo?: string;
}

export interface SearchRecordParams {
  query?: string;
  resourceType?: string;
  dateFrom?: string;
  dateTo?: string;
  patientMrn?: string;
  limit?: number;
}

export interface SearchResultItem {
  record_id: string;
  patient_mrn: string;
  patient_name: string;
  record_date: string;
  resource_type: string;
  record_type?: string;
  relevance_score?: number;
  snippet: string;
  full_content?: string;
  isSearchMatch?: boolean;
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

export function mapCleanRecordToSearchResultItem(record: CleanRecordItem): SearchResultItem {
  const isDiagnostic = record.record_type === "lab" || record.record_type === "imaging";
  const resource_type = isDiagnostic ? "DiagnosticReport" : "DocumentReference";
  const snippet =
    record.content_text.length > 180
      ? record.content_text.slice(0, 180) + "..."
      : record.content_text;

  return {
    record_id: record.id,
    patient_mrn: record.patient_mrn,
    patient_name: record.patient_name,
    record_date: record.encounter_date ? record.encounter_date.slice(0, 10) : "",
    resource_type,
    record_type: record.record_type,
    relevance_score: undefined,
    snippet,
    full_content: record.content_text,
    isSearchMatch: false,
  };
}

export async function fetchCleanRecords({
  page = 1,
  pageSize = 10,
  mrn,
  resourceType,
  recordType,
  dateFrom,
  dateTo,
}: FetchRecordsParams = {}): Promise<PaginatedRecordsResponse> {
  const params = new URLSearchParams();
  params.append("page", page.toString());
  params.append("page_size", pageSize.toString());
  if (mrn) params.append("mrn", mrn);
  if (resourceType) params.append("resource_type", resourceType);
  if (recordType) params.append("record_type", recordType);
  if (dateFrom) params.append("date_from", dateFrom);
  if (dateTo) params.append("date_to", dateTo);

  const response = await fetch(`${API_BASE}/records?${params.toString()}`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to fetch clean clinical records");
  }

  return response.json();
}

export async function searchRecords({
  query,
  resourceType,
  dateFrom,
  dateTo,
  patientMrn,
  limit = 20,
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

  const res: SearchResponse = await response.json();
  if (res.data?.results) {
    res.data.results = res.data.results.map((item) => ({
      ...item,
      isSearchMatch: true,
    }));
  }
  return res;
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

