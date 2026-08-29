from contextlib import asynccontextmanager

from app.api.v1.fhir import router as fhir_router
from app.api.v1.ingestion import router as ingestion_router
from app.api.v1.search import router as search_router
from app.api.v1.summary import router as summary_router
from app.core.config import settings
from app.core.database import init_db
from app.core.response import StandardResponse
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=StandardResponse[dict])
def health_check():
    return StandardResponse(
        success=True,
        message="EHR Media Intelligence API is operational",
        data={"status": "healthy"},
    )


app.include_router(
    ingestion_router,
    prefix=settings.API_V1_STR,
    tags=["Ingestion & Cleaning"],
)

app.include_router(
    fhir_router,
    prefix=f"{settings.API_V1_STR}/fhir",
    tags=["FHIR R4 Normalization"],
)

app.include_router(
    summary_router,
    prefix=settings.API_V1_STR,
    tags=["AI Clinical Summarization"],
)

app.include_router(
    search_router,
    prefix=settings.API_V1_STR,
    tags=["Semantic Vector Search"],
)
