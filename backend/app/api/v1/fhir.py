import json
import math
from typing import Annotated, Any

from app.core.database import get_session
from app.core.response import PaginatedResponse, PaginationMeta, StandardResponse
from app.fhir.models import FHIRBundle, FHIRBundleRead, FHIRValidationReport
from app.fhir.service import FHIRService
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import Session, col, select

router = APIRouter()
SessionDep = Annotated[Session, Depends(get_session)]


@router.post("/normalize", response_model=StandardResponse[FHIRValidationReport])
def normalize_to_fhir(session: SessionDep):
    """Triggers FHIR R4 Normalization and Bundle generation across all ingested records."""
    report = FHIRService.normalize_and_store_all(session)
    return StandardResponse(
        success=len(report.errors) == 0,
        message=(
            f"FHIR Normalization complete: {report.total_bundles_created} Bundles created "
            f"({report.total_resources_mapped} total FHIR resources)"
        ),
        data=report,
    )


@router.get("/bundles", response_model=PaginatedResponse[FHIRBundleRead])
def list_fhir_bundles(
    session: SessionDep,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 10,
):
    """Returns a paginated list of validated FHIR bundles (metadata only)."""
    statement = select(FHIRBundle)
    count_statement = select(func.count()).select_from(statement.subquery())
    total_records = session.exec(count_statement).one()

    offset = (page - 1) * page_size
    paged_statement = (
        statement.order_by(col(FHIRBundle.updated_at).desc())
        .offset(offset)
        .limit(page_size)
    )
    bundles = session.exec(paged_statement).all()

    total_pages = math.ceil(total_records / page_size) if total_records > 0 else 1

    return PaginatedResponse(
        success=True,
        message="Fetched FHIR Bundles successfully",
        data=[FHIRBundleRead.model_validate(b) for b in bundles],
        pagination=PaginationMeta(
            total_records=total_records,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        ),
    )


@router.get("/bundles/{patient_mrn}", response_model=StandardResponse[dict[str, Any]])
def get_patient_fhir_bundle(
    patient_mrn: str,
    session: SessionDep,
):
    """Retrieves the full HL7 FHIR R4 Bundle JSON for a given patient MRN."""
    bundle = FHIRService.get_bundle_by_mrn(session, patient_mrn)
    if not bundle:
        raise HTTPException(
            status_code=404,
            detail=f"FHIR Bundle for Patient MRN '{patient_mrn}' not found",
        )

    bundle_dict = json.loads(bundle.bundle_json)
    return StandardResponse(
        success=True,
        message=f"Retrieved FHIR R4 Bundle for {patient_mrn}",
        data=bundle_dict,
    )
