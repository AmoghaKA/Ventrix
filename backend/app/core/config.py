from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "Ventrix"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    SECRET_KEY: str = "dev-secret-change-in-production"

    GEMINI_API_KEY: str = ""
    NVIDIA_API_KEY: str = ""
    MISTRAL_API_KEY: str = ""

    DATABASE_URL: str = "sqlite:///./ventrix.db"

    WORKFLOW_MAX_RETRIES: int = 2
    WORKFLOW_RETRY_BACKOFF_SECONDS: float = 0.05
    WORKFLOW_MAX_PAGES: int = 5

    MAX_ANALYSES: int = 10

    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
