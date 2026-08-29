from fastapi import HTTPException
from sqlmodel import Session, col, select

from app.ingestion.adapters import IngestionAdapter
from app.ingestion.models import CleanRecord, CleanRecordRead, IngestionSummary


class IngestionService:
    @staticmethod
    def persist_records(
        session: Session, records: list[CleanRecord]
    ) -> tuple[list[CleanRecord], int]:
        """Persists clean records and their associated audit logs atomically, dropping DB duplicates."""
        persisted: list[CleanRecord] = []
        db_duplicates = 0

        for record in records:
            # Check for existing record with the identical content_hash
            existing_by_hash = session.exec(
                select(CleanRecord).where(
                    col(CleanRecord.content_hash) == record.content_hash
                )
            ).first()
            if existing_by_hash:
                db_duplicates += 1
                continue

            # Check if record ID already exists (merge/upsert cleanly)
            existing_by_id = session.get(CleanRecord, record.id)
            if existing_by_id:
                session.delete(existing_by_id)
                session.flush()

            session.add(record)
            persisted.append(record)

        session.commit()
        return persisted, db_duplicates

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

        persisted_records, db_dupes = cls.persist_records(session, records)
        total_dupes = dupes + db_dupes

        total_audit_logs: int = sum(len(r.audit_trail) for r in persisted_records)

        read_records: list[CleanRecordRead] = [
            CleanRecordRead.model_validate(r) for r in persisted_records
        ]

        return IngestionSummary(
            total_processed=len(records) + dupes + invalid,
            total_cleaned=len(persisted_records),
            total_duplicates_dropped=total_dupes,
            total_invalid_dropped=invalid,
            records=read_records,
            audit_logs_count=total_audit_logs,
        )
