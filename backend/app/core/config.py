from pydantic import field_validator
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
    GROQ_API_KEY: str = ""

    GEMINI_MODEL: str = "gemini-1.5-flash"
    NVIDIA_MODEL: str = "nvidia/nemotron-70b-instruct"
    MISTRAL_MODEL: str = "mistral-large-latest"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    LLM_TIMEOUT_SECONDS: float = 30.0
    LLM_MOCK_MODE: bool = True

    # Supabase (backend only - never expose service role key to frontend)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_DATABASE_URL: str = ""

    DATABASE_URL: str = "sqlite:///./ventrix.db"

    @property
    def database_url(self) -> str:
        url = self.SUPABASE_DATABASE_URL or self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    WORKFLOW_MAX_RETRIES: int = 2
    WORKFLOW_RETRY_BACKOFF_SECONDS: float = 0.05
    WORKFLOW_MAX_PAGES: int = 5

    MAX_ANALYSES: int = 10

    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
