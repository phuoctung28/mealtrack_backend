"""
Application configuration settings loaded from environment variables.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application settings."""

    # General application settings
    ENVIRONMENT: str = Field(default="development")
    FAIL_ON_MIGRATION_ERROR: bool = Field(default=False)
    FAIL_ON_CACHE_ERROR: bool = Field(default=False)
    AUTO_MIGRATE: bool = Field(default=True)
    MIGRATION_TIMEOUT: int = Field(default=60)
    MIGRATION_RETRY_ATTEMPTS: int = Field(default=3)
    MIGRATION_RETRY_DELAY: float = Field(default=2.0)

    # Database configuration
    DATABASE_URL: str | None = Field(default=None)
    DB_USER: str = Field(default="nutree")
    DB_PASSWORD: str = Field(default="")
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=5432)
    DB_NAME: str = Field(default="nutree")

    # Connection pool tuning
    UVICORN_WORKERS: int = Field(
        default=4, description="Number of worker processes"
    )
    POOL_SIZE_PER_WORKER: int = Field(
        default=3, description="DB connections per worker"
    )
    POOL_MAX_OVERFLOW: int = Field(
        default=2, description="Max overflow connections"
    )
    POOL_TIMEOUT: int = Field(default=30)
    POOL_RECYCLE: int = Field(default=120)
    POOL_ECHO: bool = Field(default=False)

    # Redis configuration (optimized for low-memory)
    # Prefer setting REDIS_URL directly for hosted providers (e.g., Upstash)
    REDIS_URL: str | None = Field(default=None)
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_DB: int = Field(default=0)
    REDIS_USERNAME: str | None = Field(default=None)
    REDIS_PASSWORD: str | None = Field(default=None)
    REDIS_SSL: bool = Field(default=False)
    REDIS_MAX_CONNECTIONS: int = Field(
        default=10, description="Max Redis connections (reduced from 50)"
    )

    # Cache configuration
    CACHE_ENABLED: bool = Field(default=True)
    CACHE_DEFAULT_TTL: int = Field(default=3600)  # 1 hour

    # Firebase
    FIREBASE_CREDENTIALS: str | None = Field(default=None)
    FIREBASE_SERVICE_ACCOUNT_JSON: str | None = Field(default=None)
    FIREBASE_SERVICE_ACCOUNT_PATH: str | None = Field(default=None)

    # External APIs & integrations
    DEEPL_API_KEY: str | None = Field(default=None, description="DeepL API key for meal translation")
    GOOGLE_API_KEY: str | None = Field(default=None)
    USDA_FDC_API_KEY: str | None = Field(default=None)
    FATSECRET_CLIENT_ID: str | None = Field(default=None, description="FatSecret OAuth 2.0 client ID")
    FATSECRET_CLIENT_SECRET: str | None = Field(default=None, description="FatSecret OAuth 2.0 client secret")
    NUTRITIONIX_APP_ID: str | None = Field(default=None, description="Nutritionix API app ID")
    NUTRITIONIX_API_KEY: str | None = Field(default=None, description="Nutritionix API key")
    BRAVE_SEARCH_API_KEY: str | None = Field(default=None, description="Brave Search API key (free tier: 2K/mo)")

    # LLM Provider configuration
    LLM_PROVIDER: str | None = Field(
        default=None,
        description="LLM provider to use: 'openai' or 'gemini'. Auto-detects if not set.",
    )
    OPENAI_MODEL: str = Field(
        default="gpt-3.5-turbo", description="OpenAI model to use"
    )
    GEMINI_MODEL: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model to use (same as food scanning)",
    )

    # Multi-model Gemini configuration for rate limit distribution
    GEMINI_MODEL_NAMES: str = Field(
        default="gemini-2.5-flash-lite",
        description="Gemini model for meal name generation (higher RPM: 10/min)",
    )
    GEMINI_MODEL_RECIPE_PRIMARY: str = Field(
        default="gemini-2.5-flash",
        description="Primary model for recipe generation (5 RPM)",
    )
    GEMINI_MODEL_RECIPE_SECONDARY: str = Field(
        default="gemini-3-flash",
        description="Secondary model for recipe generation (5 RPM, load distribution)",
    )

    # Image search (meal discovery photos)
    PEXELS_API_KEY: str | None = Field(default=None, description="Pexels API key for food photos")
    UNSPLASH_ACCESS_KEY: str | None = Field(default=None, description="Unsplash Client-ID access key")
    REVENUECAT_SECRET_API_KEY: str | None = Field(default=None)
    REVENUECAT_WEBHOOK_SECRET: str | None = Field(default=None)
    CLOUDINARY_CLOUD_NAME: str | None = Field(default=None)
    CLOUDINARY_API_KEY: str | None = Field(default=None)
    CLOUDINARY_API_SECRET: str | None = Field(default=None)

    # CORS
    ALLOWED_ORIGINS: str = Field(default="", description="Comma-separated list of allowed CORS origins")

    # Sentry error monitoring
    SENTRY_DSN: str | None = Field(default=None, description="Sentry DSN; disables Sentry when unset")
    SENTRY_TRACES_SAMPLE_RATE: float = Field(default=0.1, description="Performance trace sample rate (0.0-1.0)")
    SENTRY_PROFILES_SAMPLE_RATE: float = Field(default=0.05, description="Profile sample rate (0.0-1.0)")
    SENTRY_SEND_PII: bool = Field(default=False, description="Send user IP/headers to Sentry")

    # Feature flags / development toggles
    USE_MOCK_STORAGE: int = Field(default=0)
    DEV_USER_FIREBASE_UID: str = Field(default="dev_firebase_uid")
    DEV_USER_EMAIL: str = Field(default="dev@example.com")
    DEV_USER_USERNAME: str = Field(default="dev_user")

    # Additional fields from actual .env
    UPLOADS_DIR: str | None = Field(default=None)
    FCM_CREDENTIALS_PATH: str | None = Field(default=None)
    SMTP_HOST: str | None = Field(default=None)
    SMTP_PORT: int | None = Field(default=None)
    SMTP_USERNAME: str | None = Field(default=None)
    SMTP_PASSWORD: str | None = Field(default=None)
    EMAIL_FROM_ADDRESS: str | None = Field(default=None)
    EMAIL_FROM_NAME: str | None = Field(default=None)

    # --- Meal image cache (nightly-fill vector cache) ---
    MEAL_IMAGE_CACHE_ENABLED: bool = Field(default=False)
    TEXT_DEDUP_THRESHOLD: float = Field(default=0.65)
    IMAGE_MATCH_THRESHOLD: float = Field(default=0.65)
    MEAL_IMAGE_COSINE_HIT_THRESHOLD: float = Field(
        default=0.65,
        description="Cosine similarity above which a cached image is reused (0.65–0.80 recommended)",
    )

    # Embeddings — SigLIP google/siglip-base-patch16-224 (768-d)
    CLIP_MODEL_NAME: str = Field(default="google/siglip-base-patch16-224")
    CLIP_DEVICE: str = Field(default="cpu")
    CLIP_EMBEDDING_DIM: int = Field(default=768)

    # AI image generators — Cloudflare Workers AI (free tier: ~150-600 images/month)
    CF_ACCOUNT_ID: str | None = Field(default=None, description="Cloudflare account ID (dash.cloudflare.com → right sidebar)")
    CF_API_TOKEN: str | None = Field(default=None, description="Cloudflare API token with Workers AI permission")
    CF_IMAGE_MODEL: str = Field(default="@cf/black-forest-labs/flux-1-schnell", description="CF Workers AI model for image generation")
    AI_IMAGE_TIMEOUT_SECONDS: int = Field(default=60)

    # Nightly cron drain
    MAX_JOBS_PER_CRON: int = Field(default=50)
    CRON_EXTERNAL_CALL_DELAY_SECONDS: float = Field(default=2.0)
    MAX_RESOLUTION_ATTEMPTS: int = Field(default=5)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Allow extra fields without validation errors
    )

    @property
    def redis_url(self) -> str:
        """Return Redis connection URL.

        If REDIS_URL is set, it is used verbatim (supports username/password URLs).
        Otherwise, a URL is constructed from the component settings.
        """
        if self.REDIS_URL:
            return self.REDIS_URL

        protocol = "rediss" if self.REDIS_SSL else "redis"
        if self.REDIS_USERNAME and self.REDIS_PASSWORD:
            auth = f"{self.REDIS_USERNAME}:{self.REDIS_PASSWORD}@"
        elif self.REDIS_PASSWORD:
            auth = f":{self.REDIS_PASSWORD}@"
        else:
            auth = ""
        return f"{protocol}://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()
