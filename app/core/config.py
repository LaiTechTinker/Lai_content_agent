"""Centralized backend configuration loaded from environment variables."""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_ROOT / ".env")


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_origins(value: str | None) -> list[str]:
    return [origin.strip() for origin in (value or "").split(",") if origin.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Lai_agent")
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = _as_bool(os.getenv("DEBUG"), default=False)
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    backend_url: str = os.getenv("BACKEND_URL", "http://localhost:8000")

    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./content.db")
    database_path: str = os.getenv("DATABASE_PATH", "content.db")
    checkpoint_path: str = os.getenv("CHECKPOINT_PATH", "content_engine_checkpoints.db")

    google_api_key: str | None = os.getenv("GOOGLE_API_KEY")
    google_model: str = os.getenv("GOOGLE_MODEL", "gemini-3.5-flash")
    google_embedding_model: str = os.getenv("GOOGLE_EMBEDDING_MODEL", "gemini-embedding-2")
    tavily_api_key: str | None = os.getenv("TAVILY_API_KEY")

    cloudflare_secret: str | None = os.getenv("CLOUDFLARE_SECRET") or os.getenv("CLOUDFLARE_SCERET")
    cloudflare_url: str | None = os.getenv("CLOUDFLARE_URL") or os.getenv("CLOUDFLARE_WORKER_URL")
    image_model: str = os.getenv("IMAGE_MODEL", "")
    use_gemini_image: bool = _as_bool(os.getenv("USE_GEMINI_IMAGE"), default=False)
    audio_model: str = os.getenv("AUDIO_MODEL", "")

    x_client_id: str | None = os.getenv("X_CLIENT_ID")
    x_client_secret: str | None = os.getenv("X_CLIENT_SECRET")
    x_redirect_uri: str | None = os.getenv("X_REDIRECT_URI")
    linkedin_client_id: str | None = os.getenv("LINKEDIN_CLIENT_ID")
    linkedin_client_secret: str | None = os.getenv("LINKEDIN_CLIENT_SECRET")
    linkedin_redirect_uri: str | None = os.getenv("LINKEDIN_REDIRECT_URI")
    linkedin_api_version: str = os.getenv("LINKEDIN_API_VERSION", "20240201")

    secret_key: str | None = os.getenv("SECRET_KEY")
    jwt_secret_key: str | None = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
    cors_origins: list[str] = None  # type: ignore[assignment]
    cors_methods: list[str] = None  # type: ignore[assignment]
    cors_headers: list[str] = None  # type: ignore[assignment]
    cors_allow_credentials: bool = _as_bool(os.getenv("CORS_ALLOW_CREDENTIALS"), default=True)

    def __post_init__(self) -> None:
        object.__setattr__(self, "cors_origins", _as_origins(os.getenv("CORS_ORIGINS", self.frontend_url)))
        object.__setattr__(self, "cors_methods", _as_origins(os.getenv("CORS_METHODS", "GET,POST,PATCH,PUT,DELETE,OPTIONS")))
        object.__setattr__(self, "cors_headers", _as_origins(os.getenv("CORS_HEADERS", "Content-Type,Authorization")))

    def require_google_api_key(self) -> str:
        if not self.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY is required for Google AI operations.")
        return self.google_api_key

    def require_tavily_api_key(self) -> str:
        if not self.tavily_api_key:
            raise RuntimeError("TAVILY_API_KEY is required for web research.")
        return self.tavily_api_key

    def require_cloudflare(self) -> tuple[str, str]:
        if not self.cloudflare_secret or not self.cloudflare_url:
            raise RuntimeError("CLOUDFLARE_SECRET and CLOUDFLARE_URL are required for Cloudflare image generation.")
        return self.cloudflare_secret, self.cloudflare_url

    def require_jwt_secret(self) -> str:
        if self.jwt_secret_key:
            return self.jwt_secret_key
        if self.environment == "development":
            return "development-only-change-this-jwt-secret"
        raise RuntimeError("JWT_SECRET_KEY is required outside development.")


settings = Settings()
