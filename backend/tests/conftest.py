from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

import app.search.service as search_service_module
import app.search.vector_store as vector_store_module
from app.core.database import get_session
from app.llm.service import SummarizerService
from app.main import app
from app.search.vector_store import ChromaVectorStore

# In-memory SQLite engine for tests
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(autouse=True)
def isolated_vector_store():
    """Provides an isolated ephemeral in-memory ChromaDB instance for each test."""
    ephemeral_store = ChromaVectorStore(is_ephemeral=True)
    orig_vs = vector_store_module.vector_store
    orig_ss_vs = search_service_module.vector_store

    vector_store_module.vector_store = ephemeral_store
    search_service_module.vector_store = ephemeral_store

    yield ephemeral_store

    vector_store_module.vector_store = orig_vs
    search_service_module.vector_store = orig_ss_vs


@pytest.fixture(name="session")
def session_fixture() -> Generator[Session, None, None]:
    SQLModel.metadata.create_all(TEST_ENGINE)
    with Session(TEST_ENGINE) as session:
        yield session
    SQLModel.metadata.drop_all(TEST_ENGINE)


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="mock_gemini_client")
def mock_gemini_client_fixture(monkeypatch):
    """Mocks Google GenAI Client so tests run offline without live credentials."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = (
        '{"chief_concern": "Patient admitted for severe acute migraine.", '
        '"key_diagnoses": "Severe acute migraine with visual aura.", '
        '"recent_media_records": "None recorded.", '
        '"flagged_anomalies": "No acute abnormalities identified."}'
    )
    mock_client.models.generate_content.return_value = mock_response

    monkeypatch.setattr(SummarizerService, "get_client", classmethod(lambda cls: mock_client))
    return mock_client
