from fastapi import HTTPException
from sqlmodel import Session

from app.ingestion.adapters import IngestionAdapter
from app.ingestion.models import CleanRecord, CleanRecordRead, IngestionSummary


class IngestionService:
    @staticmethod
    def persist_records(session: Session, records: list[CleanRecord]) -> None:
        """Persists clean records and their associated audit logs atomically."""
        for record in records:
            # Check if record already exists, merge/upsert cleanly
            existing: CleanRecord | None = session.get(CleanRecord, record.id)
            if existing:
                session.delete(existing)
                session.flush()

            session.add(record)

        session.commit()

    @classmethod
    def ingest_payload(
        cls, session: Session, content_str: str, file_type: str
    ) -> IngestionSummary:
        if file_type.lower() == "json":
            records, dupes, invalid = IngestionAdapter.process_json(content_str)
        elif file_type.lower() == "csv":
            records, dupes, invalid = IngestionAdapter.process_csv(content_str)
        else:
            raise HTTPException(
                status_code=400, detail=f"Unsupported file format: {file_type}"
            )

        cls.persist_records(session, records)

        total_audit_logs: int = sum(len(r.audit_trail) for r in records)

        # Refresh for read DTO representation
        read_records: list[CleanRecordRead] = [
            CleanRecordRead.model_validate(r) for r in records
        ]

        return IngestionSummary(
            total_processed=len(records) + dupes + invalid,
            total_cleaned=len(records),
            total_duplicates_dropped=dupes,
            total_invalid_dropped=invalid,
            records=read_records,
            audit_logs_count=total_audit_logs,
        )
