import math
from typing import Annotated

from app.core.database import get_session
from app.core.response import PaginatedResponse, PaginationMeta, StandardResponse
from app.fhir.models import FHIRBundle, FHIRBundleRead
from app.fhir.service import FHIRService
from app.ingestion.models import (
    AuditLog,
    AuditLogRead,
    CleanRecord,
    CleanRecordRead,
    IngestAndProcessResponse,
)
from app.ingestion.service import IngestionService
from app.search.service import SearchService
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func
from sqlmodel import Session, col, select

router = APIRouter()
SessionDep = Annotated[Session, Depends(get_session)]


@router.post(
    "/ingest/upload", response_model=StandardResponse[IngestAndProcessResponse]
)
async def upload_ehr_file(
    session: SessionDep,
    file: Annotated[UploadFile, File(...)],
    auto_process: Annotated[
        bool,
        Query(
            description="Automatically trigger FHIR R4 Normalization and Bundle generation"
        ),
    ] = True,
):
    filename = (file.filename or "").lower()
    if not (filename.endswith(".json") or filename.endswith(".csv")):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Only .json and .csv are permitted.",
        )

    content_bytes = await file.read()
    content_str = content_bytes.decode("utf-8", errors="ignore")
    file_type = "json" if filename.endswith(".json") else "csv"

    # Ingest and Clean raw records
    summary = IngestionService.ingest_payload(session, content_str, file_type)

    fhir_report = None
    bundle_reads = None

    # FHIR Normalization
    if auto_process:
        fhir_report = FHIRService.normalize_and_store_all(session)
        # Automatically update ChromaDB vector index in the background
        SearchService.index_all_records(session)

        bundle_statement = select(FHIRBundle).order_by(
            col(FHIRBundle.updated_at).desc()
        )
        db_bundles = session.exec(bundle_statement).all()
        bundle_reads = [FHIRBundleRead.model_validate(b) for b in db_bundles]

    message = (
        f"Processed {summary.total_processed} raw records "
        f"({summary.total_cleaned} clean, {summary.total_duplicates_dropped} duplicates dropped)."
    )
    if auto_process and fhir_report:
        message += (
            f" Generated {fhir_report.total_bundles_created} FHIR Bundles "
            f"({fhir_report.total_resources_mapped} FHIR resources mapped)."
        )

    return StandardResponse(
        success=True,
        message=message,
        data=IngestAndProcessResponse(
            ingestion=summary,
            fhir_normalization=fhir_report,
            bundles=bundle_reads,
        ),
    )


@router.get("/records", response_model=PaginatedResponse[CleanRecordRead])
def get_clean_records(
    session: SessionDep,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 10,
    mrn: Annotated[str | None, Query(description="Filter by Patient MRN")] = None,
):
    statement = select(CleanRecord)
    if mrn:
        statement = statement.where(col(CleanRecord.patient_mrn) == mrn.strip().upper())

    count_statement = select(func.count()).select_from(statement.subquery())
    total_records = session.exec(count_statement).one()

    offset = (page - 1) * page_size
    paged_statement = (
        statement.order_by(col(CleanRecord.encounter_date).desc())
        .offset(offset)
        .limit(page_size)
    )
    records = session.exec(paged_statement).all()

    total_pages = math.ceil(total_records / page_size) if total_records > 0 else 1

    return PaginatedResponse(
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
):
    statement = (
        select(AuditLog)
        .where(col(AuditLog.record_id) == record_id)
        .order_by(col(AuditLog.created_at).asc())
    )
    logs = session.exec(statement).all()

    return StandardResponse(
        success=True,
        message=f"Fetched {len(logs)} audit entries for record '{record_id}'",
        data=[AuditLogRead.model_validate(log) for log in logs],
    )
