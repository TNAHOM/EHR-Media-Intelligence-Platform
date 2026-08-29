import re
from datetime import date, datetime, timezone

from dateutil import parser as date_parser

from app.ingestion.schemas import AuditLogEntry, GenderType, RecordCategory


class ClinicalDataCleaner:
    @staticmethod
    def normalize_mrn(
        raw_mrn: str | None,
    ) -> tuple[str | None, AuditLogEntry | None]:
        if not raw_mrn or not str(raw_mrn).strip():
            return None, None

        cleaned = str(raw_mrn).strip().upper()
        # Remove non-alphanumeric except hyphens
        cleaned = re.sub(r"[^A-Z0-9-]", "", cleaned)

        # Ensure consistent prefix format 'MRN-XXXXX'
        if not cleaned.startswith("MRN-"):
            digits = re.sub(r"[^0-9]", "", cleaned)
            cleaned = f"MRN-{digits if digits else cleaned}"

        log = None
        if cleaned != str(raw_mrn):
            log = AuditLogEntry(
                field_name="patient_mrn",
                original_value=str(raw_mrn),
                cleaned_value=cleaned,
                transformation_rule="Trimmed whitespace and standardized MRN prefix to MRN-XXXXX",
            )
        return cleaned, log

    @staticmethod
    def normalize_name(raw_name: str | None) -> tuple[str, AuditLogEntry | None]:
        if not raw_name or not str(raw_name).strip():
            return "Unknown Patient", AuditLogEntry(
                field_name="patient_name",
                original_value=str(raw_name),
                cleaned_value="Unknown Patient",
                transformation_rule="Replaced empty name with default placeholder",
            )

        cleaned = " ".join(str(raw_name).strip().split()).title()
        log = None
        if cleaned != str(raw_name):
            log = AuditLogEntry(
                field_name="patient_name",
                original_value=str(raw_name),
                cleaned_value=cleaned,
                transformation_rule="Applied Title Casing and removed irregular whitespace",
            )
        return cleaned, log

    @staticmethod
    def normalize_gender(
        raw_gender: str | None,
    ) -> tuple[GenderType, AuditLogEntry | None]:
        if not raw_gender:
            return "unknown", AuditLogEntry(
                field_name="gender",
                original_value=str(raw_gender),
                cleaned_value="unknown",
                transformation_rule="Mapped null/empty gender to FHIR 'unknown'",
            )

        val = str(raw_gender).strip().lower()
        if val in ["m", "male", "man"]:
            cleaned: GenderType = "male"
        elif val in ["f", "female", "woman"]:
            cleaned = "female"
        elif val in ["other", "non-binary"]:
            cleaned = "other"
        else:
            cleaned = "unknown"

        log = None
        if cleaned != val:
            log = AuditLogEntry(
                field_name="gender",
                original_value=str(raw_gender),
                cleaned_value=cleaned,
                transformation_rule="Mapped raw gender representation to strict FHIR R4 administrative gender enum",
            )
        return cleaned, log

    @staticmethod
    def parse_dob(
        raw_dob: str | None,
    ) -> tuple[date | None, AuditLogEntry | None]:
        if not raw_dob or not str(raw_dob).strip():
            return None, None

        try:
            parsed = date_parser.parse(str(raw_dob)).date()
            log = None
            if str(parsed) != str(raw_dob).strip():
                log = AuditLogEntry(
                    field_name="dob",
                    original_value=str(raw_dob),
                    cleaned_value=str(parsed),
                    transformation_rule="Standardized non-standard DOB format to ISO-8601 (YYYY-MM-DD)",
                )
            return parsed, log
        except Exception:
            return None, None

    @staticmethod
    def parse_encounter_date(
        raw_date: str | None,
    ) -> tuple[datetime | None, AuditLogEntry | None]:
        if not raw_date or not str(raw_date).strip():
            return None, None

        try:
            parsed = date_parser.parse(str(raw_date))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            else:
                parsed = parsed.astimezone(timezone.utc)

            cleaned_iso = parsed.isoformat()
            log = None
            if cleaned_iso != str(raw_date).strip():
                log = AuditLogEntry(
                    field_name="encounter_date",
                    original_value=str(raw_date),
                    cleaned_value=cleaned_iso,
                    transformation_rule="Standardized timestamp to ISO-8601 UTC representation",
                )
            return parsed, log
        except Exception:
            return None, None

    @staticmethod
    def normalize_record_type(
        raw_type: str | None,
    ) -> tuple[RecordCategory, AuditLogEntry | None]:
        val = (raw_type or "").strip().lower().replace(" ", "_")
        if "discharge" in val:
            cleaned: RecordCategory = "discharge_summary"
        elif "lab" in val or "panel" in val:
            cleaned = "lab"
        elif (
            "imag" in val
            or "x-ray" in val
            or "mri" in val
            or "ct" in val
            or "rad" in val
            or "ultrasound" in val
            or "echo" in val
        ):
            cleaned = "imaging"
        else:
            cleaned = "clinical_note"

        log = None
        if cleaned != val:
            log = AuditLogEntry(
                field_name="record_type",
                original_value=str(raw_type),
                cleaned_value=cleaned,
                transformation_rule="Standardized record classification category",
            )
        return cleaned, log
