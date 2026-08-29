from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, col, select

from app.core.database import get_session
from app.core.response import StandardResponse
from app.llm.models import ClinicalSummaryRead, ClinicalSummaryTable
from app.llm.service import SummarizerService
from app.search.service import SearchService

router = APIRouter()
SessionDep = Annotated[Session, Depends(get_session)]


@router.post(
    "/summary/{patient_mrn}",
    response_model=StandardResponse[ClinicalSummaryRead],
)
def generate_patient_summary(
    patient_mrn: str,
    session: SessionDep,
):
    """
    Generates a structured clinical summary from the patient's FHIR Bundle.
    Uses SQLite caching to return instant results on unchanged records.
    """
    try:
        summary = SummarizerService.generate_summary(session, patient_mrn)
        if not summary.cache_hit:
            summary_record = session.exec(
                select(ClinicalSummaryTable)
                .where(
                    col(ClinicalSummaryTable.patient_mrn)
                    == patient_mrn.strip().upper()
                )
                .order_by(col(ClinicalSummaryTable.created_at).desc())
            ).first()
            if summary_record:
                SearchService.index_summary(summary_record)

        cache_status = "CACHE HIT" if summary.cache_hit else "CACHE MISS (AI Generated)"
        return StandardResponse(
            success=True,
            message=f"Clinical summary generated for {patient_mrn} [{cache_status}]",
            data=summary,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate clinical summary: {str(e)}",
        ) from e
