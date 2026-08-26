import math
from collections.abc import Sequence
from typing import Annotated, Literal

from app.core.database import get_session
from app.core.response import PaginatedResponse, PaginationMeta, StandardResponse
from app.ingestion.models import (
    AuditLog,
    AuditLogRead,
    CleanRecord,
    CleanRecordRead,
    IngestionSummary,
)
from app.ingestion.service import IngestionService
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func
from sqlmodel import Session, col, select
from sqlmodel.sql._expression_select_cls import SelectOfScalar

router = APIRouter()
SessionDep = Annotated[Session, Depends(get_session)]


@router.post("/ingest/upload", response_model=StandardResponse[IngestionSummary])
async def upload_ehr_file(
    session: SessionDep,
    file: Annotated[UploadFile, File()],
):
    filename = (file.filename or "").lower()
    if not (filename.endswith(".json") or filename.endswith(".csv")):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Only .json and .csv are permitted.",
        )

    content_bytes: bytes = await file.read()
    content_str: str = content_bytes.decode("utf-8", errors="ignore")
    file_type: Literal["json", "csv"] = "json" if filename.endswith(".json") else "csv"

    summary: IngestionSummary = IngestionService.ingest_payload(
        session, content_str, file_type
    )

    return StandardResponse(
        success=True,
        message=(
            f"Successfully processed {summary.total_processed} records "
            f"({summary.total_cleaned} clean, {summary.total_duplicates_dropped} duplicates dropped, "
            f"{summary.total_invalid_dropped} invalid dropped)"
        ),
        data=summary,
    )


@router.get("/records", response_model=PaginatedResponse[CleanRecordRead])
def get_clean_records(
    session: SessionDep,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    mrn: str | None = Query(None, description="Filter by Patient MRN"),
) -> PaginatedResponse[CleanRecordRead]:

    statement: SelectOfScalar[CleanRecord] = select(CleanRecord)
    if mrn:
        statement = statement.where(col(CleanRecord.patient_mrn) == mrn.strip().upper())

    count_statement: SelectOfScalar[int] = select(func.count()).select_from(
        statement.subquery()
    )
    total_records = session.exec(count_statement).one()

    # Pagination and sorting
    offset: int = (page - 1) * page_size
    paged_statement: SelectOfScalar[CleanRecord] = (
        statement.order_by(col(CleanRecord.encounter_date).desc())
        .offset(offset)
        .limit(page_size)
    )
    records: Sequence[CleanRecord] = session.exec(paged_statement).all()

    total_pages: int = math.ceil(total_records / page_size) if total_records > 0 else 1

    return PaginatedResponse[CleanRecordRead](
        success=True,
        message="Fetched clean records successfully",
        data=[CleanRecordRead.model_validate(r) for r in records],
        pagination=PaginationMeta(
            total_records=total_records,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        ),
    )


@router.get(
    "/audit-logs/{record_id}", response_model=StandardResponse[list[AuditLogRead]]
)
def get_record_audit_logs(
    record_id: str,
    session: SessionDep,
) -> StandardResponse[list[AuditLogRead]]:
    statement: SelectOfScalar[AuditLog] = (
        select(AuditLog)
        .where(col(AuditLog.record_id) == record_id)
        .order_by(col(AuditLog.created_at).asc())
    )
    logs: Sequence[AuditLog] = session.exec(statement).all()

    return StandardResponse[list[AuditLogRead]](
        success=True,
        message=f"Fetched {len(logs)} audit entries for record '{record_id}'",
        data=[AuditLogRead.model_validate(log) for log in logs],
    )
