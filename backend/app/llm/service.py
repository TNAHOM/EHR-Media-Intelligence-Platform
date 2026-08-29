import hashlib
import json

from app.core.config import settings
from app.fhir.models import FHIRBundle
from app.llm.models import (
    ClinicalSummaryRead,
    ClinicalSummaryTable,
    GeminiClinicalSummaryPayload,
)
from app.llm.preprocessor import ClinicalDeidentifier
from google import genai
from google.genai import types
from sqlmodel import Session, col, select


class SummarizerService:
    _client: genai.Client | None = None

    @classmethod
    def get_client(cls) -> genai.Client:
        """Reuses a singleton GenAI client to eliminate connection handshake latency."""
        if cls._client is None:
            cls._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return cls._client

    @staticmethod
    def _compute_cache_hash(mrn: str, bundle_json: str) -> str:
        """Computes SHA-256 fingerprint of the patient's bundle for caching."""
        fingerprint = f"{mrn.strip().upper()}|{bundle_json.strip()}"
        return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()

    @staticmethod
    def _count_words(payload: GeminiClinicalSummaryPayload) -> int:
        """Counts total words across the 4 structured summary sections."""
        combined = f"{payload.chief_concern} {payload.key_diagnoses} {payload.recent_media_records} {payload.flagged_anomalies}"
        return len(combined.strip().split())

    @classmethod
    def generate_summary(
        cls, session: Session, patient_mrn: str
    ) -> ClinicalSummaryRead:
        # 1. Fetch Patient's FHIR Bundle from SQLite
        statement = select(FHIRBundle).where(
            col(FHIRBundle.patient_mrn) == patient_mrn.strip().upper()
        )
        bundle_record = session.exec(statement).first()

        if not bundle_record:
            raise ValueError(
                f"No FHIR Bundle found for MRN '{patient_mrn}'. Please run normalization first."
            )

        # 2. Check SQLite Cache
        cache_hash = cls._compute_cache_hash(patient_mrn, bundle_record.bundle_json)
        cache_query = select(ClinicalSummaryTable).where(
            col(ClinicalSummaryTable.content_hash) == cache_hash
        )
        cached = session.exec(cache_query).first()

        if cached:
            read_dto = ClinicalSummaryRead.model_validate(cached)
            read_dto.cache_hit = True
            return read_dto

        # 3. Extract & De-identify FHIR facts
        clinical_context = ClinicalDeidentifier.extract_deidentified_context(
            bundle_record.bundle_json
        )

        if not clinical_context:
            empty_payload = GeminiClinicalSummaryPayload(
                chief_concern="No documented chief complaint.",
                key_diagnoses="No active diagnoses recorded.",
                recent_media_records="None.",
                flagged_anomalies="None.",
            )
            return cls._persist_and_return(
                session,
                bundle_record,
                cache_hash,
                empty_payload,
                "deterministic-fallback",
            )

        system_instruction = (
            "You are an expert hospital clinical triage AI assistant. "
            "Synthesize a thorough, detailed, and clinically rich summary from the provided patient timeline.\n"
            "STRICT CLINICAL RULES:\n"
            "1. Ground all statements strictly in the provided records. Never assume or hallucinate.\n"
            f"2. DEPTH & LENGTH: Target a detailed summary between 160 and {settings.MAX_SUMMARY_WORDS_PROMPT} words (strictly under {settings.MAX_SUMMARY_WORDS_PROMPT} words total). Do NOT output one-line summaries—expand on clinical context, vital signs, test metrics, and care plans.\n"
            "3. Populate the exact JSON schema with descriptive details:\n"
            "   - chief_concern: Detail the presenting symptoms, severity, and context of presentation.\n"
            "   - key_diagnoses: List active and differential diagnoses with supporting clinical findings.\n"
            "   - recent_media_records: Describe all imaging (modality/views/findings) and lab panels (specific values/units).\n"
            "   - flagged_anomalies: Detail all abnormal lab values, acute imaging abnormalities, and elevated metrics."
        )

        user_prompt = f"PATIENT MEDICAL RECORD:\n{clinical_context}\n\nGenerate the concise clinical summary in valid JSON."

        client = cls.get_client()

        thinking_level_enum = getattr(
            types.ThinkingLevel,
            str(settings.GEMINI_THINKING_LEVEL).upper(),
            types.ThinkingLevel.HIGH,
        )

        thinking_cfg = types.ThinkingConfig(thinking_level=thinking_level_enum)

        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=GeminiClinicalSummaryPayload,
                thinking_config=thinking_cfg,
            ),
        )

        if not response.text:
            raise RuntimeError(
                "Gemini returned an empty response or the request was blocked."
            )

        parsed_data = json.loads(response.text)
        summary_payload = GeminiClinicalSummaryPayload.model_validate(parsed_data)

        # 6. Check Word Count
        word_count = cls._count_words(summary_payload)
        if word_count > settings.MAX_SUMMARY_WORDS_LIMIT:
            summary_payload.flagged_anomalies = summary_payload.flagged_anomalies[:300]

        return cls._persist_and_return(
            session,
            bundle_record,
            cache_hash,
            summary_payload,
            settings.GEMINI_MODEL,
        )

    @staticmethod
    def _persist_and_return(
        session: Session,
        bundle_record: FHIRBundle,
        cache_hash: str,
        payload: GeminiClinicalSummaryPayload,
        model_name: str,
    ) -> ClinicalSummaryRead:
        word_count = len(
            f"{payload.chief_concern} {payload.key_diagnoses} {payload.recent_media_records} {payload.flagged_anomalies}".split()
        )

        db_entry = ClinicalSummaryTable(
            patient_mrn=bundle_record.patient_mrn,
            patient_id=bundle_record.patient_id,
            content_hash=cache_hash,
            chief_concern=payload.chief_concern,
            key_diagnoses=payload.key_diagnoses,
            recent_media_records=payload.recent_media_records,
            flagged_anomalies=payload.flagged_anomalies,
            word_count=word_count,
            model_used=model_name,
        )

        session.add(db_entry)
        session.commit()
        session.refresh(db_entry)

        read_dto = ClinicalSummaryRead.model_validate(db_entry)
        read_dto.cache_hit = False
        return read_dto
