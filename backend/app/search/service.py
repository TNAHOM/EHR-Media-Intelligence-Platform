import base64
import json
import time
from collections.abc import Sequence
from datetime import date
from typing import Any

from app.core.config import settings
from app.core.typeid import from_fhir_id
from app.fhir.models import FHIRBundle
from app.llm.models import ClinicalSummaryTable
from app.search.models import (
    IndexStats,
    SearchQueryRequest,
    SearchResponse,
    SearchResultItem,
)
from app.search.vector_store import EmbeddingEngine, vector_store
from dateutil import parser as dt_parser
from sqlmodel import Session, select


class SearchService:
    @staticmethod
    def _date_to_int(dt: date | str) -> int:
        """Converts date to integer format YYYYMMDD for fast ChromaDB numeric filtering."""
        if isinstance(dt, date):
            return int(dt.strftime("%Y%m%d"))
        if isinstance(dt, str):
            clean_str = dt[:10].replace("-", "")
            if clean_str.isdigit() and len(clean_str) == 8:
                return int(clean_str)
            try:
                parsed = dt_parser.parse(dt)
                return int(parsed.strftime("%Y%m%d"))
            except Exception:
                return 0
        return 0

    @classmethod
    def _extract_bundle_documents(
        cls, bundle: FHIRBundle
    ) -> tuple[list[str], list[str], list[dict[str, Any]], int, int]:
        """Extracts document records and metadata from a FHIRBundle."""
        doc_ids: list[str] = []
        doc_texts: list[str] = []
        doc_metadatas: list[dict[str, Any]] = []
        doc_ref_count = 0
        diag_rep_count = 0

        bundle_dict = json.loads(bundle.bundle_json)
        entries = bundle_dict.get("entry", [])
        patient_name = bundle.patient_name
        patient_mrn = bundle.patient_mrn
        patient_id = bundle.patient_id

        for entry in entries:
            res = entry.get("resource", {})
            res_type = res.get("resourceType")
            res_id = str(res.get("id", ""))

            if res_type == "DocumentReference":
                doc_date_str = (res.get("date") or "2024-01-01")[:10]
                doc_date_int = cls._date_to_int(doc_date_str)
                doc_type_text = res.get("type", {}).get("text", "Clinical Note")
                category = (
                    "discharge_summary"
                    if "discharge" in doc_type_text.lower()
                    else "clinical_note"
                )

                content_list = res.get("content", [])
                raw_text = ""
                if content_list:
                    b64_data = content_list[0].get("attachment", {}).get("data", "")
                    try:
                        raw_text = base64.b64decode(b64_data).decode("utf-8")
                    except Exception:
                        raw_text = b64_data

                passage = (
                    f"Patient: {patient_name} (MRN: {patient_mrn}). "
                    f"Record: {doc_type_text} ({doc_date_str}). "
                    f"Clinical Narrative: {raw_text}"
                )

                doc_ids.append(from_fhir_id(res_id))
                doc_texts.append(passage)
                doc_metadatas.append(
                    {
                        "source_id": from_fhir_id(res_id),
                        "patient_mrn": patient_mrn,
                        "patient_name": patient_name,
                        "patient_id": patient_id,
                        "resource_type": "DocumentReference",
                        "record_type": category,
                        "record_date_int": doc_date_int,
                        "record_date_str": doc_date_str,
                        "full_content": raw_text,
                    }
                )
                doc_ref_count += 1

            elif res_type == "DiagnosticReport":
                rep_date_str = (res.get("effectiveDateTime") or "2024-01-01")[:10]
                rep_date_int = cls._date_to_int(rep_date_str)
                rep_title = res.get("code", {}).get("text", "Diagnostic Report")
                conclusion = res.get("conclusion") or ""
                category = "lab"
                for cat in res.get("category", []):
                    if isinstance(cat, dict):
                        for coding in cat.get("coding", []):
                            code = coding.get("code", "")
                            display = str(coding.get("display", "")).lower()
                            if (
                                code == "RAD"
                                or "radiology" in display
                                or "imaging" in display
                            ):
                                category = "imaging"
                                break

                passage = (
                    f"Patient: {patient_name} (MRN: {patient_mrn}). "
                    f"Diagnostic Test: {rep_title} ({rep_date_str}). "
                    f"Findings/Conclusion: {conclusion}"
                )

                doc_ids.append(from_fhir_id(res_id))
                doc_texts.append(passage)
                doc_metadatas.append(
                    {
                        "source_id": from_fhir_id(res_id),
                        "patient_mrn": patient_mrn,
                        "patient_name": patient_name,
                        "patient_id": patient_id,
                        "resource_type": "DiagnosticReport",
                        "record_type": category,
                        "record_date_int": rep_date_int,
                        "record_date_str": rep_date_str,
                        "full_content": conclusion,
                    }
                )
                diag_rep_count += 1

        return doc_ids, doc_texts, doc_metadatas, doc_ref_count, diag_rep_count

    @classmethod
    def _extract_summary_document(
        cls, s: ClinicalSummaryTable
    ) -> tuple[str, str, dict[str, Any]]:
        """Extracts text and metadata for a single ClinicalSummaryTable."""
        summary_date_str = s.created_at.strftime("%Y-%m-%d")
        summary_date_int = cls._date_to_int(summary_date_str)

        passage = (
            f"Patient MRN: {s.patient_mrn}. AI Clinical Summary. "
            f"Chief Concern: {s.chief_concern}. "
            f"Diagnoses: {s.key_diagnoses}. "
            f"Media Records: {s.recent_media_records}. "
            f"Anomalies: {s.flagged_anomalies}."
        )

        full_text = (
            f"CHIEF CONCERN: {s.chief_concern}\n"
            f"DIAGNOSES: {s.key_diagnoses}\n"
            f"MEDIA: {s.recent_media_records}\n"
            f"ANOMALIES: {s.flagged_anomalies}"
        )

        doc_id = str(s.id) if s.id else f"sum-{s.patient_mrn}"
        metadata = {
            "source_id": str(s.id) if s.id else f"sum-{s.patient_mrn}",
            "patient_mrn": s.patient_mrn,
            "patient_name": f"Patient {s.patient_mrn}",
            "patient_id": s.patient_id,
            "resource_type": "ClinicalSummary",
            "record_type": "ai_summary",
            "record_date_int": summary_date_int,
            "record_date_str": summary_date_str,
            "full_content": full_text,
        }

        return doc_id, passage, metadata

    @classmethod
    def index_bundles(cls, bundles: Sequence[FHIRBundle]) -> int:
        """Incrementally upserts resources from given FHIR bundles without wiping collection."""
        all_ids: list[str] = []
        all_texts: list[str] = []
        all_metas: list[dict[str, Any]] = []

        for b in bundles:
            ids, texts, metas, _, _ = cls._extract_bundle_documents(b)
            all_ids.extend(ids)
            all_texts.extend(texts)
            all_metas.extend(metas)

        if not all_ids:
            return 0

        embeddings = EmbeddingEngine.embed_batch(all_texts)
        vector_store.upsert_records(
            ids=all_ids,
            documents=all_texts,
            embeddings=embeddings,
            metadatas=all_metas,
        )
        return len(all_ids)

    @classmethod
    def index_summary(cls, summary: ClinicalSummaryTable) -> None:
        """Incrementally upserts a single ClinicalSummary into ChromaDB."""
        doc_id, passage, meta = cls._extract_summary_document(summary)
        embedding = EmbeddingEngine.embed_text(passage)
        vector_store.upsert_records(
            ids=[doc_id],
            documents=[passage],
            embeddings=[embedding],
            metadatas=[meta],
        )

    @classmethod
    def index_all_records(cls, session: Session, reset: bool = False) -> IndexStats:
        """
        Indexes all DocumentReferences, DiagnosticReports from FHIR Bundles,
        and ClinicalSummaries from SQLite into ChromaDB.
        """
        if reset:
            vector_store.reset_collection()

        doc_ids: list[str] = []
        doc_texts: list[str] = []
        doc_metadatas: list[dict[str, Any]] = []

        doc_ref_count = 0
        diag_rep_count = 0
        ai_summary_count = 0

        # A. Index FHIR Bundles
        bundles = session.exec(select(FHIRBundle)).all()
        for b in bundles:
            ids, texts, metas, r_count, d_count = cls._extract_bundle_documents(b)
            doc_ids.extend(ids)
            doc_texts.extend(texts)
            doc_metadatas.extend(metas)
            doc_ref_count += r_count
            diag_rep_count += d_count

        # B. Index AI Clinical Summaries
        summaries = session.exec(select(ClinicalSummaryTable)).all()
        for s in summaries:
            s_id, s_text, s_meta = cls._extract_summary_document(s)
            doc_ids.append(s_id)
            doc_texts.append(s_text)
            doc_metadatas.append(s_meta)
            ai_summary_count += 1

        if doc_ids:
            embeddings = EmbeddingEngine.embed_batch(doc_texts)
            vector_store.upsert_records(
                ids=doc_ids,
                documents=doc_texts,
                embeddings=embeddings,
                metadatas=doc_metadatas,
            )

        return IndexStats(
            total_indexed_documents=len(doc_ids),
            document_references_count=doc_ref_count,
            diagnostic_reports_count=diag_rep_count,
            clinical_summaries_count=ai_summary_count,
            status="INDEXED",
        )

    @classmethod
    def search(cls, req: SearchQueryRequest) -> SearchResponse:
        start_time = time.perf_counter()

        query_vector = EmbeddingEngine.embed_text(req.query)

        # Build ChromaDB Metadata Filter
        filter_conditions: list[dict[str, Any]] = []

        if req.resource_type:
            filter_conditions.append({"resource_type": {"$eq": req.resource_type}})

        if req.patient_mrn:
            filter_conditions.append(
                {"patient_mrn": {"$eq": req.patient_mrn.strip().upper()}}
            )

        if req.date_from:
            date_from_int = cls._date_to_int(req.date_from)
            filter_conditions.append({"record_date_int": {"$gte": date_from_int}})

        if req.date_to:
            date_to_int = cls._date_to_int(req.date_to)
            filter_conditions.append({"record_date_int": {"$lte": date_to_int}})

        where_filter: dict[str, Any] | None = None
        if len(filter_conditions) == 1:
            where_filter = filter_conditions[0]
        elif len(filter_conditions) > 1:
            where_filter = {"$and": filter_conditions}

        # Vector Index Query
        results = vector_store.query(
            query_embedding=query_vector,
            where_filter=where_filter,
            top_k=req.limit,
        )

        # Parse Results and Apply Relevance Cutoff
        items: list[SearchResultItem] = []
        ids = results.get("ids", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        documents = results.get("documents", [[]])[0]

        for i in range(len(ids)):
            meta = metadatas[i]
            dist = distances[i]
            # Convert cosine distance to 0.0 - 1.0 similarity score
            similarity = max(0.0, min(1.0, 1.0 - float(dist)))

            if similarity <= settings.MIN_RELEVANCE_SCORE:
                continue

            full_doc = str(meta.get("full_content") or documents[i])
            snippet = full_doc[:160] + "..." if len(full_doc) > 160 else full_doc

            items.append(
                SearchResultItem(
                    record_id=str(meta.get("source_id", ids[i])),
                    patient_mrn=str(meta.get("patient_mrn", "")),
                    patient_name=str(meta.get("patient_name", "")),
                    resource_type=str(meta.get("resource_type", "")),
                    record_type=str(meta.get("record_type", "")),
                    record_date=str(meta.get("record_date_str", "")),
                    relevance_score=round(similarity, 4),
                    snippet=snippet,
                    full_content=full_doc,
                )
            )

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return SearchResponse(
            query=req.query,
            total_results=len(items),
            execution_time_ms=elapsed_ms,
            results=items,
        )
