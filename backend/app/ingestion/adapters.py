import csv
import hashlib
import json

from app.ingestion.cleaners import ClinicalDataCleaner
from app.ingestion.models import AuditLog, CleanRecord


class IngestionAdapter:
    @staticmethod
    def _compute_hash(mrn: str, dt: str, content: str) -> str:
        """Generates a SHA-256 fingerprint for deduplication."""
        fingerprint = f"{mrn}|{dt}|{content.strip().lower()}"
        return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()

    @classmethod
    def process_json(cls, raw_json_str: str) -> tuple[list[CleanRecord], int, int]:
        records: list[CleanRecord] = []
        seen_hashes: set[str] = set()
        duplicates_count = 0
        invalid_count = 0

        raw_data = json.loads(raw_json_str)
        if isinstance(raw_data, dict):
            raw_data = [raw_data]

        for item in raw_data:
            logs: list[AuditLog] = []

            mrn, mrn_log = ClinicalDataCleaner.normalize_mrn(
                item.get("patient_mrn") or item.get("mrn")
            )
            name, name_log = ClinicalDataCleaner.normalize_name(
                item.get("patient_full_name") or item.get("patient_name")
            )
            gender, gender_log = ClinicalDataCleaner.normalize_gender(
                item.get("gender_code") or item.get("gender")
            )
            dob, dob_log = ClinicalDataCleaner.parse_dob(
                item.get("date_of_birth") or item.get("dob")
            )
            enc_date, date_log = ClinicalDataCleaner.parse_encounter_date(
                item.get("encounter_date") or item.get("record_date")
            )
            rec_type, type_log = ClinicalDataCleaner.normalize_record_type(
                item.get("document_type") or item.get("record_type")
            )
            content = (item.get("content_body") or item.get("text") or "").strip()

            # Discard records with missing mandatory clinical identifiers
            if not mrn or not dob or not enc_date or not content:
                invalid_count += 1
                continue

            rec_id = item.get("export_id") or f"REC-{len(records) + 1:04d}"

            for raw_entry in [
                mrn_log,
                name_log,
                gender_log,
                dob_log,
                date_log,
                type_log,
            ]:
                if raw_entry:
                    logs.append(
                        AuditLog(
                            record_id=rec_id,
                            field_name=raw_entry.field_name,
                            original_value=raw_entry.original_value,
                            cleaned_value=raw_entry.cleaned_value,
                            transformation_rule=raw_entry.transformation_rule,
                        )
                    )

            # Deduplication
            doc_hash = cls._compute_hash(mrn, enc_date.isoformat(), content)
            if doc_hash in seen_hashes:
                duplicates_count += 1
                continue
            seen_hashes.add(doc_hash)

            records.append(
                CleanRecord(
                    id=rec_id,
                    patient_mrn=mrn,
                    patient_name=name,
                    dob=dob,
                    gender=gender,
                    record_type=rec_type,
                    encounter_date=enc_date,
                    content_text=content,
                    source_format="json",
                    audit_trail=logs,
                )
            )

        return records, duplicates_count, invalid_count

    @classmethod
    def process_csv(cls, raw_csv_str: str) -> tuple[list[CleanRecord], int, int]:
        records: list[CleanRecord] = []
        seen_hashes: set[str] = set()
        duplicates_count = 0
        invalid_count = 0

        reader = csv.DictReader(raw_csv_str.strip().splitlines())

        for row in reader:
            logs: list[AuditLog] = []

            mrn, mrn_log = ClinicalDataCleaner.normalize_mrn(
                row.get("patient_mrn") or row.get("mrn")
            )
            name, name_log = ClinicalDataCleaner.normalize_name(
                row.get("patient_name") or row.get("name")
            )
            gender, gender_log = ClinicalDataCleaner.normalize_gender(
                row.get("gender") or row.get("sex")
            )
            dob, dob_log = ClinicalDataCleaner.parse_dob(
                row.get("birth_date") or row.get("dob")
            )
            enc_date, date_log = ClinicalDataCleaner.parse_encounter_date(
                row.get("recorded_date") or row.get("effective_date")
            )
            rec_type, type_log = ClinicalDataCleaner.normalize_record_type(
                row.get("category") or row.get("record_type")
            )
            content = (
                row.get("clinical_text") or row.get("findings_text") or ""
            ).strip()

            if not mrn or not dob or not enc_date or not content:
                invalid_count += 1
                continue

            rec_id = row.get("record_id") or f"CSV-{len(records) + 1:04d}"

            for raw_entry in [
                mrn_log,
                name_log,
                gender_log,
                dob_log,
                date_log,
                type_log,
            ]:
                if raw_entry:
                    logs.append(
                        AuditLog(
                            record_id=rec_id,
                            field_name=raw_entry.field_name,
                            original_value=raw_entry.original_value,
                            cleaned_value=raw_entry.cleaned_value,
                            transformation_rule=raw_entry.transformation_rule,
                        )
                    )

            doc_hash = cls._compute_hash(mrn, enc_date.isoformat(), content)
            if doc_hash in seen_hashes:
                duplicates_count += 1
                continue
            seen_hashes.add(doc_hash)

            records.append(
                CleanRecord(
                    id=rec_id,
                    patient_mrn=mrn,
                    patient_name=name,
                    dob=dob,
                    gender=gender,
                    record_type=rec_type,
                    encounter_date=enc_date,
                    content_text=content,
                    source_format="csv",
                    audit_trail=logs,
                )
            )

        return records, duplicates_count, invalid_count
