from datetime import date
from typing import Annotated

from app.core.database import get_session
from app.core.response import StandardResponse
from app.search.models import (IndexStats, ResourceTypeFilter,
                               SearchQueryRequest, SearchResponse)
from app.search.service import SearchService
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

router = APIRouter()
SessionDep = Annotated[Session, Depends(get_session)]


@router.post("/search", response_model=StandardResponse[SearchResponse])
def execute_semantic_search(
    query: Annotated[
        str,
        Query(
            description="Free-text clinical search query (e.g. 'chest pain', 'diabetic neuropathy')",
            min_length=2,
        ),
    ],
    resource_type: Annotated[
        ResourceTypeFilter | None,
        Query(
            description="Filter by FHIR resource type (DocumentReference, DiagnosticReport, ClinicalSummary)"
        ),
    ] = None,
    date_from: Annotated[
        date | None,
        Query(description="Filter records on or after this date (YYYY-MM-DD)"),
    ] = None,
    date_to: Annotated[
        date | None,
        Query(description="Filter records on or before this date (YYYY-MM-DD)"),
    ] = None,
    patient_mrn: Annotated[
        str | None,
        Query(description="Optional scope search to a single patient MRN"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=50, description="Top-K ranked matches to return (default: 5)"),
    ] = 5,
):
    """
    Performs semantic vector search across all patient records and AI summaries
    using URL query parameters.
    """
    if not query.strip():
        return StandardResponse(
            success=False,
            message="Search query cannot be empty",
            data=SearchResponse(
                query="", total_results=0, execution_time_ms=0.0, results=[]
            ),
        )

    req = SearchQueryRequest(
        query=query,
        resource_type=resource_type,
        date_from=date_from,
        date_to=date_to,
        patient_mrn=patient_mrn,
        limit=limit,
    )

    response = SearchService.search(req)

    return StandardResponse(
        success=True,
        message=f"Found {response.total_results} matching records in {response.execution_time_ms}ms",
        data=response,
    )


@router.post("/search/reindex", response_model=StandardResponse[IndexStats])
def trigger_vector_reindexing(session: SessionDep):
    """Rebuilds the entire ChromaDB semantic vector index across all FHIR bundles and AI summaries."""
    stats = SearchService.index_all_records(session, reset=True)
    return StandardResponse(
        success=True,
        message=f"Successfully indexed {stats.total_indexed_documents} clinical items into ChromaDB",
        data=stats,
    )
