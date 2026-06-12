from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str

    # ── Auth ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = "clavra_dev_secret_key_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── AI ────────────────────────────────────────────────────────────────
    AI_PROVIDER: str = "ollama"
    OPENAI_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"
    AI_CONFIDENCE_THRESHOLD: float = 0.72
    SQL_MAX_ROWS: int = 500
    TTS_VOICE: str = "alloy"

    # ── Cache ─────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── App ───────────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174,http://localhost:3000"
    MAX_FILE_SIZE_MB: int = 20

    # ── Legacy support (old .env keys still work) ─────────────────────────
    jwt_secret: Optional[str] = None
    jwt_algorithm: Optional[str] = None
    access_token_expire_minutes: Optional[int] = None

    def get_secret_key(self) -> str:
        """Unified secret key — supports both old and new .env keys."""
        return self.jwt_secret or self.SECRET_KEY

    def get_allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
