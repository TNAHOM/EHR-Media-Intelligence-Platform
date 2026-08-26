from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "EHR Media Intelligence Platform"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./data/ehr.db"
    RAW_DATA_DIR: str = "./data/raw"
    model_config = SettingsConfigDict(case_sensitive=True)


settings = Settings()
