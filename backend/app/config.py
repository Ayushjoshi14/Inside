import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

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

    # Google Play Billing (Optional)
    GOOGLE_PLAY_SERVICE_ACCOUNT_JSON: Optional[str] = None
    GOOGLE_PLAY_PACKAGE_NAME: str = "com.inside.inside"

    # Razorpay Payment Gateway (Live / Test configured strictly via .env)
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = None
    PREMIUM_PRODUCT_ID: str = "inside_premium_lifetime"
    LIFETIME_PRODUCT_ID: str = "inside_premium_lifetime"
    PREMIUM_PRICE_PAISE: int = 19900  # 19900 paise = 199 INR
    PREMIUM_CURRENCY: str = "INR"

    # Free Usage Tier Limits
    FREE_SCAN_LIMIT: int = 3

    model_config = SettingsConfigDict(
        env_file=(str(ENV_PATH) if ENV_PATH.exists() else ".env"),
        extra="ignore"
    )

settings = Settings()

