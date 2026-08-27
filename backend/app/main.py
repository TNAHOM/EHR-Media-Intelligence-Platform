from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.fhir import router as fhir_router
from app.api.v1.ingestion import router as ingestion_router
from app.core.config import settings
from app.core.database import init_db
from app.core.response import StandardResponse


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
    allow_credentials=True,
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
