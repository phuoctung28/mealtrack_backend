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
    DB_PASSWORD: str = Field(default="changeme")
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=3306)
    DB_NAME: str = Field(default="nutree")

    # SSL controls
    DB_SSL_ENABLED: bool = Field(default=True)
    DB_SSL_VERIFY_CERT: bool = Field(default=False)
    DB_SSL_VERIFY_IDENTITY: bool = Field(default=False)

    # Connection pool tuning
    UVICORN_WORKERS: int = Field(default=1)
    POOL_SIZE_PER_WORKER: int = Field(default=5)
    POOL_MAX_OVERFLOW: int = Field(default=10)
    POOL_TIMEOUT: int = Field(default=30)
    POOL_RECYCLE: int = Field(default=300)
    POOL_ECHO: bool = Field(default=False)

    # Redis configuration
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_DB: int = Field(default=0)
    REDIS_PASSWORD: str | None = Field(default=None)
    REDIS_SSL: bool = Field(default=False)
    REDIS_MAX_CONNECTIONS: int = Field(default=50)

    # Cache configuration
    CACHE_ENABLED: bool = Field(default=True)
    CACHE_DEFAULT_TTL: int = Field(default=3600)  # 1 hour

    # Firebase
    FIREBASE_CREDENTIALS: str | None = Field(default=None)
    FIREBASE_SERVICE_ACCOUNT_JSON: str | None = Field(default=None)
    FIREBASE_SERVICE_ACCOUNT_PATH: str | None = Field(default=None)

    # External APIs & integrations
    GOOGLE_API_KEY: str | None = Field(default=None)
    USDA_FDC_API_KEY: str | None = Field(default=None)
    PINECONE_API_KEY: str | None = Field(default=None)
    
    # LLM Provider configuration
    LLM_PROVIDER: str | None = Field(default=None, description="LLM provider to use: 'openai' or 'gemini'. Auto-detects if not set.")
    OPENAI_MODEL: str = Field(default="gpt-3.5-turbo", description="OpenAI model to use")
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash", description="Gemini model to use (same as food scanning)")
    
    # Chat/AI configuration
    CHAT_ENABLE_STRUCTURED_RESPONSES: bool = Field(default=True, description="Enable structured JSON responses from chat AI")
    CHAT_ENABLE_WELCOME_MESSAGE: bool = Field(default=True, description="Auto-generate welcome message on thread creation")
    REVENUECAT_SECRET_API_KEY: str | None = Field(default=None)
    REVENUECAT_WEBHOOK_SECRET: str | None = Field(default=None)
    CLOUDINARY_CLOUD_NAME: str | None = Field(default=None)
    CLOUDINARY_API_KEY: str | None = Field(default=None)
    CLOUDINARY_API_SECRET: str | None = Field(default=None)

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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Allow extra fields without validation errors
    )

    @property
    def redis_url(self) -> str:
        """Construct a Redis URL from the configured components."""
        protocol = "rediss" if self.REDIS_SSL else "redis"
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"{protocol}://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()

