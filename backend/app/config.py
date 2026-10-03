import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "Inside"
    APP_ENV: str = "development"  # development, staging, production
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./inside.db"

    # Security & Auth
    JWT_SECRET_KEY: str = "inside-super-secure-jwt-secret-key-production-change"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days

    # Gemini AI
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Google Play Billing
    GOOGLE_PLAY_PACKAGE_NAME: str = "com.inside.ingredients"
    GOOGLE_PLAY_SERVICE_ACCOUNT_JSON: Optional[str] = None
    LIFETIME_PRODUCT_ID: str = "premium_lifetime"

    # Free Usage Tier Limits
    FREE_SCAN_LIMIT: int = 5

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
