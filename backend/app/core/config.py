from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "EHR Media Intelligence Platform"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./data/ehr.db"
    RAW_DATA_DIR: str = "./data/raw"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.6-flash"
    GEMINI_THINKING_LEVEL: Literal["LOW", "MEDIUM", "HIGH"] = "LOW"

    CHROMA_PERSIST_DIR: str = "./data/chroma_db"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    MIN_RELEVANCE_SCORE: float = 0.20

    MAX_SUMMARY_WORDS_PROMPT: int = 190
    MAX_SUMMARY_WORDS_LIMIT: int = 215

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),  # Checks backend/.env or root .env
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
